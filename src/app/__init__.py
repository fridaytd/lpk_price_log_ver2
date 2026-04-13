import logging

from ._config import Config, load_sheets_config

## Seting logger
# Configure logging once at the application level
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s :: %(message)s",
    handlers=[logging.StreamHandler()],
)

# Get logger for this module
logger = logging.getLogger(__name__)


config = Config.from_env()

# Loaded at import time; exits on invalid config
sheets_config = load_sheets_config()


__all__ = ["config", "logger", "sheets_config"]
