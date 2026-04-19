import os
from pathlib import Path


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def load_env():
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False

    load_dotenv(ENV_PATH)
    return True


def coalesce_env(*keys, default=None):
    for key in keys:
        value = os.getenv(key)
        if value not in (None, ""):
            return value
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
