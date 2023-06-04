import logging

from aws_lambda_powertools.utilities.typing import LambdaContext
from utils.database import read_database_credentials_from_ssm
from utils.settings import read_settings_from_env
from utils.types import WorkerOutput

logger = logging.getLogger()
logger.setLevel(logging.INFO)  # use logging.DEBUG to see boto3 logs


def handler(event: dict, context: LambdaContext) -> WorkerOutput:
    logger.info(f"Start handler with arguments: {event=}, {context=}")

    settings = read_settings_from_env()
    stage = settings["stage"]
    database_credentials = read_database_credentials_from_ssm(stage)

    logger.info(f"{database_credentials['host']=}")

    result: WorkerOutput = {"message": "Hello World"}
    logger.info(f"End handler with result: {result}")
    return result
