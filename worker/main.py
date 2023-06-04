import logging

from aws_lambda_powertools.utilities.typing import LambdaContext

from worker.utils.settings import read_settings_from_env
from worker.utils.ssm import read_ssm_parameter
from worker.utils.types import WorkerOutput

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


def handler(event: dict, context: LambdaContext) -> WorkerOutput:
    logger.debug(f"Start handler with arguments: {event=}, {context=}")

    settings = read_settings_from_env()
    stage = settings["stage"]

    database_host = read_ssm_parameter(f"/{stage}/amy/database_host")
    # database_port = read_ssm_parameter(f'/{stage}/amy/database_port')
    # database_name = read_ssm_parameter(f'/{stage}/amy/database_name')
    # database_user = read_ssm_parameter(f'/{stage}/amy/database_user')
    # database_password = read_ssm_parameter(f'/{stage}/amy/database_password')

    logger.debug(f"{database_host=}")

    result: WorkerOutput = {"message": "Hello World"}
    logger.debug("End handler with result: {result}")
    return result
