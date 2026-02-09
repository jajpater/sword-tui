"""Configuration management for sword-tui."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


CONFIG_DIR = Path.home() / ".config" / "sword-tui"
CONFIG_FILE = CONFIG_DIR / "config.json"


@dataclass
class Config:
    """Application configuration."""

    default_module: Optional[str] = None
    default_reference: str = "Gen 1:1"

    @classmethod
    def load(cls) -> "Config":
        """Load config from file, or return defaults."""
        if not CONFIG_FILE.exists():
            return cls()

        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
                return cls(
                    default_module=data.get("default_module"),
                    default_reference=data.get("default_reference", "Gen 1:1"),
                )
        except (json.JSONDecodeError, OSError):
            return cls()

    def save(self) -> None:
        """Save config to file."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "default_module": self.default_module,
            "default_reference": self.default_reference,
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)


def get_config() -> Config:
    """Get the application config."""
    return Config.load()
