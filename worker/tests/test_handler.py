from datetime import datetime, timezone
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from httpx import HTTPStatusError
import pytest

from src.handler import handle_email, return_fail_email
from src.token import TokenCache
from src.types import (
    Attachment,
    AttachmentWithContent,
    AuthToken,
    MailgunCredentials,
    RenderedScheduledEmail,
    ScheduledEmail,
    ScheduledEmailStatus,
)


@pytest.fixture
def scheduled_email() -> ScheduledEmail:
    id_ = uuid4()
    now_ = datetime.now(timezone.utc)
    return ScheduledEmail(
        pk=id_,
        created_at=now_,
        last_updated_at=now_,
        state=ScheduledEmailStatus.SCHEDULED,
        scheduled_at=now_,
        to_header=[],
        to_header_context_json=[{"api_uri": "api:person#1", "property": "email"}],
        from_header="",
        reply_to_header="",
        cc_header=[],
        bcc_header=[],
        subject="Hello World and {{ name }}!",
        body="Welcome, {{ name }}!\n\nNew paragraph.",
        context_json={"name": "value:str#John Doe"},
        template="Welcome email",
        attachments=[
            Attachment(
                filename="certificate.pdf",
                s3_path="certificates/random-person/certificate.pdf",
                s3_bucket="",
                presigned_url="",
                presigned_url_expiration=None,
            )
        ],
    )


@pytest.fixture
def mailgun_credentials() -> MailgunCredentials:
    return MailgunCredentials(
        MAILGUN_SENDER_DOMAIN="example.com",
        MAILGUN_API_KEY="key-1234567890",
    )


@pytest.fixture
def overwrite_outgoing_emails() -> str:
    return "test-ml@example.com"


@pytest.mark.asyncio
async def test_return_fail_email(scheduled_email: ScheduledEmail) -> None:
    # Arrange
    details = "Failed to read JSON from email context."
    controller = AsyncMock()
    controller.fail_by_id.return_value = scheduled_email

    # Act
    result = await return_fail_email(scheduled_email.pk, details, controller)

    # Assert
    controller.fail_by_id.assert_awaited_once_with(scheduled_email.pk, details=details)

    # no point in testing the values
    assert result.keys() == {"email", "status"}


@pytest.mark.asyncio
@patch("src.handler.send_email")
@patch("src.handler.fetch_model_field")
@patch("src.handler.read_attachment_from_s3")
async def test_handle_email__happy_path(
    mock_read_attachment_from_s3: MagicMock,
    mock_fetch_model_field: AsyncMock,
    mock_send_email: AsyncMock,
    token: AuthToken,
    scheduled_email: ScheduledEmail,
    mailgun_credentials: MailgunCredentials,
    overwrite_outgoing_emails: str,
) -> None:
    # Arrange
    client = AsyncMock()
    token_cache = TokenCache(client, token=token)
    controller = AsyncMock()
    controller.lock_by_id.return_value = scheduled_email
    controller.succeed_by_id.return_value = scheduled_email

    expected_rendered_email = RenderedScheduledEmail(
        **scheduled_email.model_dump(),
        to_header_rendered=["person@example.org"],
        subject_rendered="Hello World and John Doe!",
        body_rendered="<p>Welcome, John Doe!</p>\n<p>New paragraph.</p>",
        attachments_with_content=[AttachmentWithContent(filename="certificate.pdf", content=b"Test")],
    )

    mock_fetch_model_field.return_value = "person@example.org"
    mock_send_email.return_value.content = {
        "message": "Queued. Thank you.",
        "id": "<20111114174239.25659.5817@samples.mailgun.org>",
    }
    mock_send_email.return_value.raise_for_status = MagicMock()
    mock_read_attachment_from_s3.return_value = AttachmentWithContent(filename="certificate.pdf", content=b"Test")

    # Act
    result = await handle_email(
        scheduled_email,
        mailgun_credentials,
        overwrite_outgoing_emails,
        controller,
        client,
        token_cache,
    )

    # Assert
    assert result == {
        "email": scheduled_email.model_dump(mode="json"),
        "status": scheduled_email.state.value,
    }
    controller.lock_by_id.assert_awaited_once_with(scheduled_email.pk)
    mock_fetch_model_field.assert_awaited_once_with("api:person#1", "email", client, token)
    mock_send_email.assert_awaited_once_with(
        client,
        expected_rendered_email,
        mailgun_credentials,
        overwrite_outgoing_emails=overwrite_outgoing_emails,
    )
    mock_send_email.return_value.raise_for_status.assert_called_once()
    controller.succeed_by_id.assert_awaited_once_with(
        scheduled_email.pk,
        "Email sent successfully. Mailgun response: " f"{mock_send_email.return_value.content}",
    )


