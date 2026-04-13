# Architecture Overview — lpk_price_log_ver2

This document describes the high-level design of `lpk_price_log_ver2`, a backend automation worker that monitors and updates pricing data in multiple Google Sheets for the Lapakgaming marketplace.

---

## 1. System Purpose

`lpk_price_log_ver2` is a headless Python worker that runs in an infinite loop. For each configured Google Sheet, it:

1. Fetches current product listings from a batch of rows in the sheet
2. Calls the Lapakgaming marketplace API to obtain up-to-date product prices
3. Computes the correct competitive price using business logic
4. Writes the updated values back to the same sheet

The worker is designed to be always-on: it runs continuously until stopped, sleeping briefly between batches and between full processing rounds to respect API rate limits.

This version is a brownfield refactor of a previous synchronous implementation. The entire I/O layer has been migrated from synchronous `gspread`/`httpx.Client` patterns to a fully asynchronous architecture using `asyncio` and `httpx.AsyncClient`.

---

## 2. Top-Level Architecture

```
main.py
  └── asyncio.run(run_loop())
        └── while True:
              └── processes.run_all_sheets()
                    └── asyncio.gather(
                          process_sheet(sheet_1),
                          process_sheet(sheet_2),
                          ...               ← one task per entry in sheets_config.yaml
                          return_exceptions=True
                        )
                          │
                          ├── sheet/ ──────► AsyncSheetsClient (httpx.AsyncClient)
                          │                  KeyRotationPool (round-robin key selection)
                          │                  TokenCache (per-key OAuth2 JWT bearer token)
                          │                  ColSheetModel / RowModel (Pydantic v2 models)
                          │                  retry policies (tenacity decorators)
                          │
                          └── lapakgaming/ ► LapakgamingAPIClient (httpx.AsyncClient)
                                             retry policy (LAPAK_API_RETRY)
```

All concurrent sheet tasks share the module-level singletons (`key_rotation_pool`, `token_cache`, `async_sheets_client`, `lapakgaming_api_client`). Each task is independent: a failure in one sheet does not interrupt the others.

---

## 3. Module Boundaries

Each module has a single, clearly-scoped responsibility. Cross-boundary imports are forbidden except in `processes.py`.

### `src/app/lapakgaming/`

- **Responsibility:** All Lapakgaming API concerns only.
- **Contains:**
  - `LapakgamingAPIClient` — async HTTP client for the Lapakgaming marketplace API; uses `httpx.AsyncClient`; decorated with `@LAPAK_API_RETRY` on network methods
  - `lapakgaming_api_client` — module-level singleton; instantiated in `lapakgaming/__init__.py`
- **Rule:** No sheet logic, no `sheets_config.yaml` loading, no Google API calls.

### `src/app/sheet/`

- **Responsibility:** All Google Sheets concerns only.
- **Contains:**
  - `AsyncSheetsClient` — custom `httpx`-based async Sheets client (4 operations)
  - `KeyRotationPool` — round-robin service account key selector
  - `TokenCache` — per-key OAuth2 JWT bearer token cache
  - `ColSheetModel` / `RowModel` — Pydantic v2 data models; all classmethods that touch the Sheets API are `async def`
  - retry policies — `SHEETS_READ_RETRY`, `SHEETS_WRITE_RETRY` (lives at `src/app/shared/retry_policies.py`)
  - `key_rotation_pool`, `token_cache`, `async_sheets_client` singletons — instantiated in `sheet/__init__.py`
- **Rule:** No Lapakgaming API logic, no business rules.

### `src/app/processes.py`

- **Responsibility:** Orchestration and all business logic.
- **Rule:** The **only** file that imports from both `lapakgaming/` and `sheet/`. Contains `process_sheet()` and `run_all_sheets()`. All price comparison and update logic lives here.

### `src/app/utils.py`

- **Responsibility:** Pure helper functions — no I/O, no API calls.

### `src/app/_config.py`

- **Responsibility:** Configuration loading only.
- **Contains:**
  - `Config` — loaded from `settings.env` via `Config.model_validate(os.environ)` after `load_dotenv()`
  - `SheetsConfig` / `SheetEntry` — loaded from `sheets_config.yaml` via `load_sheets_config()`
  - `config` and `sheets_config` singletons (referenced from `app/__init__.py`)

### `src/app/shared/retry_policies.py`

- **Responsibility:** Named `tenacity` retry decorators used by `sheet/` and `lapakgaming/` modules.
- **Rule:** No business logic. Only `@SHEETS_READ_RETRY`, `@SHEETS_WRITE_RETRY`, `@LAPAK_API_RETRY` decorator definitions.

