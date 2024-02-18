import os
from typing import cast

from src.ssm import get_parameter_value, read_ssm_parameter
from src.types import MailgunCredentials, Settings, Stage


def read_settings_from_env() -> Settings:
    return Settings(
        OVERWRITE_OUTGOING_EMAILS=os.getenv("OVERWRITE_OUTGOING_EMAILS") or "",
        STAGE=cast(Stage, stage)
        if (stage := os.getenv("STAGE")) in ["staging", "prod"]
        else "staging",
        # TODO: add in cdk
        API_BASE_URL=os.getenv("API_BASE_URL") or "http://localhost:8000/api",
    )


SETTINGS = read_settings_from_env()
STAGE = SETTINGS.STAGE


def read_mailgun_credentials() -> MailgunCredentials:
    # TODO: turn into async
    api_key_parameter = read_ssm_parameter(f"/{STAGE}/email-worker/mailgun_key")
    api_key = get_parameter_value(api_key_parameter) if api_key_parameter else "fakeKey"

    sender_domain_parameter = read_ssm_parameter(
        f"/{STAGE}/email-worker/mailgun_sender_domain"
    )
    sender_domain = (
        get_parameter_value(sender_domain_parameter) if sender_domain_parameter else ""
    )
    return MailgunCredentials(
        MAILGUN_SENDER_DOMAIN=sender_domain,
        MAILGUN_API_KEY=api_key,
    )
