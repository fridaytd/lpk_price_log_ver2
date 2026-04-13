import logging

from .. import config
from .key_rotation import KeyRotationPool
from .auth import TokenCache
from .g_sheet import async_sheets_client  # New in Story 2.2

## Seting logger
logger = logging.getLogger(name=__name__)

# New in Story 1.3 — uses KEYS_FOLDER_PATH from config
key_rotation_pool = KeyRotationPool(config.KEYS_FOLDER_PATH)

# New in Story 2.1 — TokenCache singleton for OAuth2 Bearer tokens
token_cache = TokenCache()

__all__ = ["key_rotation_pool", "token_cache", "async_sheets_client"]  # Updated in Story 2.2
