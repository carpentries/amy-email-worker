from datetime import datetime, timezone, timedelta

import httpx

from src.settings import STAGE
from src.types import AuthToken, Stage


def api_url() -> str:
    stage_to_host: dict[Stage, str] = {
        "prod": "amy.carpentries.org",
        "staging": "test-amy2.carpentries.org",
    }
    host = stage_to_host[STAGE]
    return f"https://{host}/api"


def api_credentials() -> tuple[str, str]:
    # TODO: implement
    return "user", "pswd"


class CachedToken:
    _token: AuthToken | None
    _delta: timedelta

    def __init__(self, delta: timedelta = timedelta(0)) -> None:
        self._token = None
        self._delta = delta

    @staticmethod
    async def fetch_token(client: httpx.AsyncClient) -> AuthToken:
        url = f"{api_url()}/auth/login/"
        user, pswd = api_credentials()

        response = await client.post(url, auth=(user, pswd))
        response.raise_for_status()

        return AuthToken(**response.json())

    async def get_token(self, client: httpx.AsyncClient) -> AuthToken:
        current_time = datetime.now(tz=timezone.utc)

        if self._token is None or self._token.has_expired(current_time, self._delta):
            self._token = await self.fetch_token(client)

        return self._token
