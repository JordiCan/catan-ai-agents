import os
from pathlib import Path


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def load_env():
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False

    load_dotenv(ENV_PATH)
    # Normalize common AWS keys from lowercase .env entries.
    for lower_key, upper_key in {
        "aws_access_key_id": "AWS_ACCESS_KEY_ID",
        "aws_secret_access_key": "AWS_SECRET_ACCESS_KEY",
        "aws_session_token": "AWS_SESSION_TOKEN",
        "aws_default_region": "AWS_DEFAULT_REGION",
        "aws_region": "AWS_REGION",
    }.items():
        if not os.getenv(upper_key) and os.getenv(lower_key):
            os.environ[upper_key] = os.getenv(lower_key, "").strip()
    return True


def coalesce_env(*keys, default=None):
    for key in keys:
        value = os.getenv(key)
        if value not in (None, ""):
            return value.strip()
    return default


def normalize_provider_name(provider_name):
    provider_name = (provider_name or "mock").lower()
    if provider_name == "upv":
        return "poligpt"
    return provider_name


def env_bool(key, default=False):
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}
