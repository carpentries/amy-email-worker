from datetime import datetime, timedelta, timezone

import httpx

from src.settings import SETTINGS, read_token_credentials_from_ssm
from src.types import AuthToken


class TokenCache:
    client: httpx.AsyncClient
    _token: AuthToken | None
    _delta: timedelta

    def __init__(
        self,
        client: httpx.AsyncClient,
        delta: timedelta = timedelta(0),
        token: AuthToken | None = None,
    ) -> None:
        self.client = client
        self._token = token.model_copy() if token is not None else None
        self._delta = delta

    async def fetch_token(self) -> AuthToken:
        credentials = read_token_credentials_from_ssm()
        url = f"{SETTINGS.API_BASE_URL}/auth/login/"

        response = await self.client.post(
            url,
            auth=(credentials.USER, credentials.PASSWORD),
        )
        response.raise_for_status()

        return AuthToken(**response.json())

    async def get_token(self) -> AuthToken:
        current_time = datetime.now(tz=timezone.utc)

        if self._token is None or self._token.has_expired(current_time, self._delta):
            self._token = await self.fetch_token()

        return self._token
