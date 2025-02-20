from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api import (
    UriError,
    context_entry,
    fetch_model,
    fetch_model_field,
    map_api_uri_to_url,
    scalar_value_from_uri,
)
from src.types import AuthToken


# Arrange
@pytest.mark.parametrize(
    "uri,expected",
    [
        (
            "api:person#123456",
            "http://localhost:8000/api/v2/person/123456",
        ),
        (
            "api:event#444",
            "http://localhost:8000/api/v2/event/444",
        ),
    ],
)
def test_map_api_uri_to_url(uri: str, expected: str) -> None:
    # Act
    result = map_api_uri_to_url(uri)
    # Assert
    assert result == expected


def test_map_api_uri_to_url__unexpected_scheme() -> None:
    # Arrange
    uri = "value:int#123456"

    # Act & Assert
    with pytest.raises(UriError, match="Unexpected API URI 'value' scheme. Expected only 'api'."):
        map_api_uri_to_url(uri)


def test_map_api_uri_to_url__unsupported_uri() -> None:
    # Arrange
    uri = "value:int#123456"
    # Act & Assert
    with pytest.raises(UriError, match="Unexpected API URI 'value' scheme. Expected only 'api'."):
        map_api_uri_to_url(uri)


# Arrange
@pytest.mark.parametrize(
    "uri,expected",
    [
        ("value:str#test", "test"),
        ("value:int#123", 123),
        ("value:float#3.14", 3.14),
        ("value:bool#True", True),
        ("value:bool#False", False),
        ("value:bool#true", True),
        ("value:bool#false", False),
        ("value:none#", None),
        ("value:none#None", None),
        ("value:none#asdf123", None),
        ("value:date#2022-01-01T12:01Z", datetime(2022, 1, 1, 12, 1, tzinfo=UTC)),
    ],
)
def test_scalar_value_from_uri(uri: str, expected: Any) -> None:
    # Act
    result = scalar_value_from_uri(uri)
    # Assert
    assert result == expected


def test_scalar_value_from_uri__unsupported_scalar_type() -> None:
    # Arrange
    uri = "value:unsupported#test"
    # Act & Assert
    with pytest.raises(UriError, match="Unsupported scalar type 'unsupported'."):
        scalar_value_from_uri(uri)


def test_scalar_value_from_uri__failed_parsing() -> None:
    # Arrange
    uri = "value:int#asd"
    # Act & Assert
    with pytest.raises(UriError, match="Failed to parse 'asd' from 'value:int#asd'."):
        scalar_value_from_uri(uri)


@pytest.mark.asyncio
async def test_fetch_model(token: AuthToken) -> None:
    # Arrange
    uri = "api:person#123456"
    mapped_url = "http://localhost:8000/api/v2/person/123456"
    headers = {"Authorization": f"Token {token.token}"}
    client = AsyncMock()
    mock_get = MagicMock()
    client.get.return_value = mock_get
    mock_get.json.return_value = {"id": 123456, "name": "John Doe"}

    # Act
    result = await fetch_model(uri, client, token)

    # Assert
    client.get.assert_awaited_once_with(mapped_url, headers=headers)
    mock_get.raise_for_status.assert_called_once()
    assert result == {"id": 123456, "name": "John Doe"}


@pytest.mark.asyncio
@patch("src.api.fetch_model")
async def test_fetch_model_field(mock_fetch_model: AsyncMock, token: AuthToken) -> None:
    # Arrange
    uri = "api:person#123456"
    property = "email"
    mock_fetch_model.return_value = {
        "id": 123456,
        "name": "John Doe",
        "email": "jdoe@example.com",
    }
    client = AsyncMock()

    # Act
    result = await fetch_model_field(uri, property, client, token)

    # Assert
    mock_fetch_model.assert_awaited_once_with(uri, client, token)
    assert result == "jdoe@example.com"


@pytest.mark.asyncio
@patch("src.api.fetch_model")
async def test_fetch_model_field__property_string_conversion(mock_fetch_model: AsyncMock, token: AuthToken) -> None:
    # Arrange
    uri = "api:person#123456"
    property = "age"
    mock_fetch_model.return_value = {
        "id": 123456,
        "name": "John Doe",
        "age": 35,
    }
    client = AsyncMock()

    # Act
    result = await fetch_model_field(uri, property, client, token)

    # Assert
    mock_fetch_model.assert_awaited_once_with(uri, client, token)
    assert result == "35"


@pytest.mark.asyncio
@patch("src.api.fetch_model")
async def test_fetch_model_field__invalid_property(mock_fetch_model: AsyncMock, token: AuthToken) -> None:
    # Arrange
    uri = "api:person#123456"
    property = "email"
    mock_fetch_model.return_value = {"id": 123456, "name": "John Doe"}
    client = AsyncMock()

    # Act & Assert
    with pytest.raises(KeyError, match="email"):
        await fetch_model_field(uri, property, client, token)


@pytest.mark.asyncio
async def test_context_entry__scalar(token: AuthToken) -> None:
    # Arrange
    uri = "value:str#test"
    client = AsyncMock()

    # Act
    result = await context_entry(uri, client, token)

    # Assert
    assert result == "test"


@pytest.mark.asyncio
@patch("src.api.fetch_model")
async def test_context_entry__model(mock_fetch_model: AsyncMock, token: AuthToken) -> None:
    # Arrange
    uri = "api:person#123456"
    mock_fetch_model.return_value = {"id": 123456, "name": "John Doe"}
    client = AsyncMock()

    # Act
    result = await context_entry(uri, client, token)

    # Assert
    assert result == {"id": 123456, "name": "John Doe"}


@pytest.mark.asyncio
async def test_context_entry__unsupported_uri(token: AuthToken) -> None:
    # Arrange
    uri = "unsupported:person#123456"
    client = AsyncMock()

    # Act & Assert
    with pytest.raises(
        UriError,
        match="Unsupported URI 'unsupported:person#123456' for context generation.",
    ):
        await context_entry(uri, client, token)


@pytest.mark.asyncio
@patch("src.api.fetch_model")
async def test_context_entry__multiple_models(mock_fetch_model: AsyncMock, token: AuthToken) -> None:
    # Arrange
    uris = [
        "api:person#123456",
        "api:event#444",
    ]
    mock_fetch_model.side_effect = [
        {"id": 123456, "name": "John Doe"},
        {"id": 444, "slug": "test-event"},
    ]
    client = AsyncMock()

    # Act
    result = await context_entry(uris, client, token)

    # Assert
    assert result == [
        {"id": 123456, "name": "John Doe"},
        {"id": 444, "slug": "test-event"},
    ]
