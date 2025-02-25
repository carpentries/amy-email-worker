from io import BytesIO
from typing import Optional, cast

import boto3

from src.types import SSMParameter

ssm_client = boto3.client("ssm")
s3_client = boto3.client("s3")


# TODO: turn into async, perhaps use aioboto3 for that
def read_ssm_parameter(path: str) -> Optional[SSMParameter]:
    response = ssm_client.get_parameter(Name=path)

    if "Parameter" in response and response["Parameter"]:
        return cast(SSMParameter, response["Parameter"])

    return None


def get_parameter_value(parameter: SSMParameter) -> str:
    return parameter.get("Value", "")


def inmemory_s3_download(bucket: str, path: str) -> bytes:
    bytes = BytesIO()
    s3_client.download_fileobj(Bucket=bucket, Key=path, Fileobj=bytes)

    bytes.seek(0)
    file_contents = bytes.read()
    bytes.close()

    return file_contents
