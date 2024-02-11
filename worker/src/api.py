import asyncio
import logging
from typing import Any, Callable, cast
from urllib.parse import ParseResult, urlparse

import httpx

from src.token import api_url
from src.types import AuthToken, BasicTypes

logger = logging.getLogger("amy-email-worker")


class UriError(Exception):
    pass


def map_api_uri_to_url(api_uri: str) -> str:
    logger.info(f"Mapping API URI {api_uri!r} onto URL.")

    url = api_url()

    match urlparse(api_uri):
        case ParseResult(
            scheme="value", netloc="", path=_, params="", query="", fragment=_
        ):
            raise UriError("Unexpected API URI 'value' scheme. Expected only 'api'.")

        case ParseResult(
            scheme="api", netloc="", path=model, params="", query="", fragment=id_
        ):
            return f"{url}/v2/{model}/{id_}"

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
