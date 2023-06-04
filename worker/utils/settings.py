import os

from utils.types import Settings


def read_settings_from_env() -> Settings:
    return {
        "stage": os.getenv("STAGE") or "staging",
        "overwrite_outgoing_emails": os.getenv("OVERWRITE_OUTGOING_EMAILS") or "",
    }