@pytest.mark.asyncio
async def test_handle_email__invalid_context_json(
    token: AuthToken,
    scheduled_email: ScheduledEmail,
    mailgun_credentials: MailgunCredentials,
    overwrite_outgoing_emails: str,
) -> None:
    # Arrange
    # forcing validation error
    scheduled_email.context_json = cast(dict[str, Any], "{")
    failed_email = scheduled_email.model_copy(update={"state": ScheduledEmailStatus.FAILED})
    client = AsyncMock()
    token_cache = TokenCache(client, token=token)
    controller = AsyncMock()
    controller.lock_by_id.return_value = scheduled_email
    controller.fail_by_id.return_value = failed_email

    # Act
    result = await handle_email(
        scheduled_email,
        mailgun_credentials,
        overwrite_outgoing_emails,
        controller,
        client,
        token_cache,
    )

    # Assert
    assert result == {
        "email": failed_email.model_dump(mode="json"),
        "status": failed_email.state.value,
    }
    controller.lock_by_id.assert_awaited_once_with(scheduled_email.pk)
    controller.fail_by_id.assert_awaited_once_with(
        scheduled_email.pk,
        details=f"Failed to read email context {scheduled_email.pk}.",
    )


@pytest.mark.asyncio
async def test_handle_email__invalid_to_header_context_json(
    token: AuthToken,
    scheduled_email: ScheduledEmail,
    mailgun_credentials: MailgunCredentials,
    overwrite_outgoing_emails: str,
) -> None:
    # Arrange
    # forcing validation error
    scheduled_email.to_header_context_json = cast(list[dict[str, Any]], "{")
    failed_email = scheduled_email.model_copy(update={"state": ScheduledEmailStatus.FAILED})
    client = AsyncMock()
    token_cache = TokenCache(client, token=token)
    controller = AsyncMock()
    controller.lock_by_id.return_value = scheduled_email
    controller.fail_by_id.return_value = failed_email

    # Act
    result = await handle_email(
        scheduled_email,
        mailgun_credentials,
        overwrite_outgoing_emails,
        controller,
        client,
        token_cache,
    )

    # Assert
    assert result == {
        "email": failed_email.model_dump(mode="json"),
        "status": failed_email.state.value,
    }
    controller.lock_by_id.assert_awaited_once_with(scheduled_email.pk)
    controller.fail_by_id.assert_awaited_once_with(
        scheduled_email.pk,
        details=f"Failed to read email recipients {scheduled_email.pk}.",
    )


