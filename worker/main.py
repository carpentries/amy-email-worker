import logging

import psycopg
from aws_lambda_powertools.utilities.typing import LambdaContext
from psycopg.rows import dict_row

from utils.database import (
    connection_string,
    fetch_scheduled_emails,
    read_database_credentials_from_ssm,
)
from utils.settings import read_settings_from_env
from utils.types import WorkerOutput

logger = logging.getLogger()
logger.setLevel(logging.INFO)  # use logging.DEBUG to see boto3 logs


def handler(event: dict, context: LambdaContext) -> WorkerOutput:
    logger.info(f"Start handler with arguments: {event=}, {context=}")

    settings = read_settings_from_env()
    stage = settings["STAGE"]
    database_credentials = read_database_credentials_from_ssm(stage)

    logger.info("Obtained credentials for database.")

    result: WorkerOutput = {"scheduled_emails": []}

    with psycopg.connect(
        connection_string(database_credentials), row_factory=dict_row
    ) as connection:
        with connection.cursor() as cur:
            emails = fetch_scheduled_emails(cur)
            result["scheduled_emails"] = emails

    logger.info(f"End handler with result: {result}")
    return result
