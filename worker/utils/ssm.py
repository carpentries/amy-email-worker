from typing import Optional

import boto3
from utils.types import SSMParameter


def read_ssm_parameter(path: str) -> Optional[SSMParameter]:
    ssm_client = boto3.client("ssm")
    response = ssm_client.get_parameter(Name=path)

    if "Parameter" in response and response["Parameter"]:
        return response["Parameter"]

    return None


def get_parameter_value(parameter: SSMParameter) -> str:
    return parameter.get("Value", "")
