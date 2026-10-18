
import os

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow browser-based cross-origin requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Layer 1: Hardcoded defaults
DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def normalize_key(key: str) -> str:
    """Normalize configuration keys and resolve aliases."""
    key = key.strip()

    if key.upper() == "NUM_WORKERS":
        return "workers"

    if key.upper().startswith("APP_"):
        key = key[4:]

    return key.lower()


def read_config():
    # Layer 1: Defaults
    config = DEFAULTS.copy()

    # Layer 2: Environment-specific YAML
    env_name = os.getenv("APP_ENV", "development")
    yaml_file = f"config.{env_name}.yaml"

    try:
        with open(yaml_file, "r", encoding="utf-8") as file:
            yaml_config = yaml.safe_load(file) or {}

        for key, value in yaml_config.items():
            config[normalize_key(key)] = value

    except FileNotFoundError:
        pass

    # Layer 3: .env file
    file_env = dotenv_values(".env")

    for key, value in file_env.items():
        if value is not None:
            config[normalize_key(key)] = value

    # Layer 4: OS environment variables with APP_ prefix
    # APP_ENV selects the YAML file and is not a config setting.
    for key, value in os.environ.items():
        if (
            key.upper().startswith("APP_")
            and key.upper() != "APP_ENV"
        ):
            config[normalize_key(key)] = value

    return config


def coerce_value(key: str, value):
    """Convert values to the required output types."""
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        if isinstance(value, bool):
            return value

        return str(value).strip().lower() in {
            "true", "1", "yes", "on"
        }

    return str(value)


@app.get("/effective-config")
def effective_config(
    set_values: list[str] = Query(default=[], alias="set")
):
    config = read_config()

    # Layer 5: Query parameter overrides have highest precedence.
    for item in set_values:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)
        key = normalize_key(key)

        config[key] = value

    # Convert values to their required types.
    result = {
        key: coerce_value(key, value)
        for key, value in config.items()
    }

    # Never expose the real API key.
    result["api_key"] = "****"

    return result

