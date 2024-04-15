from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call
from uuid import uuid4

import pytest

from src.api import ScheduledEmailController
from src.token import TokenCache
from src.types import AuthToken, ScheduledEmail


@pytest.fixture()
def scheduled_email_fixture() -> dict[str, Any]:
    now = datetime.now(tz=timezone.utc)
    return {
        "pk": uuid4(),
        "created_at": now,
        "last_updated_at": now,
        "state": "scheduled",
        "scheduled_at": now,
        "to_header": ["john@example.com"],
        "to_header_context_json": [{"api_uri": "api:person#1", "property": "email"}],
        "from_header": "team@example.com",
        "reply_to_header": "",
        "cc_header": [],
        "bcc_header": [],
        "subject": "Sample email",
        "body": "Hello, {{ name }}!",
        "context_json": {"name": "John"},
        "template": "Welcome email",
    }


def test_scheduled_email_controller__auth_headers() -> None:
    # Arrange
    api_base_url = "http://localhost:8000/api"
    client = AsyncMock()
    token_cache = TokenCache(client)
    controller = ScheduledEmailController(api_base_url, client, token_cache)
    token = "fake token"

    # Act
    headers = controller.auth_headers(token)

    # Assert
    assert headers == {"Authorization": f"Token {token}"}


@pytest.mark.asyncio
async def test_scheduled_email_controller__get_by_id(
    scheduled_email_fixture: dict[str, Any],
    token: AuthToken,
) -> None:
    # Arrange
    api_base_url = "http://localhost:8000/api"
    client = AsyncMock()
    mock_get = MagicMock()
    client.get.return_value = mock_get
    mock_get.json.return_value = scheduled_email_fixture

    token_cache = TokenCache(client, token=token)
    controller = ScheduledEmailController(api_base_url, client, token_cache)
    id_ = uuid4()

    # Act
    result = await controller.get_by_id(id_)

    # Assert
    assert result == ScheduledEmail(**scheduled_email_fixture)


@pytest.mark.asyncio
async def test_scheduled_email_controller__get_paginated(
    token: AuthToken,
) -> None:
    # Arrange
    api_base_url = "http://localhost:8000/api"
    client = AsyncMock()
    mock_get1 = MagicMock()
    mock_get2 = MagicMock()
    mock_get3 = MagicMock()
    client.get.side_effect = [mock_get1, mock_get2, mock_get3]

    mock_get1.status_code = 200
    mock_get1.json.return_value = {
        "results": [{"id": "9116a1af-f361-4633-8990-5e16e43683e3"}]
    }
    mock_get2.status_code = 200
    mock_get2.json.return_value = {
        "results": [{"id": "bffca722-d774-4b78-84d4-56863c5e923d"}]
    }
    mock_get3.status_code = 404

    token_cache = TokenCache(client, token=token)
    controller = ScheduledEmailController(api_base_url, client, token_cache)
    url = f"{api_base_url}/v2/fakepage?page={{}}"

    # Act
    result = await controller.get_paginated(url)

    # Assert
    assert result == [
        {"id": "9116a1af-f361-4633-8990-5e16e43683e3"},
        {"id": "bffca722-d774-4b78-84d4-56863c5e923d"},
    ]
    assert client.get.await_count == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("max_pages", [0, 6])
async def test_scheduled_email_controller__get_paginated__safety_break_at_max_pages(
    max_pages: int,
    token: AuthToken,
) -> None:
    # Arrange
    api_base_url = "http://localhost:8000/api"
    client = AsyncMock()
    mock_get = MagicMock()
    client.get.side_effect = [mock_get] * 100

    mock_get.status_code = 200
    mock_get.json.return_value = {
        "results": [{"id": "9116a1af-f361-4633-8990-5e16e43683e3"}]
    }

    token_cache = TokenCache(client, token=token)
    controller = ScheduledEmailController(api_base_url, client, token_cache)
    url = f"{api_base_url}/v2/fakepage?page={{}}"

    # Act
    result = await controller.get_paginated(url, max_pages=max_pages)

    # Assert
    assert client.get.await_count == max_pages
    assert result == [{"id": "9116a1af-f361-4633-8990-5e16e43683e3"}] * max_pages