---

## 4. Key Components

### `KeyRotationPool` — `src/app/sheet/key_rotation.py`

Loads all `.json` service account key files from the `KEYS_FOLDER_PATH` directory at startup. Provides round-robin key selection via `itertools.cycle`.

- **`get_next_key()`** returns `(filename, key_data)` — a tuple of the key filename (basename) and its parsed JSON content.
- Raises `ValueError` if no `.json` files are found.
- Key **content** (`key_data`) is never logged — only the **filename** appears in logs.
- Startup log example:
  ```
  KeyRotationPool: loaded 3 keys: ['service-account-1.json', 'service-account-2.json', 'service-account-3.json']
  ```

### `TokenCache` — `src/app/sheet/auth.py`

Per-key OAuth2 JWT bearer token cache. Prevents redundant token refreshes and avoids race conditions when multiple concurrent sheet tasks request a token for the same key.

- Internal cache: `{filename: {"token": str, "expires_at": float}}`
- Per-key `asyncio.Lock` — ensures at most one concurrent refresh per key file.
- Token TTL is 3600 seconds; refreshed proactively when fewer than 60 seconds remain.
- Uses `PyJWT` to sign a JWT assertion, then POSTs to `https://oauth2.googleapis.com/token` via a one-shot `httpx.AsyncClient`.

### `AsyncSheetsClient` — `src/app/sheet/g_sheet.py`

Custom `httpx`-based async client for the Google Sheets v4 API. Replaces `gspread` entirely.

- One `httpx.AsyncClient(timeout=30.0)` instance created once at `__init__` and reused for all calls.
- Singleton: `async_sheets_client` in `src/app/sheet/__init__.py`.
- Provides 4 operations:

  | Method | HTTP | Retry Policy |
  |---|---|---|
  | `batch_get(spreadsheet_id, ranges)` | GET `/values:batchGet` | `@SHEETS_READ_RETRY` |
  | `batch_update(spreadsheet_id, data)` | POST `/values:batchUpdate` (`USER_ENTERED`) | `@SHEETS_WRITE_RETRY` |
  | `get_cell_value(spreadsheet_id, sheet_name, cell)` | GET single-range | `@SHEETS_READ_RETRY` |
  | `free_style_batch_update(spreadsheet_id, payload)` | POST flexible payload | `@SHEETS_WRITE_RETRY` |

- `_get_auth_headers()` calls `key_rotation_pool.get_next_key()` + `token_cache.get_token()` on every API call.
- HTTP 403 → immediate hard-fail (`PermissionError` raised, no retry); logged as:
  ```
  AsyncSheetsClient: HTTP 403 for key: service-account-X.json — permission denied
  ```
- Example API call log:
  ```
  AsyncSheetsClient.batch_get: spreadsheet=1BxiM… key=service-account-1.json
  ```

### Retry Policies — `src/app/shared/retry_policies.py`

Three named `tenacity` decorators used across the codebase:

| Decorator | Attempts | Backoff | Retried On |
|---|---|---|---|
| `SHEETS_READ_RETRY` | 5 | exponential 8–15 s | HTTP 429, 5xx, `TimeoutException`, `ConnectError` |
| `SHEETS_WRITE_RETRY` | 3 | exponential 20–40 s | HTTP 429, 5xx, `TimeoutException`, `ConnectError` |
| `LAPAK_API_RETRY` | 3 | fixed 0.5 s | 5xx, `TimeoutException`, `ConnectError` (not 429) |

All three use `reraise=True` (re-raise the original exception after exhausting retries) and `before_sleep=before_sleep_log(logger, logging.WARNING)` for observability. Retry warning log example:
```
WARNING ... Retrying ... in X seconds as it raised ...
```

**Rule:** Only decorate **leaf** network methods (the ones that actually make the HTTP call). Do **not** decorate composite methods that call those leaf methods — this avoids nested retry loops.

### `ColSheetModel` / `RowModel` — `src/app/sheet/models.py`

Pydantic v2 data models that map Google Sheets rows to Python objects.

- Column mapping is declared via field metadata: `{COL_META: "B"}` maps a field to column B.
- `IS_UPDATE_META: True` marks a field as writable (included in `batch_update` payloads).
- `IS_NOTE_META: True` marks a field as the error/note column (receives Vietnamese-language error messages on `ValidationError`).
- All classmethods that touch the Sheets API (`batch_get`, `batch_update`, `get_run_indexes`, `get_cell_value`, `free_style_batch_update`) are `async def`.

