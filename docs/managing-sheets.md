# Managing Sheets

This guide explains how to add or remove target Google Sheets in the `lpk_price_log_ver2` worker.

---

## Overview

Sheets are defined in the `sheets_config.yaml` file at the project root. The worker reads this file at startup and processes all defined sheets concurrently. Up to 5 sheets are supported.

To add or remove a sheet: **edit `sheets_config.yaml` and restart the process**. No code changes are required.

---

## Adding a Sheet

1. Open `sheets_config.yaml` at the project root.

2. Copy an existing entry block (the two-line `name` + `spreadsheet_id` pair):

   ```yaml
   - name: "GameCategory1"
     spreadsheet_id: "1BxiM..."
   ```

3. Paste it as a new entry under `sheets:` and replace the values:
   - `name` — a human-readable label for this sheet (used in logs and error messages; can be anything descriptive)
   - `spreadsheet_id` — the Google Sheets spreadsheet ID from the URL

   **Finding the spreadsheet ID:** Open the target sheet in your browser. The ID is the long string in the URL between `/d/` and `/edit`:
   ```
   https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit
   ```

4. Save the file.

5. Restart the process:

   ```bash
   uv run python src/main.py
   ```

6. Verify in the startup log that the new sheet appears:

   ```
   Loaded 3 sheets from config
   ```

   The count should reflect the new total number of sheets.

---

## Removing a Sheet

1. Open `sheets_config.yaml` at the project root.

2. Delete the entire entry block for the sheet you want to remove (both the `name` and `spreadsheet_id` lines).

3. Save the file.

4. Restart the process:

   ```bash
   uv run python src/main.py
   ```

The removed sheet will no longer appear in startup or processing logs.

---

## Config Format Reference

The full structure of `sheets_config.yaml` with inline explanations:

```yaml
# sheets_config.yaml — Multi-sheet configuration for lpk_price_log_ver2
# Edit this file and restart the process to add/remove sheets (no code changes required).

sheets:
  - name: "GameCategory1"          # Human-readable label; appears in logs
    spreadsheet_id: "1BxiM..."     # Google Sheets ID from URL

  - name: "GameCategory2"          # Second target sheet
    spreadsheet_id: "2CyiN..."     # Replace with actual spreadsheet ID
```

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Human-readable label; appears in log output and error messages |
| `spreadsheet_id` | Yes | Google Sheets spreadsheet ID from the sheet URL |

---

## Validation Errors

If the process exits at startup with an error such as:

```
ERROR: Invalid sheets_config.yaml schema
```

Check that:
- The `sheets_config.yaml` file exists at the project root
- The YAML syntax is valid (no missing colons, incorrect indentation, etc.)
- Every entry has both `name` and `spreadsheet_id` fields present

These errors are detected before any sheet processing begins — no partial processing will have occurred.
