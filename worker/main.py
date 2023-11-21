import logging

import psycopg
from aws_lambda_powertools.utilities.typing import LambdaContext
from psycopg.rows import dict_row

from utils.database import (
    connection_string,
    fail_email,
    fetch_scheduled_emails_to_run,
    lock_email,
    read_database_credentials_from_ssm,
    succeed_email,
    update_email_state,
)
from utils.email import send_email
from utils.settings import read_mailgun_credentials, read_settings_from_env
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

    mailgun_credentials = read_mailgun_credentials(stage)
    logger.info("Obtained credentials for Mailgun.")

    result: WorkerOutput = {"emails": []}

    with psycopg.connect(
        connection_string(database_credentials), row_factory=dict_row
    ) as connection:
        with connection.cursor() as cur:
            emails = fetch_scheduled_emails_to_run(cur)

            for email in emails:
                id = email.id
                logger.info(f"Working on email {id}.")

                updated_email = lock_email(email, cur)
                logger.info(f"Locked email {id}. Attempting to send.")

                try:
                    response = send_email(
                        updated_email,
                        mailgun_credentials,
                        overwrite_outgoing_emails=settings.OVERWRITE_OUTGOING_EMAILS,
                    )
                    logger.info(f"Sent email {id}.")
                    logger.info(f"Mailgun response: {response=}")
                    logger.info(f"Response content: {response.content}")
                    response.raise_for_status()

                except Exception as exc:
                    logger.info(f"Failed to send email {id}. Error: {exc}")
                    failed_email = fail_email(
                        updated_email, f"Email failed to send. Error: {exc}", cur
                    )
                    result["emails"].append(
                        {
                            "email": failed_email.model_dump(),
                            "status": failed_email.state,
                        }
                    )

                else:
                    succeeded_email = succeed_email(
                        updated_email, "Email sent successfully.", cur
                    )
                    update_email_state(
                        succeeded_email,
                        succeeded_email.state,
                        cur,
                        details=f"Mailgun response: {response.content}",
                    )
                    result["emails"].append(
                        {
                            "email": succeeded_email.model_dump(),
                            "status": succeeded_email.state,
                        }
                    )

        connection.commit()

    logger.info(f"End handler with result: {result}")
    return result
