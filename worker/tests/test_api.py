from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api import (
    map_api_uri_to_url,
    scalar_value_from_uri,
    fetch_model,
    fetch_model_field,
    context_entry,
)


# Arrange
@pytest.mark.parametrize(
    "uri,stage,expected",
    [
        (
            "api:person#123456",
            "staging",
            "https://test-amy2.carpentries.org/api/v1/person/123456",
        ),
        (
            "api:event#444",
            "prod",
            "https://amy.carpentries.org/api/v1/event/444",
        ),
    ],
)
def test_map_api_uri_to_url(uri, stage, expected) -> None:
    # Act
    result = map_api_uri_to_url(uri, stage)
    # Assert
    assert result == expected


def test_map_api_uri_to_url__unexpected_scheme() -> None:
    # Arrange
    uri = "value:int#123456"
    stage = "prod"
    # Act & Assert
    with pytest.raises(
        ValueError, match="Unexpected API URI 'value' scheme. Expected only 'api'."
    ):
        map_api_uri_to_url(uri, stage)


def test_map_api_uri_to_url__unsupported_uri() -> None:
    # Arrange
    uri = "value:int#123456"
    stage = "prod"
    # Act & Assert
    with pytest.raises(
        ValueError, match="Unexpected API URI 'value' scheme. Expected only 'api'."
    ):
        map_api_uri_to_url(uri, stage)


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
    ],
)
def test_scalar_value_from_uri(uri, expected) -> None:
    # Act
    result = scalar_value_from_uri(uri)
    # Assert
    assert result == expected


def test_scalar_value_from_uri__unsupported_scalar_type() -> None:
    # Arrange
    uri = "value:unsupported#test"
    # Act & Assert
    with pytest.raises(ValueError, match="Unsupported scalar type 'unsupported'."):
        scalar_value_from_uri(uri)


def test_scalar_value_from_uri__failed_parsing() -> None:
    # Arrange
    uri = "value:int#asd"
    # Act & Assert
    with pytest.raises(ValueError, match="Failed to parse 'asd' from 'value:int#asd'."):
        scalar_value_from_uri(uri)


@pytest.mark.asyncio
async def test_fetch_model() -> None:
    # Arrange
    stage = "staging"
    uri = "api:person#123456"
    mapped_url = "https://test-amy2.carpentries.org/api/v1/person/123456"
    client = AsyncMock()
    mock_get = MagicMock()
    client.get.return_value = mock_get
    mock_get.json.return_value = {"id": 123456, "name": "John Doe"}

    # Act
    result = await fetch_model(uri, client, stage)

    # Assert
    client.get.assert_awaited_once_with(mapped_url)
    mock_get.raise_for_status.assert_called_once()
    assert result == {"id": 123456, "name": "John Doe"}


@pytest.mark.asyncio
@patch("src.api.fetch_model")
async def test_fetch_model_field(mock_fetch_model: AsyncMock) -> None:
    # Arrange
    stage = "staging"
    uri = "api:person#123456"
    property = "email"
    mock_fetch_model.return_value = {
        "id": 123456,
        "name": "John Doe",
        "email": "jdoe@example.com",
    }
    client = AsyncMock()

    # Act
    result = await fetch_model_field(uri, property, client, stage)

    # Assert
    mock_fetch_model.assert_awaited_once_with(uri, client, stage)
    assert result == "jdoe@example.com"


@pytest.mark.asyncio
@patch("src.api.fetch_model")
async def test_fetch_model_field__property_string_conversion(
    mock_fetch_model: AsyncMock,
) -> None:
    # Arrange
    stage = "staging"
    uri = "api:person#123456"
    property = "age"
    mock_fetch_model.return_value = {
        "id": 123456,
        "name": "John Doe",
        "age": 35,
    }
    client = AsyncMock()

    # Act
    result = await fetch_model_field(uri, property, client, stage)

    # Assert
    mock_fetch_model.assert_awaited_once_with(uri, client, stage)
    assert result == "35"


@pytest.mark.asyncio
@patch("src.api.fetch_model")
async def test_fetch_model_field__invalid_property(mock_fetch_model: AsyncMock) -> None:
    # Arrange
    stage = "staging"
    uri = "api:person#123456"
    property = "email"
    mock_fetch_model.return_value = {"id": 123456, "name": "John Doe"}
    client = AsyncMock()

    # Act & Assert
    with pytest.raises(KeyError, match="email"):
        await fetch_model_field(uri, property, client, stage)


@pytest.mark.asyncio
async def test_context_entry__scalar() -> None:
    # Arrange
    uri = "value:str#test"
    stage = "staging"
    client = AsyncMock()

    # Act
    result = await context_entry(uri, client, stage)

    # Assert
    assert result == "test"


@pytest.mark.asyncio
@patch("src.api.fetch_model")
async def test_context_entry__model(mock_fetch_model: AsyncMock) -> None:
    # Arrange
    uri = "api:person#123456"
    stage = "staging"
    mock_fetch_model.return_value = {"id": 123456, "name": "John Doe"}
    client = AsyncMock()

    # Act
    result = await context_entry(uri, client, stage)

    # Assert
    assert result == {"id": 123456, "name": "John Doe"}


@pytest.mark.asyncio
async def test_context_entry__unsupported_uri() -> None:
    # Arrange
    uri = "unsupported:person#123456"
    stage = "staging"
    client = AsyncMock()

    # Act & Assert
    with pytest.raises(
        ValueError,
        match="Unsupported URI 'unsupported:person#123456' for context generation.",
    ):
        await context_entry(uri, client, stage)


@pytest.mark.asyncio
@patch("src.api.fetch_model")
async def test_context_entry__multiple_models(mock_fetch_model: AsyncMock) -> None:
    # Arrange
    uris = [
        "api:person#123456",
        "api:event#444",
    ]
    stage = "staging"
    mock_fetch_model.side_effect = [
        {"id": 123456, "name": "John Doe"},
        {"id": 444, "slug": "test-event"},
    ]
    client = AsyncMock()

    # Act
    result = await context_entry(uris, client, stage)

    # Assert
    assert result == [
        {"id": 123456, "name": "John Doe"},
        {"id": 444, "slug": "test-event"},
    ]