---

## 5. Concurrency Model

Each entry in `sheets_config.yaml` becomes an independent `asyncio` task. All tasks run concurrently via:

```python
results = await asyncio.gather(
    *[process_sheet(sheet) for sheet in sheets_config.sheets],
    return_exceptions=True,
)
```

**Per-sheet failure isolation:** `return_exceptions=True` means an unhandled exception in one sheet task is captured as a return value rather than propagated immediately. After `gather` returns, each result is checked:

```python
for sheet, result in zip(sheets_config.sheets, results):
    if isinstance(result, BaseException):
        logger.exception(
            f"Sheet '{sheet.name}' failed: {result}",
            exc_info=result,
        )
```

This guarantees that a failure in one sheet (e.g., revoked credentials, API error after retries exhausted) does not stop the other sheets from completing their round.

**`asyncio.run()` rule:** `asyncio.run()` is called **only** in `src/main.py`. It is never called inside any class method, module function, or test helper. All async entry points are reached via `await`.

---

## 6. Data Flow (Per-Sheet Execution)

The following steps describe a single `process_sheet(sheet)` execution:

1. **Key selection** — `KeyRotationPool.get_next_key()` returns `(filename, key_data)` for the next service account in round-robin order.

2. **Token acquisition** — `TokenCache.get_token(filename, key_data)` returns a valid OAuth2 Bearer token. If the cached token is expired or about to expire (< 60 s remaining), the cache refreshes it transparently using `PyJWT` + Google OAuth2 token endpoint.

3. **Batch read** — `AsyncSheetsClient.batch_get(spreadsheet_id, ranges)` fetches a batch of rows from the sheet. Decorated with `@SHEETS_READ_RETRY`.

4. **Model parsing** — `ColSheetModel.batch_get(...)` deserializes the raw Sheets response into a `list[RowModel]`. Rows that fail Pydantic `ValidationError` are caught: an error message (in **Vietnamese**) is written to that row's `NOTE` column and the row is skipped.

5. **API fetch** — `LapakgamingAPIClient.get_all_products()` calls the Lapakgaming marketplace API to retrieve current product prices. Decorated with `@LAPAK_API_RETRY`.

6. **Business logic** — `processes.py` compares the sheet data against the API results: identifies minimum prices, applies country code priority, computes the correct update values.

7. **Batch write** — `AsyncSheetsClient.batch_update(spreadsheet_id, data)` writes updated values back to the sheet using `USER_ENTERED` input mode. Decorated with `@SHEETS_WRITE_RETRY`.

8. **Completion log** — `logger.info(...)` records the batch completion with row count and sheet name.

The loop then sleeps (`RELAX_TIME_EACH_BATCH`) before the next batch, and sleeps again (`RELAX_TIME_EACH_ROUND`) between full processing rounds.

---

## 7. Error Handling Summary

| Condition | Behavior |
|---|---|
| HTTP 403 (permission denied) | Immediate hard-fail — `PermissionError` raised; logs key filename (not content); no retry |
| HTTP 429 / 5xx / timeout | Retried per named tenacity policy (`SHEETS_READ_RETRY` or `SHEETS_WRITE_RETRY`) |
| Lapakgaming API 5xx / timeout | Retried via `LAPAK_API_RETRY` (3 attempts, 0.5 s fixed; NOT retried on 429) |
| Pydantic `ValidationError` on a row | Error written to that row's `NOTE` column in **Vietnamese**; row skipped; processing continues |
| Sheet task unhandled exception | Captured by `asyncio.gather(return_exceptions=True)`; `logger.exception()` called; other sheets continue |
| No `.json` keys found at startup | `ValueError` raised in `KeyRotationPool.__init__`; process exits |
| Missing/invalid `settings.env` field | `ValidationError` at startup in `Config.model_validate(os.environ)`; process exits |
| Missing/invalid `sheets_config.yaml` | Startup error in `load_sheets_config()`; process exits with descriptive message |

---

## 8. Security Model

- **Service account key files** (`keys/*.json`) are gitignored. Only the **filename** (basename) appears in logs — the JSON key content is never logged or exposed.
- **`LAPAK_API_KEY`** is a Bearer token. It is passed only via the `Authorization: Bearer` HTTP header. It is never written to logs, query strings, or git history.
- **`settings.env`** is gitignored. All secrets (`LAPAK_API_KEY`) and environment-specific values live here and are never committed.
- All sensitive configuration is validated at startup. If any required variable is missing, the process exits immediately rather than running in a degraded state.
