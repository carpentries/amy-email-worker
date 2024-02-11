import asyncio
import logging
from typing import Any

import httpx
import psycopg
from aws_lambda_powertools.utilities.typing import LambdaContext
from psycopg.rows import dict_row

from src.database import (
    connection_string,
    fetch_scheduled_emails_to_run,
    read_database_credentials_from_ssm,
)
from src.handler import handle_email
from src.settings import STAGE, SETTINGS, read_mailgun_credentials
from src.types import WorkerOutput

logging.basicConfig()
logger = logging.getLogger("amy-email-worker")
logger.setLevel(logging.INFO)  # use logging.DEBUG to see boto3 logs


# TODO:
# 1. rewrite to async ✅
# 2. make sure tests pass (even with async on) ✅
# 3. add mapping for API endpoints ✅
# 4. fetch and render emails ✅
# 5. write unit tests! ✅
# 6. create new simplified API in AMY ✅
# 7. use authentication in the new API ✅
# 8. use authentication in the worker
# 9. create schemas for the endpoints
# 10. add endpoints for managing emails
# 11. rewrite email logic from handler below to use the new email endpoints


async def main(event: dict[Any, Any], context: LambdaContext) -> WorkerOutput:
    logger.info(f"Start handler with arguments: {event=}, {context=}")

    overwrite_outgoing_emails = SETTINGS.OVERWRITE_OUTGOING_EMAILS
    logger.info(f"Stage: {STAGE}")
    logger.info(f"Outgoing emails override: {overwrite_outgoing_emails}")

    database_credentials = read_database_credentials_from_ssm()
    logger.info("Obtained credentials for database.")

    mailgun_credentials = read_mailgun_credentials()
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
