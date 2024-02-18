from datetime import datetime, timedelta, timezone

import httpx

from src.settings import SETTINGS, read_token_credentials_from_ssm
from src.types import AuthToken


class CachedToken:
    _token: AuthToken | None
    _delta: timedelta

    def __init__(self, delta: timedelta = timedelta(0)) -> None:
        self._token = None
        self._delta = delta

    @staticmethod
    async def fetch_token(client: httpx.AsyncClient) -> AuthToken:
        credentials = read_token_credentials_from_ssm()
        url = f"{SETTINGS.API_BASE_URL}/auth/login/"

        response = await client.post(
            url,
            auth=(credentials.USER, credentials.PASSWORD),
        )
        response.raise_for_status()

        return AuthToken(**response.json())

    async def get_token(self, client: httpx.AsyncClient) -> AuthToken:
        current_time = datetime.now(tz=timezone.utc)

        if self._token is None or self._token.has_expired(current_time, self._delta):
            self._token = await self.fetch_token(client)

        return self._token
