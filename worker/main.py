import logging

from aws_lambda_powertools.utilities.typing import LambdaContext
from utils.settings import read_settings_from_env
from utils.ssm import read_ssm_parameter
from utils.types import WorkerOutput

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event: dict, context: LambdaContext) -> WorkerOutput:
    logger.info(f"Start handler with arguments: {event=}, {context=}")

    settings = read_settings_from_env()
    stage = settings["stage"]

    database_host = read_ssm_parameter(f"/{stage}/amy/database_host")
    # database_port = read_ssm_parameter(f'/{stage}/amy/database_port')
    # database_name = read_ssm_parameter(f'/{stage}/amy/database_name')
    # database_user = read_ssm_parameter(f'/{stage}/amy/database_user')
    # database_password = read_ssm_parameter(f'/{stage}/amy/database_password')

    logger.info(f"{database_host=}")

    result: WorkerOutput = {"message": "Hello World"}
    logger.info("End handler with result: {result}")
    return result
