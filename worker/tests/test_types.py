"""
Most of the types defined in this project don't contain any logic.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.types import AuthToken


# Arrange
@pytest.mark.parametrize(
    "token, current_time, delta, expected",
    [
        (
            AuthToken(expiry=datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc), token=""),
            datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            timedelta(0),
            False,
        ),
        (
            AuthToken(expiry=datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc), token=""),
            datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            timedelta(seconds=1),
            True,
        ),
        (
            AuthToken(expiry=datetime(2022, 1, 1, 0, 0, 1, tzinfo=timezone.utc), token=""),
            datetime(2022, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            timedelta(seconds=1),
            False,
        ),
        (
            AuthToken(expiry=datetime(2022, 1, 1, 0, 5, 0, tzinfo=timezone.utc), token=""),
            datetime(2022, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
            timedelta(minutes=5),
            True,
        ),
    ],
)
def test_auth_token__has_expired(token: AuthToken, current_time: datetime, delta: timedelta, expected: bool) -> None:
    # Act
    result = token.has_expired(current_time, delta)
    # Assert
    assert result == expected
