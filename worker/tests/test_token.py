from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.token import CachedToken
from src.types import AuthToken, Credentials


def test_cached_token__fresh_initialization() -> None:
    # Arrange
    cached_token = CachedToken()

    # Assert
    assert cached_token._token is None


@pytest.mark.asyncio
@patch(
    "src.token.read_token_credentials_from_ssm",
    return_value=Credentials(USER="test", PASSWORD="test"),
)
async def test_cached_token__fetch_token(
    mock_read_token_credentials: MagicMock,
) -> None:
    # Arrange
    cached_token = CachedToken()
    client = AsyncMock()
    client.post.return_value = MagicMock()
    client.post.return_value.json.return_value = {
        "expiry": "2022-01-01T00:00:00Z",
        "token": "testToken",
    }

    # Act
    token = await cached_token.fetch_token(client)

    # Assert
    client.post.assert_awaited_once_with(
        "http://localhost:8000/api/auth/login/", auth=("test", "test")
    )
    assert token.model_dump(mode="json") == {
        "expiry": "2022-01-01T00:00:00Z",
        "token": "testToken",
    }


@pytest.mark.asyncio
async def test_cached_token__get_token__initial_fetch_token() -> None:
    # Arrange
    client = AsyncMock()
    cached_token = CachedToken()
    cached_token.fetch_token = AsyncMock(  # type: ignore[method-assign]
        return_value=AuthToken(
            expiry=datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            token="testToken",
        )
    )

    # Act
    token = await cached_token.get_token(client)

    # Assert
    assert token == AuthToken(
        expiry=datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        token="testToken",
    )


@pytest.mark.asyncio
async def test_cached_token__get_token__expired() -> None:
    # Arrange
    client = AsyncMock()
    token = AuthToken(
        expiry=datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        token="testToken",
    )
    cached_token = CachedToken(token=token)
    cached_token.fetch_token = AsyncMock()  # type: ignore[method-assign]

    # Act
    await cached_token.get_token(client)

    # Assert
    assert token.has_expired(datetime.now(tz=timezone.utc), delta=timedelta(0))
    cached_token.fetch_token.assert_awaited_once_with(client)


@pytest.mark.asyncio
async def test_cached_token__get_token__cached() -> None:
    # Arrange
    client = AsyncMock()
    token = AuthToken(
        expiry=datetime.now(tz=timezone.utc) + timedelta(days=1),  # future
        token="testToken",
    )
    cached_token = CachedToken(token=token)
    cached_token.fetch_token = AsyncMock()  # type: ignore[method-assign]

    # Act
    await cached_token.get_token(client)

    # Assert
    assert not token.has_expired(datetime.now(tz=timezone.utc), delta=timedelta(0))
    cached_token.fetch_token.assert_not_awaited()
