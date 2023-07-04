from datetime import datetime
from enum import Enum
from typing import Literal, Optional, TypedDict
from uuid import UUID


class NotFoundError(Exception):
    pass


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
    SUCCEEDED = "succeeded"
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


def to_scheduled_email(d: dict) -> ScheduledEmail:
    return {
        "id": d["id"],
        "created_at": d["created_at"],
        "last_updated_at": d["last_updated_at"],
        "state": ScheduledEmailStatus(d["state"]),
        "scheduled_at": d["scheduled_at"],
        "to_header": d["to_header"],
        "from_header": d["from_header"],
        "reply_to_header": d["reply_to_header"],
        "cc_header": d["cc_header"],
        "bcc_header": d["bcc_header"],
        "subject": d["subject"],
        "body": d["body"],
        "template": d["template_id"],
    }
