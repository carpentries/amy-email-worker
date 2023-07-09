import os

from utils.ssm import get_parameter_value, read_ssm_parameter
from utils.types import MailgunCredentials, Settings


def read_settings_from_env() -> Settings:
    return Settings(
        STAGE=os.getenv("STAGE") or "staging",
        OVERWRITE_OUTGOING_EMAILS=os.getenv("OVERWRITE_OUTGOING_EMAILS") or "",
    )


def read_mailgun_credentials(stage: str) -> MailgunCredentials:
    api_key_parameter = read_ssm_parameter(f"/{stage}/amy/mailgun_key")
    api_key = get_parameter_value(api_key_parameter) if api_key_parameter else "fakeKey"
    return MailgunCredentials(
        MAILGUN_SENDER_DOMAIN=os.getenv("MAILGUN_SENDER_DOMAIN") or "",
        MAILGUN_API_KEY=api_key,
    )
