from typing import Optional

import boto3

from worker.utils.types import SSMParameter


def read_ssm_parameter(path: str) -> Optional[SSMParameter]:
    ssm_client = boto3.client("ssm")
    response = ssm_client.get_parameters_by_path(
        Path=path,
        Recursive=False,
        MaxResults=1,
    )

    if "Parameters" in response and response["Parameters"]:
        return response["Parameters"][0]

    return None
