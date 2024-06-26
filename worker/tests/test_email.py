from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from jinja2 import DebugUndefined, Environment
from jinja2.exceptions import TemplateSyntaxError

from src.email import render_email, render_template_from_string, send_email
from src.types import (
    MailgunCredentials,
    RenderedScheduledEmail,
    ScheduledEmail,
    ScheduledEmailStatus,
)


def test_render_template_from_string() -> None:
    # Arrange
    engine = Environment(autoescape=True, undefined=DebugUndefined)
    template = "Hello {{ name }}!"
    context = {"name": "John Doe"}

    # Act
    result = render_template_from_string(engine, template, context)

    # Assert
    assert result == "Hello John Doe!"


def test_render_template_from_string__syntax_error() -> None:
    # Arrange
    engine = Environment(autoescape=True, undefined=DebugUndefined)
    template = "Hello {{ name }!"
    context = {"name": "John Doe"}

    # Act & Assert
    with pytest.raises(TemplateSyntaxError):
        render_template_from_string(engine, template, context)


def test_render_template_from_string__missing_context() -> None:
    # Arrange
    engine = Environment(autoescape=True, undefined=DebugUndefined)
    template = "Hello {{ name }}!"
    context: dict[str, Any] = {}

    # Act
    result = render_template_from_string(engine, template, context)

    # Assert
    assert result == "Hello {{ name }}!"  # no warning, no error


def test_render_email() -> None:
    # Arrange
    engine = Environment(autoescape=True, undefined=DebugUndefined)
    id_ = uuid4()
    now_ = datetime.now(tz=UTC)
    email = ScheduledEmail(
        pk=id_,
        created_at=now_,
        last_updated_at=now_,
        state=ScheduledEmailStatus.SCHEDULED,
        scheduled_at=now_,
        to_header=[],
        to_header_context_json=[],
        from_header="",
        reply_to_header="",
        cc_header=[],
        bcc_header=[],
        subject="Hello World and {{ name }}!",
        body="Welcome, {{ name }}!",
        context_json={},
        template="Welcome email",
    )
    context = {"name": "John Doe"}
    recipients = ["jdoe@example.com", ""]  # empty string should be filtered out

    # Act
    result = render_email(engine, email, context, recipients)

    # Assert
    assert result == RenderedScheduledEmail(
        **email.model_dump(),
        to_header_rendered=["jdoe@example.com"],
        subject_rendered="Hello World and John Doe!",
        body_rendered="Welcome, John Doe!",
    )


@pytest.mark.asyncio
async def test_send_email() -> None:
    # Arrange
    client = AsyncMock()
    id_ = uuid4()
    now_ = datetime.now(tz=UTC)
    email = RenderedScheduledEmail(
        pk=id_,
        created_at=now_,
        last_updated_at=now_,
        state=ScheduledEmailStatus.SCHEDULED,
        scheduled_at=now_,
        to_header=[],
        to_header_context_json=[],
        to_header_rendered=["jdoe@example.com"],
        from_header="",
        reply_to_header="",
        cc_header=[],
        bcc_header=[],
        subject="Hello World and {{ name }}!",
        subject_rendered="Hello World and John Doe!",
        body="Welcome, {{ name }}!",
        body_rendered="Welcome, John Doe!",
        context_json={},
        template="Welcome email",
    )
    credentials = MailgunCredentials(
        MAILGUN_SENDER_DOMAIN="example.com",
        MAILGUN_API_KEY="secret",
    )
    overwrite_outgoing_emails = None

    # Act
    await send_email(client, email, credentials, overwrite_outgoing_emails)

    # Assert
    client.post.assert_awaited_once_with(
        f"https://api.mailgun.net/v3/{credentials.MAILGUN_SENDER_DOMAIN}/messages",
        auth=("api", credentials.MAILGUN_API_KEY),
        data={
            "from": email.from_header,
            "to": email.to_header_rendered,
            "h:Reply-To": email.reply_to_header,
            "cc": email.cc_header,
            "bcc": email.bcc_header,
            "subject": email.subject_rendered,
            "html": email.body_rendered,
        },
    )


@pytest.mark.asyncio
async def test_send_email__outgoing_addresses_overwritten() -> None:
    # Arrange
    client = AsyncMock()
    id_ = uuid4()
    now_ = datetime.now(tz=UTC)
    email = RenderedScheduledEmail(
        pk=id_,
        created_at=now_,
        last_updated_at=now_,
        state=ScheduledEmailStatus.SCHEDULED,
        scheduled_at=now_,
        to_header=["test1@example.com"],
        to_header_context_json=[],
        to_header_rendered=["jdoe@example.com"],
        from_header="from@example.com",
        reply_to_header="reply_to@example.com",
        cc_header=["test2@example.com"],
        bcc_header=["test3@example.com"],
        subject="Hello World and {{ name }}!",
        subject_rendered="Hello World and John Doe!",
        body="Welcome, {{ name }}!",
        body_rendered="Welcome, John Doe!",
        context_json={},
        template="Welcome email",
    )
    credentials = MailgunCredentials(
        MAILGUN_SENDER_DOMAIN="example.com",
        MAILGUN_API_KEY="secret",
    )
    overwrite_outgoing_emails = "safe_mailing_group@example.com"

    # Act
    await send_email(client, email, credentials, overwrite_outgoing_emails)

    # Assert
    client.post.assert_awaited_once_with(
        f"https://api.mailgun.net/v3/{credentials.MAILGUN_SENDER_DOMAIN}/messages",
        auth=("api", credentials.MAILGUN_API_KEY),
        data={
            "from": email.from_header,
            "to": ["safe_mailing_group@example.com"],
            "h:Reply-To": email.reply_to_header,
            "cc": [],
            "bcc": [],
            "subject": email.subject_rendered,
            "html": email.body_rendered,
        },
    )
