from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv
import os
from dotenv import dotenv_values


def find_env_file(filename: str = ".env") -> Optional[Path]:
    """Search for the env file upwards."""
    current = Path.cwd()
    while current != current.parent:
        env_path = current / filename
        if env_path.exists():
            return env_path
        current = current.parent
    return None


def read_env_file(file_path: str) -> Dict[str, str]:
    """Read the contents of the env file."""
    env_path = find_env_file(file_path)
    if not env_path:
        raise FileNotFoundError(f"Can't find the environment file: {file_path}")

    # Use dotenv_values instead of manual parsing
    return dict(dotenv_values(env_path))


@dataclass
class ProjectConfig:
    project_id: Optional[str]
    source_path: Optional[Path]

    @classmethod
    def load(cls) -> "ProjectConfig":
        """Load project settings."""
        if "PROJECT_ID" in os.environ:
            del os.environ["PROJECT_ID"]

        env_path = find_env_file()
        if env_path:
            load_dotenv(env_path, override=True)

        return cls(project_id=os.getenv("PROJECT_ID"), source_path=env_path)


def get_project_config() -> ProjectConfig:
    """Obtain project settings with forced reload."""
    return ProjectConfig.load()


def get_timezone() -> str:
    """
    Get timezone setting from environment variable

    Returns:
        str: Timezone name, defaults to UTC
    """
    load_dotenv()
    return os.getenv("TZ", "UTC")
