import itertools
import json
import logging
from pathlib import Path
from typing import Final

logger = logging.getLogger(__name__)


class KeyRotationPool:
    def __init__(self, keys_folder: str) -> None:
        folder = Path(keys_folder)
        key_files = sorted(folder.glob("*.json"))  # sorted for deterministic order

        if not key_files:
            raise ValueError(f"No .json key files found in: {folder}")

        self._keys: list[tuple[str, dict]] = [
            (path.name, json.loads(path.read_text()))
            for path in key_files
        ]
        self._cycle = itertools.cycle(self._keys)
        self._pool_size: int = len(self._keys)

        filenames: Final[list[str]] = [name for name, _ in self._keys]
        logger.info(f"KeyRotationPool: loaded {self._pool_size} keys: {filenames}")

    @property
    def pool_size(self) -> int:
        return self._pool_size

    def get_next_key(self) -> tuple[str, dict]:
        """Return the next key in round-robin order and log the selection."""
        filename, key_data = next(self._cycle)
        logger.debug(f"KeyRotationPool: selected key {filename}")
        return filename, key_data
