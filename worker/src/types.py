from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Literal, Optional, TypedDict
from uuid import UUID

from pydantic import BaseModel, ConfigDict, RootModel

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
    API_BASE_URL: str


@dataclass(frozen=True)
class MailgunCredentials:
    MAILGUN_SENDER_DOMAIN: str
    MAILGUN_API_KEY: str


@dataclass(frozen=True)
class Credentials:
    USER: str
    PASSWORD: str


class ScheduledEmailStatus(Enum):
    SCHEDULED = "scheduled"
    LOCKED = "locked"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ScheduledEmail(BaseModel):
    pk: UUID
    created_at: datetime
    last_updated_at: Optional[datetime]
    state: ScheduledEmailStatus
    scheduled_at: datetime
    to_header: list[str]

    # JSON, e.g. '[{"api_uri": "api:person#1", "property": "email"}]'
    to_header_context_json: list[dict[str, Any]]
    from_header: str
    reply_to_header: str
    cc_header: list[str]
    bcc_header: list[str]
    subject: str
    body: str
    context_json: dict[str, Any]  # JSON, e.g. '{"name": "John Doe"}'
    template: str  # template name


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


class AuthToken(BaseModel):
    model_config = ConfigDict(frozen=True)

    expiry: datetime
    token: str

    def has_expired(self, current_time: datetime, delta: timedelta) -> bool:
        """
        Check if the token has expired.

        If `delta` is provided, the token is considered expired if it expired
        `delta` time ago from `current_time`.
        This is useful for checking if a token is about to expire soon.
        """
        return self.expiry < (current_time + delta)
