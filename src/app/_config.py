import os
import sys
import yaml
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError


class Config(BaseModel):
    # Keys
    KEYS_FOLDER_PATH: str  # Path to folder containing service account JSON key files for rotation pool

    LAPAK_API_KEY: str  # Lapakgaming API Bearer token

    PROCESS_BATCH_SIZE: int  # Number of rows per batch for logging sheets
    PARALLEL_BATCH_COUNT: (
        int  # Number of batches to process concurrently for logging sheets (e.g. 4)
    )

    LISTING_BATCH_SIZE: int  # Number of rows per batch for listing sheets
    LISTING_PARALLEL_BATCH_COUNT: (
        int  # Number of batches to process concurrently for listing sheets (e.g. 4)
    )

    RATE_LIMIT_WAIT_SECONDS: (
        float  # Seconds to wait after all keys in the pool have hit 429 (e.g. 60.0)
    )

    RELAX_AFTER_EACH_ROUND: float = 60

    @staticmethod
    def from_env(dotenv_path: str = "settings.env") -> "Config":
        load_dotenv(dotenv_path)
        return Config.model_validate(os.environ)


class SheetEntry(BaseModel):
    name: str  # Human-readable label; used in log output and error messages
    spreadsheet_id: str  # Google Sheets spreadsheet ID (from URL)


class SheetsConfig(BaseModel):
    listing_sheets: list[SheetEntry]
    logging_sheets: list[SheetEntry]


def load_sheets_config(config_path: Path | None = None) -> SheetsConfig:
    """Load and validate sheets_config.yaml. Exits on invalid config."""
    if config_path is None:
        from app.paths import ROOT_PATH

        config_path = ROOT_PATH / "sheets_config.yaml"
    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)
        cfg = SheetsConfig.model_validate(data)
        print(
            f"Loaded {len(cfg.listing_sheets)} listing sheet(s), {len(cfg.logging_sheets)} logging sheet(s)"
        )
        return cfg
    except FileNotFoundError:
        print(f"ERROR: sheets_config.yaml not found at {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"ERROR: Invalid YAML in sheets_config.yaml: {e}")
        sys.exit(1)
    except ValidationError as e:
        print(f"ERROR: Invalid sheets_config.yaml schema: {e}")
        sys.exit(1)