@pytest.mark.asyncio
async def test_handle_email__unsupported_context_uri(
    token: AuthToken,
    scheduled_email: ScheduledEmail,
    mailgun_credentials: MailgunCredentials,
    overwrite_outgoing_emails: str,
) -> None:
    # Arrange
    scheduled_email.context_json = {"name": "unsupported#John Doe"}
    failed_email = scheduled_email.model_copy(update={"state": ScheduledEmailStatus.FAILED})
    client = AsyncMock()
    token_cache = TokenCache(client, token=token)
    controller = AsyncMock()
    controller.lock_by_id.return_value = scheduled_email
    controller.fail_by_id.return_value = failed_email

    # Act
    result = await handle_email(
        scheduled_email,
        mailgun_credentials,
        overwrite_outgoing_emails,
        controller,
        client,
        token_cache,
    )

    # Assert
    assert result == {
        "email": failed_email.model_dump(mode="json"),
        "status": failed_email.state.value,
    }
    controller.lock_by_id.assert_awaited_once_with(scheduled_email.pk)
    controller.fail_by_id.assert_awaited_once_with(
        scheduled_email.pk,
        details=("Issue when generating context: Unsupported URI 'unsupported#John Doe' " "for context generation."),
    )


@pytest.mark.asyncio
async def test_handle_email__api_error(
    token: AuthToken,
    scheduled_email: ScheduledEmail,
    mailgun_credentials: MailgunCredentials,
    overwrite_outgoing_emails: str,
) -> None:
    # Arrange
    scheduled_email.context_json = {"name": "api:person#1"}
    failed_email = scheduled_email.model_copy(update={"state": ScheduledEmailStatus.FAILED})
    client = AsyncMock()
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock(
        side_effect=HTTPStatusError("Client error '404 Not Found'", request=MagicMock(), response=MagicMock())
    )
    client.get.return_value = mock_response

    token_cache = TokenCache(client, token=token)
    controller = AsyncMock()
    controller.lock_by_id.return_value = scheduled_email
    controller.fail_by_id.return_value = failed_email

    # Act
    result = await handle_email(
        scheduled_email,
        mailgun_credentials,
        overwrite_outgoing_emails,
        controller,
        client,
        token_cache,
    )

    # Assert
    assert result == {
        "email": failed_email.model_dump(mode="json"),
        "status": failed_email.state.value,
    }
    controller.lock_by_id.assert_awaited_once_with(scheduled_email.pk)
    controller.fail_by_id.assert_awaited_once_with(
        scheduled_email.pk,
        details="Issue when generating context: Client error '404 Not Found'",
    )


@pytest.mark.asyncio
async def test_handle_email__invalid_recipients(
    token: AuthToken,
    scheduled_email: ScheduledEmail,
    mailgun_credentials: MailgunCredentials,
    overwrite_outgoing_emails: str,
) -> None:
    # Arrange
    scheduled_email.to_header_context_json = [{"api_uri": "unsupported#John Doe", "property": "email"}]
    failed_email = scheduled_email.model_copy(update={"state": ScheduledEmailStatus.FAILED})
    client = AsyncMock()
    token_cache = TokenCache(client, token=token)
    controller = AsyncMock()
    controller.lock_by_id.return_value = scheduled_email
    controller.fail_by_id.return_value = failed_email

    # Act
    result = await handle_email(
        scheduled_email,
        mailgun_credentials,
        overwrite_outgoing_emails,
        controller,
        client,
        token_cache,
    )

    # Assert
    assert result == {
        "email": failed_email.model_dump(mode="json"),
        "status": failed_email.state.value,
    }
    controller.lock_by_id.assert_awaited_once_with(scheduled_email.pk)
    controller.fail_by_id.assert_awaited_once_with(
        scheduled_email.pk,
        details=(
            f"Issue when generating email {scheduled_email.pk} recipients: " "Unsupported URI 'unsupported#John Doe'."
        ),
    )


