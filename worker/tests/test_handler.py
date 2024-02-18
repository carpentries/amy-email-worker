from datetime import datetime
from unittest.mock import ANY, AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import HTTPStatusError

from src.handler import handle_email, return_fail_email
from src.types import (
    AuthToken,
    MailgunCredentials,
    ScheduledEmail,
    ScheduledEmailStatus,
)


@pytest.fixture
def scheduled_email() -> ScheduledEmail:
    id_ = uuid4()
    now_ = datetime.utcnow()
    return ScheduledEmail(
        id=id_,
        created_at=now_,
        last_updated_at=now_,
        state=ScheduledEmailStatus.SCHEDULED,
        scheduled_at=now_,
        to_header=[],
        to_header_context_json='[{"api_uri": "api:person#1", "property": "email"}]',
        from_header="",
        reply_to_header="",
        cc_header=[],
        bcc_header=[],
        subject="Hello World and {{ name }}!",
        body="Welcome, {{ name }}!",
        context_json='{"name": "value:str#John Doe"}',
        template_id=id_,
    )


@pytest.mark.asyncio
@patch("src.handler.fail_email")
async def test_return_fail_email(
    mock_fail_email: AsyncMock, scheduled_email: ScheduledEmail
) -> None:
    # Arrange
    details = "Failed to read JSON from email context."
    cursor = AsyncMock()
    mock_fail_email.return_value = scheduled_email

    # Act
    result = await return_fail_email(scheduled_email, details, cursor)

    # Assert
    mock_fail_email.assert_awaited_once_with(scheduled_email, details, cursor)

    # no point in testing the values since they would be from `mock_fail_email`
    assert result.keys() == {"email", "status"}


@pytest.mark.asyncio
@patch("src.handler.update_email_state")
@patch("src.handler.succeed_email")
@patch("src.handler.send_email")
@patch("src.handler.fetch_model_field")
@patch("src.handler.lock_email")
async def test_handle_email__happy_path(
    mock_lock_email: AsyncMock,
    mock_fetch_model_field: AsyncMock,
    mock_send_email: AsyncMock,
    mock_succeed_email: AsyncMock,
    mock_update_email_state: AsyncMock,
    scheduled_email: ScheduledEmail,
    token: AuthToken,
) -> None:
    # Arrange
    mailgun_credentials = MailgunCredentials(
        MAILGUN_SENDER_DOMAIN="example.com",
        MAILGUN_API_KEY="key-1234567890",
    )
    overwrite_outgoing_emails = "test-ml@example.com"
    cursor = AsyncMock()
    client = AsyncMock()
    mock_lock_email.return_value = scheduled_email
    mock_fetch_model_field.return_value = "person@example.org"
    mock_send_email.return_value.content = {
        "message": "Queued. Thank you.",
        "id": "<20111114174239.25659.5817@samples.mailgun.org>",
    }
    mock_send_email.return_value.raise_for_status = MagicMock()
    mock_succeed_email.return_value = scheduled_email
    mock_update_email_state.return_value = scheduled_email

    # Act
    result = await handle_email(
        scheduled_email,
        mailgun_credentials,
        overwrite_outgoing_emails,
        cursor,
        client,
        token,
    )

    # Assert
    assert result == {
        "email": scheduled_email.model_dump(mode="json"),
        "status": scheduled_email.state.value,
    }
    mock_lock_email.assert_awaited_once_with(scheduled_email, cursor)
    mock_fetch_model_field.assert_awaited_once_with(
        "api:person#1", "email", client, token
    )
    mock_send_email.assert_awaited_once_with(
        client,
        ANY,
        mailgun_credentials,
        overwrite_outgoing_emails=overwrite_outgoing_emails,
    )
    mock_send_email.return_value.raise_for_status.assert_called_once()
    mock_succeed_email.assert_awaited_once_with(
        scheduled_email, "Email sent successfully.", cursor
    )
    mock_update_email_state.assert_awaited_once()


