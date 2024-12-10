from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv
import os


def read_env_file(file_path: str) -> Dict[str, str]:
    """
    Read content from .env file

    Args:
        file_path (str): Path to .env file

    Returns:
        Dict[str, str]: Environment variables dictionary

    Raises:
        FileNotFoundError: File not found
    """
    env_path = Path(os.getcwd()) / file_path
    if not env_path.exists():
        raise FileNotFoundError(f"File not found: {env_path}")

    env_content = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                try:
                    key, value = line.split("=", 1)
                    env_content[key.strip()] = value.strip()
                except ValueError:
                    continue

    return env_content


def get_project_id() -> Optional[str]:
    """
    Get project ID from environment variable

    Returns:
        Optional[str]: Project ID, or None if not set
    """
    load_dotenv()
    return os.getenv("PROJECT_ID")


def get_timezone() -> str:
    """
    Get timezone setting from environment variable

    Returns:
        str: Timezone name, defaults to UTC
    """
    load_dotenv()
    return os.getenv("TZ", "UTC")
