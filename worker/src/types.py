from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional, TypedDict
from uuid import UUID

from pydantic import BaseModel, RootModel

BasicTypes = str | int | float | bool | None
Stage = Literal["prod", "staging"]


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
    STAGE: Stage
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
    to_header_context_json: str  # JSON, TODO: validate what API/DRF returns
    from_header: str
    reply_to_header: str
    cc_header: list[str]
    bcc_header: list[str]
    subject: str
    body: str
    context_json: str  # JSON, TODO: validate what API/DRF returns
    template_id: UUID


class RenderedScheduledEmail(ScheduledEmail):
    to_header_rendered: list[str]
    subject_rendered: str
    body_rendered: str


class WorkerOutputEmail(TypedDict):
    email: dict[str, Any]
    status: str


class WorkerOutput(TypedDict):
    emails: list[WorkerOutputEmail]


class SinglePropertyLinkModel(BaseModel):
    # custom URI for links to individual models in API, e.g. "api:person#1234"
    api_uri: str
    property: str


ToHeaderModel = RootModel[list[SinglePropertyLinkModel]]

ContextModel = RootModel[dict[str, str | list[str]]]
