from typing import Any

from httpx import AsyncClient, Response
from jinja2 import Environment

from src.aws import inmemory_s3_download
from src.settings import read_s3_bucket_from_ssm
from src.types import (
    Attachment,
    AttachmentWithContent,
    MailgunCredentials,
    RenderedScheduledEmail,
    ScheduledEmail,
)


def render_template_from_string(engine: Environment, template: str, context: dict[str, Any]) -> str:
    return engine.from_string(template).render(context)


def render_email(
    engine: Environment,
    email: ScheduledEmail,
    context: dict[str, Any],
    recipients: list[str],
) -> RenderedScheduledEmail:
    subject_rendered = render_template_from_string(engine, email.subject, context)
    body_rendered = render_template_from_string(engine, email.body, context)
    to_header_rendered = [recipient for recipient in recipients if recipient]

    return RenderedScheduledEmail(
        **email.model_dump(),
        to_header_rendered=to_header_rendered,
        subject_rendered=subject_rendered,
        body_rendered=body_rendered,
        attachments_with_content=[],
    )


def read_attachment_from_s3(attachment: Attachment) -> AttachmentWithContent:
    bucket_name = read_s3_bucket_from_ssm()
    file_contents = inmemory_s3_download(bucket_name, attachment.s3_path)
    return AttachmentWithContent(filename=attachment.filename, content=file_contents)


async def send_email(
    client: AsyncClient,
    email: RenderedScheduledEmail,
    credentials: MailgunCredentials,
    overwrite_outgoing_emails: str | None = None,
) -> Response:
    url = f"https://api.mailgun.net/v3/{credentials.MAILGUN_SENDER_DOMAIN}/messages"
    to = email.to_header_rendered[:]
    cc = email.cc_header[:]
    bcc = email.bcc_header[:]

    if overwrite_outgoing_emails:
        to = [overwrite_outgoing_emails]
        cc = []
        bcc = []

    return await client.post(
        url,
        auth=("api", credentials.MAILGUN_API_KEY),
        files=[
            ("attachment", (attachment.filename or "attachment", attachment.content))
            for attachment in email.attachments_with_content
        ],
        data={
            "from": email.from_header,
            "to": to,
            "h:Reply-To": email.reply_to_header,
            "cc": cc,
            "bcc": bcc,
            "subject": email.subject_rendered,
            "html": email.body_rendered,
        },
    )