@pytest.mark.asyncio
@patch("src.handler.fetch_model_field")
async def test_handle_email__invalid_jinja2_template(
    mock_fetch_model_field: AsyncMock,
    token: AuthToken,
    scheduled_email: ScheduledEmail,
    mailgun_credentials: MailgunCredentials,
    overwrite_outgoing_emails: str,
) -> None:
    # Arrange
    scheduled_email.subject = "{{ invalid_syntax }"
    failed_email = scheduled_email.model_copy(update={"state": ScheduledEmailStatus.FAILED})
    client = AsyncMock()
    token_cache = TokenCache(client, token=token)
    controller = AsyncMock()
    controller.lock_by_id.return_value = scheduled_email
    controller.fail_by_id.return_value = failed_email
    mock_fetch_model_field.return_value = "person@example.org"

    # Act
    result = await handle_email(
        scheduled_email,
        mailgun_credentials,
        overwrite_outgoing_emails,
        controller,
        client,
        token_cache,
    )

    # Assert
    assert result == {
        "email": failed_email.model_dump(mode="json"),
        "status": failed_email.state.value,
    }
    controller.lock_by_id.assert_awaited_once_with(scheduled_email.pk)
    controller.fail_by_id.assert_awaited_once_with(
        scheduled_email.pk,
        details=(f"Failed to render email {scheduled_email.pk}. Error: unexpected '}}'"),
    )


@pytest.mark.asyncio
@patch("src.handler.send_email")
@patch("src.handler.fetch_model_field")
@patch("src.handler.read_attachment_from_s3")
async def test_handle_email__mailgun_error(
    mock_read_attachment_from_s3: MagicMock,
    mock_fetch_model_field: AsyncMock,
    mock_send_email: AsyncMock,
    token: AuthToken,
    scheduled_email: ScheduledEmail,
    mailgun_credentials: MailgunCredentials,
    overwrite_outgoing_emails: str,
) -> None:
    # Arrange
    failed_email = scheduled_email.model_copy(update={"state": ScheduledEmailStatus.FAILED})
    client = AsyncMock()
    token_cache = TokenCache(client, token=token)
    controller = AsyncMock()
    controller.lock_by_id.return_value = scheduled_email
    controller.fail_by_id.return_value = failed_email
    mock_fetch_model_field.return_value = "person@example.org"
    mock_send_email.return_value.raise_for_status = MagicMock(
        side_effect=HTTPStatusError("test", request=MagicMock(), response=MagicMock())
    )

    # Act
    result = await handle_email(
        scheduled_email,
        mailgun_credentials,
        overwrite_outgoing_emails,
        controller,
        client,
        token_cache,
    )

    # Assert
    assert result == {
        "email": failed_email.model_dump(mode="json"),
        "status": failed_email.state.value,
    }
    controller.lock_by_id.assert_awaited_once_with(scheduled_email.pk)
    controller.fail_by_id.assert_awaited_once_with(
        scheduled_email.pk,
        details=(f"Failed to send email {scheduled_email.pk}. Error: test"),
    )


@pytest.mark.asyncio
@patch("src.handler.fetch_model_field")
@patch("src.handler.read_attachment_from_s3")
async def test_handle_email__s3_error(
    mock_read_attachment_from_s3: MagicMock,
    mock_fetch_model_field: AsyncMock,
    token: AuthToken,
    scheduled_email: ScheduledEmail,
    mailgun_credentials: MailgunCredentials,
    overwrite_outgoing_emails: str,
) -> None:
    # Arrange
    failed_email = scheduled_email.model_copy(update={"state": ScheduledEmailStatus.FAILED})
    client = AsyncMock()
    token_cache = TokenCache(client, token=token)
    controller = AsyncMock()
    controller.lock_by_id.return_value = scheduled_email
    controller.fail_by_id.return_value = failed_email
    mock_fetch_model_field.return_value = "person@example.org"
    mock_read_attachment_from_s3.side_effect = Exception("???")  # TODO: use real exception

    # Act
    result = await handle_email(
        scheduled_email,
        mailgun_credentials,
        overwrite_outgoing_emails,
        controller,
        client,
        token_cache,
    )

    # Assert
    assert result == {
        "email": failed_email.model_dump(mode="json"),
        "status": failed_email.state.value,
    }
    controller.lock_by_id.assert_awaited_once_with(scheduled_email.pk)
    controller.fail_by_id.assert_awaited_once_with(
        scheduled_email.pk,
        details=(f"Failed to download attachments for email {scheduled_email.pk}. Error: ???"),
    )