@pytest.mark.asyncio
@patch("src.database.update_email_state")
@patch("src.handler.lock_email")
async def test_handle_email__invalid_context_json(
    mock_lock_email: AsyncMock,
    mock_update_email_state: AsyncMock,
    scheduled_email: ScheduledEmail,
    token: AuthToken,
) -> None:
    # Arrange
    scheduled_email.context_json = "{"  # invalid JSON
    failed_email = scheduled_email.model_copy(
        update={"state": ScheduledEmailStatus.FAILED}
    )
    mailgun_credentials = MailgunCredentials(
        MAILGUN_SENDER_DOMAIN="example.com",
        MAILGUN_API_KEY="key-1234567890",
    )
    overwrite_outgoing_emails = "test-ml@example.com"
    cursor = AsyncMock()
    client = AsyncMock()
    mock_lock_email.return_value = scheduled_email
    mock_update_email_state.return_value = failed_email

    # Act
    result = await handle_email(
        scheduled_email,
        mailgun_credentials,
        overwrite_outgoing_emails,
        cursor,
        client,
        token,
    )

    # Assert
    assert result == {
        "email": failed_email.model_dump(mode="json"),
        "status": failed_email.state.value,
    }
    mock_lock_email.assert_awaited_once_with(scheduled_email, cursor)
    mock_update_email_state.assert_awaited_once_with(
        scheduled_email, ScheduledEmailStatus.FAILED, cursor, details=ANY
    )


@pytest.mark.asyncio
@patch("src.database.update_email_state")
@patch("src.handler.lock_email")
async def test_handle_email__invalid_to_header_context_json(
    mock_lock_email: AsyncMock,
    mock_update_email_state: AsyncMock,
    scheduled_email: ScheduledEmail,
    token: AuthToken,
) -> None:
    # Arrange
    scheduled_email.to_header_context_json = "{"  # invalid JSON
    failed_email = scheduled_email.model_copy(
        update={"state": ScheduledEmailStatus.FAILED}
    )
    mailgun_credentials = MailgunCredentials(
        MAILGUN_SENDER_DOMAIN="example.com",
        MAILGUN_API_KEY="key-1234567890",
    )
    overwrite_outgoing_emails = "test-ml@example.com"
    cursor = AsyncMock()
    client = AsyncMock()
    mock_lock_email.return_value = scheduled_email
    mock_update_email_state.return_value = failed_email

    # Act
    result = await handle_email(
        scheduled_email,
        mailgun_credentials,
        overwrite_outgoing_emails,
        cursor,
        client,
        token,
    )

    # Assert
    assert result == {
        "email": failed_email.model_dump(mode="json"),
        "status": failed_email.state.value,
    }
    mock_lock_email.assert_awaited_once_with(scheduled_email, cursor)
    mock_update_email_state.assert_awaited_once_with(
        scheduled_email, ScheduledEmailStatus.FAILED, cursor, details=ANY
    )


@pytest.mark.asyncio
@patch("src.database.update_email_state")
@patch("src.handler.lock_email")
async def test_handle_email__unsupported_context_uri(
    mock_lock_email: AsyncMock,
    mock_update_email_state: AsyncMock,
    scheduled_email: ScheduledEmail,
    token: AuthToken,
) -> None:
    # Arrange
    scheduled_email.context_json = '{"name": "unsupported#John Doe"}'
    failed_email = scheduled_email.model_copy(
        update={"state": ScheduledEmailStatus.FAILED}
    )
    mailgun_credentials = MailgunCredentials(
        MAILGUN_SENDER_DOMAIN="example.com",
        MAILGUN_API_KEY="key-1234567890",
    )
    overwrite_outgoing_emails = "test-ml@example.com"
    cursor = AsyncMock()
    client = AsyncMock()
    mock_lock_email.return_value = scheduled_email
    mock_update_email_state.return_value = failed_email

    # Act
    result = await handle_email(
        scheduled_email,
        mailgun_credentials,
        overwrite_outgoing_emails,
        cursor,
        client,
        token,
    )

    # Assert
    assert result == {
        "email": failed_email.model_dump(mode="json"),
        "status": failed_email.state.value,
    }
    mock_lock_email.assert_awaited_once_with(scheduled_email, cursor)
    mock_update_email_state.assert_awaited_once_with(
        scheduled_email,
        ScheduledEmailStatus.FAILED,
        cursor,
        details=(
            "Issue when generating context: Unsupported URI 'unsupported#John Doe' "
            "for context generation."
        ),
    )


