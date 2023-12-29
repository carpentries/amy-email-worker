from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional, TypedDict
from uuid import UUID

from pydantic import BaseModel


class NotFoundError(Exception):
    pass


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


@dataclass(frozen=True)
class Settings:
    STAGE: str
    OVERWRITE_OUTGOING_EMAILS: str


@dataclass(frozen=True)
class MailgunCredentials:
    MAILGUN_SENDER_DOMAIN: str
    MAILGUN_API_KEY: str


@dataclass(frozen=True)
class DatabaseCredentials:
    HOST: str
    PORT: str
    USER: str
    PASSWORD: str
    NAME: str


class ScheduledEmailStatus(Enum):
    SCHEDULED = "scheduled"
    LOCKED = "locked"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ScheduledEmail(BaseModel):
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
    template_id: UUID


class WorkerOutputEmail(TypedDict):
    email: dict[str, dict[str, Any] | ScheduledEmailStatus]
    status: ScheduledEmailStatus


class WorkerOutput(TypedDict):
    emails: list[WorkerOutputEmail]
