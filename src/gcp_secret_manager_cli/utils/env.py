from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv
import os


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
