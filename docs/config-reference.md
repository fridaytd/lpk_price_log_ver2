# Configuration Reference — lpk_price_log_ver2

This document describes every configuration field required to run `lpk_price_log_ver2`. There are two configuration files: `sheets_config.yaml` (which Google Sheets to process) and `settings.env` (environment variables and secrets).

---

## Section 1: `sheets_config.yaml` Reference

**Location:** project root — `lpk_price_log_ver2/sheets_config.yaml`

This file tells the worker which Google Sheets to monitor and update. Each entry in the `sheets` list maps to one concurrent processing task.

### Example

```yaml
# sheets_config.yaml — Multi-sheet configuration for lpk_price_log_ver2
sheets:
  - name: "GameCategory1"          # Human-readable name; used in log output and error messages
    spreadsheet_id: "1BxiMxxxxxxx"  # Google Sheets spreadsheet ID (found in the sheet URL)
  - name: "GameCategory2"
    spreadsheet_id: "2CyiNxxxxxxx"
```

### Field Reference

| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| `sheets` | list of entries | Yes | List of target sheets to process concurrently (1–5 entries supported) | *(see entries below)* |
| `sheets[].name` | string | Yes | Human-readable label for this sheet. Appears in all log output and error messages. | `"GameCategory1"` |
| `sheets[].spreadsheet_id` | string | Yes | The Google Sheets spreadsheet ID. Extract it from the sheet URL: `https://docs.google.com/spreadsheets/d/<ID>/edit` | `"1BxiMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"` |

### Validation & Error Messages

The file is validated at startup by `load_sheets_config()` in `src/app/_config.py`. The process exits immediately if any of the following conditions occur:

| Condition | Error Message |
|---|---|
| File not found | `ERROR: sheets_config.yaml not found at <path>` |
| Invalid YAML syntax | `ERROR: Invalid YAML in sheets_config.yaml: <detail>` |
| Missing `name` or `spreadsheet_id` field | `ERROR: Invalid sheets_config.yaml schema: <detail>` |

### Operational Notes

- **Maximum 5 sheets** — the system uses `asyncio.gather` to run all sheet tasks concurrently; 5 is the practical upper limit.
- **No code changes required** to add or remove sheets — simply edit `sheets_config.yaml` and restart the process.
- **Restart required** — the file is read once at startup; changes do not take effect until the process is restarted.

---

## Section 2: `settings.env` Reference

**Location:** project root — `lpk_price_log_ver2/settings.env`

This file provides all runtime configuration and secrets. It is loaded at startup via `load_dotenv("settings.env")`, and every field is validated by `Config.model_validate(os.environ)` in `src/app/_config.py`.

> **Note:** Use `settings.env.example` as a starting template. Copy it to `settings.env` and fill in real values.

### Field Reference

| Variable | Type | Required | Description | Default / Example |
|---|---|---|---|---|
| `KEYS_PATH` | string | Yes (legacy) | Path to a single legacy service account key file. Kept for backward compatibility during migration. Still required by the `Config` model — omitting it causes a `ValidationError` at startup. | `"keys.json"` |
| `KEYS_FOLDER_PATH` | string | Yes | Path to the **folder** containing service account JSON key files used by `KeyRotationPool`. All `.json` files in this folder are loaded at startup. | `"./keys"` |
| `SPREADSHEET_KEY` | string | Yes (legacy) | Legacy single-sheet spreadsheet ID. Kept for backward compatibility. Still required by `Config` model validation — omitting it causes startup failure. | `"your-spreadsheet-id-here"` |
| `SHEET_NAME` | string | Yes | The Google Sheets tab name used in `processes.py` via `config.SHEET_NAME`. **This is not dead code** — it is actively used in business logic to identify the correct worksheet tab. | `"Your Sheet Tab Name"` |
| `LAPAK_API_KEY` | string | Yes | Lapakgaming marketplace API Bearer token. Used in the `Authorization: Bearer <token>` header on every API request. | `"your-lapakgaming-api-key-here"` |
| `PROCESS_BATCH_SIZE` | int | Yes | Number of rows processed per batch. Limits rows per API call to stay within rate limits. | `30` |
| `RELAX_TIME_EACH_BATCH` | float | Yes | Sleep duration in seconds between batch operations within a single processing round. | `10` |
| `RELAX_TIME_EACH_ROUND` | float | Yes | Sleep duration in seconds between full processing rounds (after all sheets have been processed). | `10` |

### Example `settings.env`

```env
# Path to the single legacy service account key (kept for backward compat)
KEYS_PATH="keys.json"

# Path to the folder containing service account JSON key files for the rotation pool
KEYS_FOLDER_PATH="./keys"

# Legacy single-sheet config (kept for backward compat during migration)
SPREADSHEET_KEY="your-spreadsheet-id-here"
SHEET_NAME="Your Sheet Tab Name"

# Lapakgaming API Bearer token
LAPAK_API_KEY="your-lapakgaming-api-key-here"

# Batch processing settings
PROCESS_BATCH_SIZE=30
RELAX_TIME_EACH_BATCH=10
RELAX_TIME_EACH_ROUND=10
```

### Important: All 8 Fields Are Required

`Config.model_validate(os.environ)` validates **all 8 variables** at startup. Omitting any variable — even the ones marked "legacy" — will cause a `ValidationError` and the process will exit immediately with an error message.

Do not remove any field from `settings.env`, even if it appears unused.

### Security Notes

- **`settings.env` is gitignored** — never commit this file. It contains secrets (`LAPAK_API_KEY`) and environment-specific values.
- **`LAPAK_API_KEY` is a Bearer token** — never add it to logs, query strings, comments, or git history. It is passed only via the `Authorization: Bearer` HTTP header.
- **Service account key files** (`keys/*.json`) are gitignored — never commit them. Only the filename (not the file content) appears in log output.
