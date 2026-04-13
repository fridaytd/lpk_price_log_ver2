# lpk_price_log_ver2

A backend automation worker that monitors and updates pricing data in Google Sheets for the Lapakgaming marketplace. The system runs as an infinite processing loop, concurrently processing multiple Google Sheets and updating product prices by fetching live data from the Lapakgaming API.

---

## Prerequisites

Before setting up the project, ensure you have the following:

- **Python 3.12+** — required; the project uses modern Python syntax
- **`uv` package manager** — used for all dependency and runtime management; [install uv](https://docs.astral.sh/uv/getting-started/installation/)
- **Google service account JSON key files** — one or more `.json` key files downloaded from Google Cloud Console (IAM & Admin → Service Accounts → Keys); each key must have read/write access to the target spreadsheets
- **Lapakgaming API key** — a Bearer token for the Lapakgaming API (`LAPAK_API_KEY`)

---

## Installation

Clone the repository and install all dependencies using `uv`:

```bash
uv sync
```

> **Note:** Do NOT use `pip install`. This project is managed with `uv` and requires `uv sync` to install the correct locked versions from `uv.lock`.

---

## Configuration: `settings.env`

Copy the example file and fill in your values:

```bash
cp settings.env.example settings.env
```

Then edit `settings.env` with your actual values:

```env
# Path to the single legacy service account key (will be deprecated post-migration)
KEYS_PATH="keys.json"

# Path to the folder containing service account JSON key files for rotation pool
KEYS_FOLDER_PATH="./keys"

# Legacy single-sheet config (kept for backward compatibility)
SPREADSHEET_KEY="your-spreadsheet-id-here"
SHEET_NAME="Your Sheet Tab Name"

# Lapakgaming API Bearer token
LAPAK_API_KEY="your-lapakgaming-api-key-here"

# Batch processing settings
PROCESS_BATCH_SIZE=30
RELAX_TIME_EACH_BATCH=10
RELAX_TIME_EACH_ROUND=10
```

| Variable | Description |
|---|---|
| `KEYS_PATH` | Path to a single legacy service account JSON key file (kept for backward compatibility) |
| `KEYS_FOLDER_PATH` | Folder containing service account JSON key files used in the key rotation pool (default: `./keys`) |
| `SPREADSHEET_KEY` | Google Sheets spreadsheet ID for the legacy single-sheet mode |
| `SHEET_NAME` | Sheet tab name used in legacy single-sheet and active multi-sheet processing |
| `LAPAK_API_KEY` | Bearer token for authenticating with the Lapakgaming API |
| `PROCESS_BATCH_SIZE` | Number of rows to process per batch (default: 30) |
| `RELAX_TIME_EACH_BATCH` | Seconds to sleep between batches within a round (default: 10) |
| `RELAX_TIME_EACH_ROUND` | Seconds to sleep between full processing rounds (default: 10) |

> **Security:** `settings.env` is gitignored. Never commit it to version control.

---

## Configuration: `sheets_config.yaml`

The `sheets_config.yaml` file at the project root defines which Google Sheets the worker processes. Each entry requires a human-readable `name` (used in logs and error messages) and a `spreadsheet_id` (the ID found in the Google Sheets URL).

```yaml
sheets:
  - name: "GameCategory1"          # Human-readable label; appears in logs
    spreadsheet_id: "1BxiM..."     # Google Sheets ID from URL

  - name: "GameCategory2"
    spreadsheet_id: "2CyiN..."
```

To find a spreadsheet's ID, open the sheet in your browser. The ID is the long string in the URL between `/d/` and `/edit`:

```
https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit
```

Up to 5 sheets are supported. Edit this file and restart the process to apply changes (no code changes required).

> **Startup validation:** If `sheets_config.yaml` is missing, contains invalid YAML, or is missing required fields, the process will exit at startup with a clear error message before any sheet processing begins.

---

## Configuration: Key Files

Place service account JSON key files in the `keys/` folder (or the path specified in `KEYS_FOLDER_PATH` in `settings.env`):

```
keys/
├── service-account-1.json
├── service-account-2.json
└── service-account-3.json
```

The system automatically discovers all `.json` files in the folder and rotates across them in round-robin order — one key per API call. You can add or remove key files and restart the process without any code changes.

> **Security:** The `keys/` folder is gitignored. Never commit key files to version control.

---

## Running

Start the worker:

```bash
uv run python src/main.py
```

The process runs an infinite loop until manually stopped (`Ctrl+C` or process termination).

---

## Verifying Startup

After starting, look for these lines in the log output to confirm a healthy startup:

```
KeyRotationPool: loaded 3 keys: ['service-account-1.json', 'service-account-2.json', 'service-account-3.json']
Loaded 2 sheets from config
# Starting processing round...
```

- **Key count** — confirms the key rotation pool loaded your `.json` files from the keys folder
- **Sheets loaded** — confirms `sheets_config.yaml` was parsed successfully
- **Processing round** — confirms the worker has entered the main loop and is actively processing sheets

If the process exits immediately, check the error message — common causes are a missing/invalid `sheets_config.yaml` or missing environment variables in `settings.env`.

---

## Further Guides

- [`docs/managing-sheets.md`](docs/managing-sheets.md) — How to add or remove target sheets
- [`docs/managing-keys.md`](docs/managing-keys.md) — How to add or remove service account key files
