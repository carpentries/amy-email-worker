import os

from utils.types import Settings


def read_settings_from_env() -> Settings:
    return {
        "STAGE": os.getenv("STAGE") or "staging",
        "OVERWRITE_OUTGOING_EMAILS": os.getenv("OVERWRITE_OUTGOING_EMAILS") or "",
    }
