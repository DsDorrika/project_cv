from pathlib import Path
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent.absolute()
SETTINGS_FILE = BASE_DIR / 'user_settings.json'


def load_user_settings() -> Dict[str, Any]:
    """Load user settings from JSON file. Returns empty dict if not present or on error."""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception as e:
        logger.error(f"Failed to load user settings: {e}")
    return {}


def save_user_settings(settings: Dict[str, Any]) -> bool:
    """Save provided settings dict to JSON file. Returns True on success."""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save user settings: {e}")
        return False


def get_user_setting(key: str, default: Optional[Any] = None) -> Optional[Any]:
    s = load_user_settings()
    return s.get(key, default)
