import os
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def load_config(config_file: str):
    if not HAS_YAML:
        raise ImportError("PyYAML is required to load config files")
    config_path = Path(__file__).parent.parent / "configs" / config_file
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class Config:
    CTA_URL = os.getenv("CTA_URL", "http://127.0.0.1:8000")
    EC_URL = os.getenv("EC_URL", "http://127.0.0.1:8050")
    GTT_VALID_DAYS = 30
    RRT_VALID_HOURS = 24
    SAT_VALID_MINUTES = 30
    CHALLENGE_TTL_SECONDS = 300
