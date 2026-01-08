"""Configuration manager for storing user preferences outside the database.

This module handles configuration that needs to persist independently of the
database, such as the database path itself (which can't be stored in the
database it points to).

Configuration is stored in the user's AppData folder:
    %APPDATA%\\IssueRegister\\config.json
"""

import json
import os
from pathlib import Path
from typing import Optional


# Configuration directory and file
APP_NAME = "IssueRegister"
CONFIG_FILENAME = "config.json"

# Configuration keys
KEY_DATABASE_PATH = "database_path"


def get_config_dir() -> Path:
    """
    Get the configuration directory path.

    Returns:
        Path to %APPDATA%\\IssueRegister\\ (created if doesn't exist)
    """
    appdata = os.environ.get("APPDATA")
    if appdata:
        config_dir = Path(appdata) / APP_NAME
    else:
        # Fallback for non-Windows systems
        config_dir = Path.home() / ".config" / APP_NAME

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_file() -> Path:
    """Get the configuration file path."""
    return get_config_dir() / CONFIG_FILENAME


def load_config() -> dict:
    """
    Load configuration from file.

    Returns:
        Configuration dictionary (empty dict if file doesn't exist)
    """
    config_file = get_config_file()

    if not config_file.exists():
        return {}

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_config(config: dict) -> bool:
    """
    Save configuration to file.

    Args:
        config: Configuration dictionary to save

    Returns:
        True if successful, False otherwise
    """
    config_file = get_config_file()

    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except IOError:
        return False


def get_saved_database_path() -> Optional[str]:
    """
    Get the saved database path from configuration.

    Returns:
        Database path string if saved, None otherwise
    """
    config = load_config()
    return config.get(KEY_DATABASE_PATH)


def set_saved_database_path(path: str) -> bool:
    """
    Save the database path to configuration.

    Args:
        path: Database file path to save

    Returns:
        True if successful, False otherwise
    """
    config = load_config()
    config[KEY_DATABASE_PATH] = path
    return save_config(config)


def clear_saved_database_path() -> bool:
    """
    Clear the saved database path from configuration.

    Returns:
        True if successful, False otherwise
    """
    config = load_config()
    if KEY_DATABASE_PATH in config:
        del config[KEY_DATABASE_PATH]
    return save_config(config)


def is_database_path_valid(path: Optional[str]) -> bool:
    """
    Check if a database path is valid and accessible.

    Args:
        path: Database path to check

    Returns:
        True if path exists or parent directory is writable
    """
    if not path:
        return False

    db_path = Path(path)

    # If database file exists, it's valid
    if db_path.exists():
        return True

    # If parent directory exists and is writable, we can create the database
    parent = db_path.parent
    return parent.exists() and os.access(str(parent), os.W_OK)
