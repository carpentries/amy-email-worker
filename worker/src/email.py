from typing import Any

from django.template import Engine, Context
from httpx import AsyncClient, Response

from src.types import (
    MailgunCredentials,
    ScheduledEmail,
    RenderedScheduledEmail,
)


def render_django_template(
    engine: Engine, template: str, context: dict[str, Any]
) -> str:
    return engine.from_string(template).render(Context(context))


def render_email(
    email: ScheduledEmail,
    context: dict[str, Any],
    recipients: list[str],
) -> RenderedScheduledEmail:
    engine = Engine.get_default()
    subject_rendered = render_django_template(engine, email.subject, context)
    body_rendered = render_django_template(engine, email.body, context)
    to_header_rendered = [recipient for recipient in recipients if recipient]

    return RenderedScheduledEmail(
        **email.model_dump(),
        to_header_rendered=to_header_rendered,
        subject_rendered=subject_rendered,
        body_rendered=body_rendered,
    )


async def send_email(
    client: AsyncClient,
    email: ScheduledEmail,
    credentials: MailgunCredentials,
    overwrite_outgoing_emails: str | None = None,
) -> Response:
    url = f"https://api.mailgun.net/v3/{credentials.MAILGUN_SENDER_DOMAIN}/messages"
    to = email.to_header
    cc = email.cc_header
    bcc = email.bcc_header

    if overwrite_outgoing_emails:
        to = [overwrite_outgoing_emails]
        cc = []
        bcc = []

    return await client.post(
        url,
        auth=("api", credentials.MAILGUN_API_KEY),
        data={
            "from": email.from_header,
            "to": to,
            "h:Reply-To": email.reply_to_header,
            "cc": cc,
            "bcc": bcc,
            "subject": email.subject,
            "html": email.body,
        },
    )
