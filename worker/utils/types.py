from datetime import datetime
from typing import Literal, TypedDict


class WorkerOutput(TypedDict):
    message: str


class SSMParameter(TypedDict, total=False):
    Name: str
    Type: Literal["String", "StringList", "SecureString"]
    Value: str
    Version: int
    Selector: str
    SourceResult: str
    LastModifiedDate: datetime
    ARN: str
    DataType: str


class Settings(TypedDict):
    STAGE: str
    OVERWRITE_OUTGOING_EMAILS: str


class DatabaseCredentials(TypedDict):
    host: str
    port: str
    name: str
    user: str
    password: str
