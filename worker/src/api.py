import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, cast
from urllib.parse import ParseResult, urlparse
from uuid import UUID

import httpx

from src.settings import SETTINGS
from src.token import TokenCache
from src.types import AuthToken, BasicTypes, ScheduledEmail

logger = logging.getLogger("amy-email-worker")


class UriError(Exception):
    pass


@dataclass
class ScheduledEmailController:
    api_base_url: str
    client: httpx.AsyncClient
    token_cache: TokenCache

    def auth_headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Token {token}"}

    async def get_by_id(self, id_: UUID) -> ScheduledEmail:
        token = await self.token_cache.get_token()
        headers = self.auth_headers(token.token)
        result = await self.client.get(
            f"{self.api_base_url}/v2/scheduledemail/{id_}", headers=headers
        )
        result.raise_for_status()
        return ScheduledEmail(**result.json())

    async def get_paginated(
        self, url: str, *, max_pages: int = 10
    ) -> list[dict[str, Any]]:
        """Paginate over results and collect them. Safety break at max_pages.

        Param `url` should contain `{}` for page number, indexation starts from 1 and
        increments by 1.
        """
        results: list[dict[str, Any]] = []

        token = await self.token_cache.get_token()
        headers = self.auth_headers(token.token)

        # safety break, preventing infinite loop
        counter = 0
        while counter < max_pages:
            result = await self.client.get(url.format(counter + 1), headers=headers)

            # Could be 404 if pagination is out of range
            if result.status_code != 200:
                break

            counter += 1
            results.extend(result.json()["results"])

        return results

    async def get_all(self) -> list[ScheduledEmail]:
        url = f"{self.api_base_url}/v2/scheduledemail?page={{}}"
        results = await self.get_paginated(url)
        scheduled_emails = [ScheduledEmail(**result) for result in results]
        return scheduled_emails

    async def get_scheduled_to_run(self) -> list[ScheduledEmail]:
        url = f"{self.api_base_url}/v2/scheduledemail/scheduled_to_run?page={{}}"
        results = await self.get_paginated(url)
        scheduled_emails = [ScheduledEmail(**result) for result in results]
        return scheduled_emails

    async def lock_by_id(self, id_: UUID) -> ScheduledEmail:
        token = await self.token_cache.get_token()
        headers = self.auth_headers(token.token)
        result = await self.client.post(
            f"{self.api_base_url}/v2/scheduledemail/{id_}/lock", headers=headers
        )
        result.raise_for_status()
        return ScheduledEmail(**result.json())

    async def fail_by_id(self, id_: UUID, details: str) -> ScheduledEmail:
        token = await self.token_cache.get_token()
        headers = self.auth_headers(token.token)
        result = await self.client.post(
            f"{self.api_base_url}/v2/scheduledemail/{id_}/fail",
            json={"details": details},
            headers=headers,
        )
        result.raise_for_status()
        return ScheduledEmail(**result.json())

    async def succeed_by_id(self, id_: UUID, details: str) -> ScheduledEmail:
        token = await self.token_cache.get_token()
        headers = self.auth_headers(token.token)
        result = await self.client.post(
            f"{self.api_base_url}/v2/scheduledemail/{id_}/succeed",
            json={"details": details},
            headers=headers,
        )
        result.raise_for_status()
        return ScheduledEmail(**result.json())


def map_api_uri_to_url(api_uri: str) -> str:
    logger.info(f"Mapping API URI {api_uri!r} onto URL.")

    match urlparse(api_uri):
        case ParseResult(
            scheme="value", netloc="", path=_, params="", query="", fragment=_
        ):
            raise UriError("Unexpected API URI 'value' scheme. Expected only 'api'.")

        case ParseResult(
            scheme="api", netloc="", path=model, params="", query="", fragment=id_
        ):
            return f"{SETTINGS.API_BASE_URL}/v2/{model}/{id_}"

        case _:
            raise UriError(f"Unsupported URI {api_uri!r}.")


def scalar_value_from_uri(uri: str) -> BasicTypes:
    mapping: dict[str, Callable[[Any], Any]] = {
        "str": str,
        "int": int,
        "float": float,
        "bool": lambda x: x.lower() == "true",
    }

    match urlparse(uri):
        case ParseResult(
            scheme="value", netloc="", path=path, params="", query="", fragment=value
        ):
            if path == "none":
                return None

            try:
                return cast(str | int | float | bool, mapping[path](value))
            except KeyError as exc:
                raise UriError(f"Unsupported scalar type {path!r}.") from exc
            except ValueError as exc:
                raise UriError(f"Failed to parse {value!r} from {uri!r}.") from exc

        case _:
            raise UriError(f"Unsupported URI {uri!r}.")


async def fetch_model(
    api_uri: str, client: httpx.AsyncClient, token: AuthToken
) -> dict[str, Any]:
    url = map_api_uri_to_url(api_uri)
    logger.info(f"Fetching entity from {url}.")

    headers = {"Authorization": f"Token {token.token}"}

    response = await client.get(url, headers=headers)
    response.raise_for_status()

    return cast(dict[str, Any], response.json())


async def fetch_model_field(
    api_uri: str, property: str, client: httpx.AsyncClient, token: AuthToken
) -> str:
    logger.info(f"Fetching {property=} from model {api_uri!r}.")

    model = await fetch_model(api_uri, client, token)
    raw_property = model[property]

    logger.info(f"{api_uri} = {raw_property!r}.")
    str_property = str(raw_property)
    return str_property


async def context_entry(
    uri: str | list[str], client: httpx.AsyncClient, token: AuthToken
) -> dict[str, Any] | list[dict[str, Any]] | BasicTypes:
    if isinstance(uri, list):
        return cast(
            list[dict[str, Any]],
            await asyncio.gather(
                *[fetch_model(single_uri, client, token) for single_uri in uri]
            ),
        )

    match urlparse(uri):
        case ParseResult(
            scheme="value", netloc="", path=_, params="", query="", fragment=_
        ):
            return scalar_value_from_uri(uri)

        case ParseResult(
            scheme="api", netloc="", path=_, params="", query="", fragment=_
        ):
            return await fetch_model(uri, client, token)

        case _:
            raise UriError(f"Unsupported URI {uri!r} for context generation.")