@pytest.mark.asyncio
@patch("src.database.update_email_state")
@patch("src.handler.lock_email")
async def test_handle_email__invalid_recipients(
    mock_lock_email: AsyncMock,
    mock_update_email_state: AsyncMock,
    scheduled_email: ScheduledEmail,
    token: AuthToken,
) -> None:
    # Arrange
    scheduled_email.to_header_context_json = (
        '[{"api_uri": "unsupported#John Doe", "property": "email"}]'
    )
    failed_email = scheduled_email.model_copy(
        update={"state": ScheduledEmailStatus.FAILED}
    )
    mailgun_credentials = MailgunCredentials(
        MAILGUN_SENDER_DOMAIN="example.com",
        MAILGUN_API_KEY="key-1234567890",
    )
    overwrite_outgoing_emails = "test-ml@example.com"
    cursor = AsyncMock()
    client = AsyncMock()
    mock_lock_email.return_value = scheduled_email
    mock_update_email_state.return_value = failed_email

    # Act
    result = await handle_email(
        scheduled_email,
        mailgun_credentials,
        overwrite_outgoing_emails,
        cursor,
        client,
        token,
    )

    # Assert
    assert result == {
        "email": failed_email.model_dump(mode="json"),
        "status": failed_email.state.value,
    }
    mock_lock_email.assert_awaited_once_with(scheduled_email, cursor)
    mock_update_email_state.assert_awaited_once_with(
        scheduled_email,
        ScheduledEmailStatus.FAILED,
        cursor,
        details=(
            f"Issue when generating email {scheduled_email.id} recipients: "
            "Unsupported URI 'unsupported#John Doe'."
        ),
    )


@pytest.mark.asyncio
@patch("src.database.update_email_state")
@patch("src.handler.fetch_model_field")
@patch("src.handler.lock_email")
async def test_handle_email__invalid_jinja2_template(
    mock_lock_email: AsyncMock,
    mock_fetch_model_field: AsyncMock,
    mock_update_email_state: AsyncMock,
    scheduled_email: ScheduledEmail,
    token: AuthToken,
) -> None:
    # Arrange
    scheduled_email.subject = "{{ invalid_syntax }"
    failed_email = scheduled_email.model_copy(
        update={"state": ScheduledEmailStatus.FAILED}
    )
    mailgun_credentials = MailgunCredentials(
        MAILGUN_SENDER_DOMAIN="example.com",
        MAILGUN_API_KEY="key-1234567890",
    )
    overwrite_outgoing_emails = "test-ml@example.com"
    cursor = AsyncMock()
    client = AsyncMock()
    mock_lock_email.return_value = scheduled_email
    mock_fetch_model_field.return_value = "person@example.org"
    mock_update_email_state.return_value = failed_email

    # Act
    result = await handle_email(
        scheduled_email,
        mailgun_credentials,
        overwrite_outgoing_emails,
        cursor,
        client,
        token,
    )

    # Assert
    assert result == {
        "email": failed_email.model_dump(mode="json"),
        "status": failed_email.state.value,
    }
    mock_lock_email.assert_awaited_once_with(scheduled_email, cursor)
    mock_update_email_state.assert_awaited_once_with(
        scheduled_email,
        ScheduledEmailStatus.FAILED,
        cursor,
        details=(
            f"Failed to render email {scheduled_email.id}. Error: unexpected '}}'"
        ),
    )


@pytest.mark.asyncio
@patch("src.database.update_email_state")
@patch("src.handler.send_email")
@patch("src.handler.fetch_model_field")
@patch("src.handler.lock_email")
async def test_handle_email__mailgun_error(
    mock_lock_email: AsyncMock,
    mock_fetch_model_field: AsyncMock,
    mock_send_email: AsyncMock,
    mock_update_email_state: AsyncMock,
    scheduled_email: ScheduledEmail,
    token: AuthToken,
) -> None:
    # Arrange
    failed_email = scheduled_email.model_copy(
        update={"state": ScheduledEmailStatus.FAILED}
    )
    mailgun_credentials = MailgunCredentials(
        MAILGUN_SENDER_DOMAIN="example.com",
        MAILGUN_API_KEY="key-1234567890",
    )
    overwrite_outgoing_emails = "test-ml@example.com"
    cursor = AsyncMock()
    client = AsyncMock()
    mock_lock_email.return_value = scheduled_email
    mock_fetch_model_field.return_value = "person@example.org"
    mock_send_email.return_value.raise_for_status = MagicMock(
        side_effect=HTTPStatusError("test", request=MagicMock(), response=MagicMock())
    )
    mock_update_email_state.return_value = failed_email

    # Act
    result = await handle_email(
        scheduled_email,
        mailgun_credentials,
        overwrite_outgoing_emails,
        cursor,
        client,
        token,
    )

    # Assert
    assert result == {
        "email": failed_email.model_dump(mode="json"),
        "status": failed_email.state.value,
    }
    mock_lock_email.assert_awaited_once_with(scheduled_email, cursor)
    mock_update_email_state.assert_awaited_once_with(
        scheduled_email,
        ScheduledEmailStatus.FAILED,
        cursor,
        details=(f"Failed to send email {scheduled_email.id}. Error: test"),
    )
