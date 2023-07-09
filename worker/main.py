import logging

import psycopg
from aws_lambda_powertools.utilities.typing import LambdaContext
from psycopg.rows import dict_row

from utils.database import (
    connection_string,
    fail_email,
    fetch_scheduled_emails,
    lock_email,
    read_database_credentials_from_ssm,
    succeed_email,
)
from utils.settings import read_settings_from_env
from utils.types import WorkerOutput

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # use logging.DEBUG to see boto3 logs


def handler(event: dict, context: LambdaContext) -> WorkerOutput:
    logger.info(f"Start handler with arguments: {event=}, {context=}")

    settings = read_settings_from_env()
    stage = settings.STAGE
    database_credentials = read_database_credentials_from_ssm(stage)

    logger.info("Obtained credentials for database.")

    result: WorkerOutput = {"scheduled_emails": []}

    with psycopg.connect(
        connection_string(database_credentials), row_factory=dict_row
    ) as connection:
        with connection.cursor() as cur:
            emails = fetch_scheduled_emails(cur)
            result["scheduled_emails"] = emails

            for email in emails:
                id = email["id"]
                logger.info(f"Working on email {id}.")

                updated_email = lock_email(email, cur)
                logger.info(f"Locked email {id}. Attempting to send.")

                try:
                    send_email(updated_email)  # type: ignore
                    logger.info(f"Sent email {id}.")

                except Exception as exc:
                    logger.info(f"Failed to send email {id}. Error: {exc}")
                    fail_email(
                        updated_email, f"Email failed to send. Error: {exc}", cur
                    )

                else:
                    succeed_email(updated_email, "Email sent successfully.", cur)

        connection.commit()

    logger.info(f"End handler with result: {result}")
    return result
