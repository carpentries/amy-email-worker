import logging
from typing import cast
from uuid import UUID

import httpx
from jinja2 import DebugUndefined, Environment
from jinja2.exceptions import TemplateError
import markdown
from pydantic_core import ValidationError

from src.api import (
    ScheduledEmailController,
    UriError,
    context_entry,
    fetch_model_field,
    scalar_value_from_uri,
)
from src.email import read_attachment_from_s3, render_email, send_email
from src.token import TokenCache
from src.types import (
    ContextModel,
    MailgunCredentials,
    ScheduledEmail,
    SinglePropertyLinkModel,
    SingleValueLinkModel,
    ToHeaderModel,
    WorkerOutputEmail,
)

logger = logging.getLogger("amy-email-worker")


async def return_fail_email(id_: UUID, details: str, controller: ScheduledEmailController) -> WorkerOutputEmail:
    """Auxilary function to log failed info and return failed email struct."""
    logger.info(details)
    failed_email = await controller.fail_by_id(id_, details=details)
    return {
        "email": failed_email.model_dump(mode="json"),
        "status": failed_email.state.value,
    }


async def handle_email(
    email: ScheduledEmail,
    mailgun_credentials: MailgunCredentials,
    overwrite_outgoing_emails: str,
    controller: ScheduledEmailController,
    client: httpx.AsyncClient,
    token_cache: TokenCache,
) -> WorkerOutputEmail:
    id = email.pk
    logger.info(f"Working on email {id}.")

    locked_email = await controller.lock_by_id(id)
    logger.info(f"Locked email {id}.")

    try:
        context = ContextModel(locked_email.context_json)
    except ValidationError as exc:
        logger.error(f"Validation error: {exc}")
        return await return_fail_email(
            id,
            f"Failed to read email context {id}.",
            controller,
        )

    try:
        recipients = ToHeaderModel(
            root=cast(
                list[SinglePropertyLinkModel | SingleValueLinkModel],
                locked_email.to_header_context_json,
            )
        )
    except ValidationError as exc:
        logger.error(f"Validation error: {exc}")
        return await return_fail_email(
            id,
            f"Failed to read email recipients {id}.",
            controller,
        )

    try:
        token = await token_cache.get_token()
    except httpx.HTTPError as exc:
        return await return_fail_email(
            id,
            f"Failed to get API auth token. Error: {exc}",
            controller,
        )

    # Fetch data from API for context and recipients
    try:
        context_dict = {key: await context_entry(link, client, token) for key, link in context.root.items()}
    except (UriError, httpx.HTTPError) as exc:
        return await return_fail_email(
            id,
            f"Issue when generating context: {exc}",
            controller,
        )

    try:
        recipient_addresses_list = [
            (
                str(scalar_value_from_uri(recipient.value_uri))
                if isinstance(recipient, SingleValueLinkModel)
                else await fetch_model_field(recipient.api_uri, recipient.property, client, token)
            )
            for recipient in recipients.root
        ]
    except (UriError, httpx.HTTPError) as exc:
        return await return_fail_email(
            id,
            f"Issue when generating email {id} recipients: {exc}",
            controller,
        )

    # Render email subject, body and recipients using JSON data from the API.
    logger.info(f"Rendering email {id}.")
    engine = Environment(autoescape=True, undefined=DebugUndefined)
    try:
        rendered_email = render_email(engine, locked_email, context_dict, recipient_addresses_list)
    except TemplateError as exc:
        return await return_fail_email(
            id,
            f"Failed to render email {id}. Error: {exc}",
            controller,
        )

    # Render the markdown body of the email
    logger.info(f"Rendering email's MD body {id}.")
    body_html = markdown.markdown(rendered_email.body_rendered)
    rendered_email.body_rendered = body_html

    # Read attachments from S3
    logger.info("Reading attachments from S3.")
    try:
        rendered_email.attachments_with_content = [
            read_attachment_from_s3(attachment) for attachment in rendered_email.attachments
        ]
    except Exception as exc:  # TODO: what exception actually this is? boto3 I guess
        return await return_fail_email(
            id,
            f"Failed to download attachments for email {id}. Error: {exc}",
            controller,
        )

    try:
        logger.info(f"Attempting to send email {id}.")
        response = await send_email(
            client,
            rendered_email,
            mailgun_credentials,
            overwrite_outgoing_emails=overwrite_outgoing_emails,
        )
        logger.info(f"Sent email {id}.")
        logger.info(f"Mailgun response: {response=}")
        logger.info(f"Response content: {response.content!r}")
        response.raise_for_status()

    except Exception as exc:
        return await return_fail_email(id, f"Failed to send email {id}. Error: {exc}", controller)

    else:
        succeeded_email = await controller.succeed_by_id(
            id, f"Email sent successfully. Mailgun response: {response.content!r}"
        )
        return {
            "email": succeeded_email.model_dump(mode="json"),
            "status": succeeded_email.state.value,
        }
