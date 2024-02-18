from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from src.types import AuthToken


@pytest.fixture()
def token() -> AuthToken:
    return AuthToken(
        expiry=datetime.now(tz=timezone.utc) + timedelta(hours=10),
        token=str(uuid4()),
    )
