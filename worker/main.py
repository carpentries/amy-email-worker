import asyncio
import logging
from typing import Any

import httpx
import psycopg
import psycopg.cursor_async
from aws_lambda_powertools.utilities.typing import LambdaContext
from psycopg.rows import dict_row

from src.database import (
    connection_string,
    fail_email,
    fetch_scheduled_emails_to_run,
    lock_email,
    read_database_credentials_from_ssm,
    succeed_email,
    update_email_state,
)
from src.email import send_email
from src.settings import read_mailgun_credentials, read_settings_from_env
from src.types import (
    MailgunCredentials,
    ScheduledEmail,
    WorkerOutput,
    WorkerOutputEmail,
)

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # use logging.DEBUG to see boto3 logs


# TODO:
# 1. rewrite to async ✅
# 2. make sure tests pass (even with async on) ✅
# 3. add mapping for API endpoints
# 4. circle back to AMY to update the endpoints
# 5. create schemas for the endpoints
# 6. add endpoints for managing emails
# 7. rewrite logic from handler below to use the new email endpoints


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
            details=f"Mailgun response: {response.content}",
        )
        return {
            "email": succeeded_email.model_dump(),
            "status": succeeded_email.state,
        }


async def main(event: dict[Any, Any], context: LambdaContext) -> WorkerOutput:
    logger.info(f"Start handler with arguments: {event=}, {context=}")

    settings = read_settings_from_env()
    stage = settings.STAGE
    overwrite_outgoing_emails = settings.OVERWRITE_OUTGOING_EMAILS
    logger.info(f"Stage: {stage}")
    logger.info(f"Outgoing emails override: {overwrite_outgoing_emails}")

    database_credentials = read_database_credentials_from_ssm(stage)
    logger.info("Obtained credentials for database.")

    mailgun_credentials = read_mailgun_credentials(stage)
    logger.info("Obtained credentials for Mailgun.")

    result: WorkerOutput = {"emails": []}

    async with (
        await psycopg.AsyncConnection.connect(
            connection_string(database_credentials),
            row_factory=dict_row,  # TODO: pydantic model for row_factory
        ) as connection,
        connection.cursor() as cursor,
        httpx.AsyncClient() as client,
    ):
        emails = await fetch_scheduled_emails_to_run(cursor)

        result["emails"] = await asyncio.gather(
            *[
                handle_email(
                    email,
                    mailgun_credentials,
                    overwrite_outgoing_emails,
                    cursor,
                    client,
                )
                for email in emails
            ]
        )

        await connection.commit()

    logger.info(f"End handler with result: {result}")
    return result


def handler(event: dict[Any, Any], context: LambdaContext) -> WorkerOutput:
    return asyncio.run(main(event, context))
