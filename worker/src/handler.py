import json
import logging
from typing import Any

import httpx
import psycopg.cursor_async

from src.api import context_entry, fetch_model_field
from src.database import (
    fail_email,
    lock_email,
    succeed_email,
    update_email_state,
)
from src.email import render_email, send_email
from src.types import (
    ContextModel,
    MailgunCredentials,
    ScheduledEmail,
    ToHeaderModel,
    WorkerOutputEmail,
)

logger = logging.getLogger("amy-email-worker")


async def return_fail_email(
    email: ScheduledEmail, details: str, cursor: psycopg.cursor_async.AsyncCursor[Any]
) -> WorkerOutputEmail:
    """Auxilary function to log failed info and return failed email struct."""
    logger.info(details)
    failed_email = await fail_email(email, details, cursor)
    return {
        "email": failed_email.model_dump(),
        "status": failed_email.state,
    }


async def handle_email(
    email: ScheduledEmail,
    mailgun_credentials: MailgunCredentials,
    overwrite_outgoing_emails: str,
    cursor: psycopg.cursor_async.AsyncCursor[Any],
    client: httpx.AsyncClient,
    stage: str,
) -> WorkerOutputEmail:
    id = email.id
    logger.info(f"Working on email {id}.")

    locked_email = await lock_email(email, cursor)
    logger.info(f"Locked email {id}.")

    try:
        context = ContextModel(**json.loads(locked_email.context_json))
    except json.JSONDecodeError as exc:
        return await return_fail_email(
            locked_email,
            f"Failed to read JSON from email context {id}. Error: {exc}",
            cursor,
        )

    try:
        recipients = ToHeaderModel(root=json.loads(locked_email.to_header_context_json))
    except json.JSONDecodeError as exc:
        return await return_fail_email(
            locked_email,
            f"Failed to read JSON from email recipients {id}. Error: {exc}",
            cursor,
        )

    # Fetch data from API for context and recipients
    context_dict = {
        key: await context_entry(link, client, stage)
        for key, link in context.root.items()
    }
    recipient_addresses_list = [
        await fetch_model_field(recipient.api_uri, recipient.property, client, stage)
        for recipient in recipients.root
    ]

    # Render email subject, body and recipients using JSON data from the API.
    logger.info(f"Rendering email {id}.")
    rendered_email = render_email(locked_email, context_dict, recipient_addresses_list)

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
        return await return_fail_email(
            locked_email,
            f"Failed to send email {id}. Error: {exc}",
            cursor,
        )

    else:
        succeeded_email = await succeed_email(
            locked_email, "Email sent successfully.", cursor
        )
        await update_email_state(
            succeeded_email,
            succeeded_email.state,
            cursor,
            details=f"Mailgun response: {response.content!r}",
        )
        return {
            "email": succeeded_email.model_dump(),
            "status": succeeded_email.state,
        }
