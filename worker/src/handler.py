import logging

import httpx
import psycopg.cursor_async


from src.database import (
    fail_email,
    lock_email,
    succeed_email,
    update_email_state,
)
from src.email import send_email
from src.types import (
    MailgunCredentials,
    ScheduledEmail,
    WorkerOutputEmail,
)

logger = logging.getLogger("amy-email-worker")


async def handle_email(
    email: ScheduledEmail,
    mailgun_credentials: MailgunCredentials,
    overwrite_outgoing_emails: str,
    cursor: psycopg.cursor_async.AsyncCursor,
    client: httpx.AsyncClient,
) -> WorkerOutputEmail:
    id = email.id
    logger.info(f"Working on email {id}.")

    updated_email = await lock_email(email, cursor)
    logger.info(f"Locked email {id}. Attempting to send.")

    try:
        response = await send_email(
            client,
            updated_email,
            mailgun_credentials,
            overwrite_outgoing_emails=overwrite_outgoing_emails,
        )
        logger.info(f"Sent email {id}.")
        logger.info(f"Mailgun response: {response=}")
        logger.info(f"Response content: {response.content!r}")
        response.raise_for_status()

    except Exception as exc:
        logger.info(f"Failed to send email {id}. Error: {exc}")
        failed_email = await fail_email(
            updated_email, f"Email failed to send. Error: {exc}", cursor
        )
        return {
            "email": failed_email.model_dump(),
            "status": failed_email.state,
        }

    else:
        succeeded_email = await succeed_email(
            updated_email, "Email sent successfully.", cursor
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