@pytest.mark.asyncio
async def test_scheduled_email_controller__get_all(
    scheduled_email_fixture: dict[str, Any],
    token: AuthToken,
) -> None:
    # Arrange
    api_base_url = "http://localhost:8000/api"
    client = AsyncMock()
    mock_get1 = MagicMock()
    mock_get2 = MagicMock()
    client.get.side_effect = [mock_get1, mock_get2]

    mock_get1.status_code = 200
    mock_get1.json.return_value = {
        "results": [scheduled_email_fixture, scheduled_email_fixture]
    }
    mock_get2.status_code = 404

    token_cache = TokenCache(client, token=token)
    controller = ScheduledEmailController(api_base_url, client, token_cache)
    headers = controller.auth_headers(token.token)

    # Act
    results = await controller.get_all()

    # Assert
    assert results == [
        ScheduledEmail(**scheduled_email_fixture),
        ScheduledEmail(**scheduled_email_fixture),
    ]
    client.get.assert_has_awaits(
        [
            call(f"{api_base_url}/v2/scheduledemail?page=1", headers=headers),
            call(f"{api_base_url}/v2/scheduledemail?page=2", headers=headers),
        ]
    )


@pytest.mark.asyncio
async def test_scheduled_email_controller__get_scheduled_to_run(
    scheduled_email_fixture: dict[str, Any],
    token: AuthToken,
) -> None:
    # Arrange
    api_base_url = "http://localhost:8000/api"
    client = AsyncMock()
    mock_get1 = MagicMock()
    mock_get2 = MagicMock()
    client.get.side_effect = [mock_get1, mock_get2]

    mock_get1.status_code = 200
    mock_get1.json.return_value = {
        "results": [scheduled_email_fixture, scheduled_email_fixture]
    }
    mock_get2.status_code = 404

    token_cache = TokenCache(client, token=token)
    controller = ScheduledEmailController(api_base_url, client, token_cache)
    headers = controller.auth_headers(token.token)

    # Act
    results = await controller.get_scheduled_to_run()

    # Assert
    assert results == [
        ScheduledEmail(**scheduled_email_fixture),
        ScheduledEmail(**scheduled_email_fixture),
    ]
    client.get.assert_has_awaits(
        [
            call(
                f"{api_base_url}/v2/scheduledemail/scheduled_to_run?page=1",
                headers=headers,
            ),
            call(
                f"{api_base_url}/v2/scheduledemail/scheduled_to_run?page=2",
                headers=headers,
            ),
        ]
    )


@pytest.mark.asyncio
async def test_scheduled_email_controller__lock_by_id(
    scheduled_email_fixture: dict[str, Any],
    token: AuthToken,
) -> None:
    # Arrange
    api_base_url = "http://localhost:8000/api"
    client = AsyncMock()
    mock_post = MagicMock()
    client.post.return_value = mock_post
    mock_post.json.return_value = scheduled_email_fixture

    token_cache = TokenCache(client, token=token)
    controller = ScheduledEmailController(api_base_url, client, token_cache)
    headers = controller.auth_headers(token.token)
    id_ = uuid4()

    # Act
    result = await controller.lock_by_id(id_)

    # Assert
    assert result == ScheduledEmail(**scheduled_email_fixture)
    client.post.assert_awaited_once_with(
        f"{api_base_url}/v2/scheduledemail/{id_}/lock", headers=headers
    )


@pytest.mark.asyncio
async def test_scheduled_email_controller__fail_by_id(
    scheduled_email_fixture: dict[str, Any],
    token: AuthToken,
) -> None:
    # Arrange
    api_base_url = "http://localhost:8000/api"
    client = AsyncMock()
    mock_post = MagicMock()
    client.post.return_value = mock_post
    mock_post.json.return_value = scheduled_email_fixture

    token_cache = TokenCache(client, token=token)
    controller = ScheduledEmailController(api_base_url, client, token_cache)
    headers = controller.auth_headers(token.token)
    id_ = uuid4()
    details = "Changed by tests"

    # Act
    result = await controller.fail_by_id(id_, details)

    # Assert
    assert result == ScheduledEmail(**scheduled_email_fixture)
    client.post.assert_awaited_once_with(
        f"{api_base_url}/v2/scheduledemail/{id_}/fail",
        json={"details": "Changed by tests"},
        headers=headers,
    )


@pytest.mark.asyncio
async def test_scheduled_email_controller__succeed_by_id(
    scheduled_email_fixture: dict[str, Any],
    token: AuthToken,
) -> None:
    # Arrange
    api_base_url = "http://localhost:8000/api"
    client = AsyncMock()
    mock_post = MagicMock()
    client.post.return_value = mock_post
    mock_post.json.return_value = scheduled_email_fixture

    token_cache = TokenCache(client, token=token)
    controller = ScheduledEmailController(api_base_url, client, token_cache)
    headers = controller.auth_headers(token.token)
    id_ = uuid4()
    details = "Changed by tests"

    # Act
    result = await controller.succeed_by_id(id_, details)

    # Assert
    assert result == ScheduledEmail(**scheduled_email_fixture)
    client.post.assert_awaited_once_with(
        f"{api_base_url}/v2/scheduledemail/{id_}/succeed",
        json={"details": "Changed by tests"},
        headers=headers,
    )
