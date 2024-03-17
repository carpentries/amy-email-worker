from typing import Optional, cast

import boto3

from src.types import SSMParameter


# TODO: turn into async, perhaps use aioboto3 for that
def read_ssm_parameter(path: str) -> Optional[SSMParameter]:
    ssm_client = boto3.client("ssm")
    response = ssm_client.get_parameter(Name=path)

    if "Parameter" in response and response["Parameter"]:
        return cast(SSMParameter, response["Parameter"])

    return None


def get_parameter_value(parameter: SSMParameter) -> str:
    return parameter.get("Value", "")
