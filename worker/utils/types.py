from datetime import datetime
from enum import Enum
from typing import Literal, Optional, TypedDict
from uuid import UUID


class WorkerOutput(TypedDict):
    scheduled_emails: list["ScheduledEmail"]


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


class ScheduledEmailStatus(Enum):
    SCHEDULED = "scheduled"
    LOCKED = "locked"
    RUNNING = "running"
    SUCCEEDED = "succeded"
    FAILED = "failed"


class ScheduledEmail(TypedDict):
    id: UUID
    created_at: datetime
    last_updated_at: Optional[datetime]
    state: ScheduledEmailStatus
    scheduled_at: datetime
    to_header: list[str]
    from_header: str
    reply_to_header: str
    cc_header: list[str]
    bcc_header: list[str]
    subject: str
    body: str
    template: UUID
