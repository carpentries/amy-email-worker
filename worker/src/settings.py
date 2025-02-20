import os
from typing import cast

from src.aws import get_parameter_value, read_ssm_parameter
from src.types import Credentials, MailgunCredentials, Settings, Stage


def read_settings_from_env() -> Settings:
    return Settings(
        OVERWRITE_OUTGOING_EMAILS=os.getenv("OVERWRITE_OUTGOING_EMAILS") or "",
        STAGE=(
            cast(Stage, stage) if (stage := os.getenv("STAGE", "staging")) in ["production", "staging"] else "staging"
        ),
        API_BASE_URL=os.getenv("API_BASE_URL") or "http://localhost:8000/api",
    )


SETTINGS = read_settings_from_env()
STAGE = SETTINGS.STAGE


def read_mailgun_credentials() -> MailgunCredentials:
    # TODO: turn into async
    api_key_parameter = read_ssm_parameter(f"/{STAGE}/email-worker/mailgun_key")
    api_key = get_parameter_value(api_key_parameter) if api_key_parameter else "fakeKey"

    sender_domain_parameter = read_ssm_parameter(f"/{STAGE}/email-worker/mailgun_sender_domain")
    sender_domain = get_parameter_value(sender_domain_parameter) if sender_domain_parameter else ""
    return MailgunCredentials(
        MAILGUN_SENDER_DOMAIN=sender_domain,
        MAILGUN_API_KEY=api_key,
    )


def read_token_credentials_from_ssm() -> Credentials:
    # TODO: turn into async
    token_user_parameter = read_ssm_parameter(f"/{STAGE}/email-worker/token_username")
    token_password_parameter = read_ssm_parameter(f"/{STAGE}/email-worker/token_password")

    token_user = get_parameter_value(token_user_parameter) if token_user_parameter else "email_worker_account"
    token_password = get_parameter_value(token_password_parameter) if token_password_parameter else "fakePassword"

    return Credentials(
        USER=token_user,
        PASSWORD=token_password,
    )


def read_s3_bucket_from_ssm() -> str:
    bucket_parameter = read_ssm_parameter(f"/{STAGE}/email-worker/s3_bucket")
    bucket = get_parameter_value(bucket_parameter) if bucket_parameter else "fakeBucket"
    return bucket
