# Managing Keys

This guide explains how to add or remove Google service account key files in the `lpk_price_log_ver2` worker.

---

## Overview

The worker authenticates to the Google Sheets API using service account JSON key files. All `.json` files in the keys folder are loaded at startup, and the system rotates across them in round-robin order — one key is used per API call. This spreads request load across multiple service accounts to stay within Google API quotas.

Key files are stored in the keys folder and are gitignored — they are never committed to version control.

---

## Finding the Keys Folder

The keys folder location is configured by `KEYS_FOLDER_PATH` in your `settings.env` file. The default value is:

```env
KEYS_FOLDER_PATH="./keys"
```

This resolves to the `keys/` folder at the project root. To use a different folder, update `KEYS_FOLDER_PATH` in `settings.env` and restart the process.

---

## Adding a Key

1. Obtain the service account JSON key file from Google Cloud Console:
   - Navigate to **IAM & Admin → Service Accounts**
   - Select the service account
   - Go to the **Keys** tab
   - Click **Add Key → Create new key → JSON**
   - Download the `.json` file

2. Ensure the service account has Google Sheets API read/write permission for all target spreadsheets. Share each Google Sheet with the service account's email address (found in the JSON key file under `client_email`), granting **Editor** access.

3. Place the `.json` file in the keys folder:

   ```
   keys/
   └── service-account-1.json   ← place new key file here
   ```

4. Restart the process:

   ```bash
   uv run python src/main.py
   ```

5. Verify in the startup log that the new key is loaded:

   ```
   KeyRotationPool: loaded 3 keys: ['service-account-1.json', 'service-account-2.json', 'service-account-3.json']
   ```

   The key count and filename list should include your new file.

---

## Removing a Key

1. Delete the `.json` file from the keys folder.

2. Restart the process:

   ```bash
   uv run python src/main.py
   ```

The removed key will no longer appear in startup logs or be used for any API calls.

---

## Security Notes

- **Keys are gitignored** — the `keys/` folder is listed in `.gitignore`. Never commit key files to the repository; never paste key contents into source files or logs.
- **Key filenames appear in logs** — the filename (e.g., `service-account-1.json`) is logged at startup and during error events. The key _contents_ (private key, credentials) are never logged.
- **Revoked or invalid keys** — if a key is revoked or loses permissions, the worker logs the filename and halts processing for the affected sheet:

  ```
  AsyncSheetsClient: HTTP 403 for key: service-account-1.json — permission denied
  ```

  **Operator action:** Remove the offending `.json` file from the keys folder and restart the process. If the key was revoked in Google Cloud Console, create and download a new one before restarting.

---

## Key Rotation Behavior

With N keys and M sheets processing concurrently, each API call selects the next key in round-robin order. This distributes calls evenly across all loaded keys.

**Recommended:** Use **3 or more keys** for a 5-sheet workload. Each service account is subject to Google Sheets API quotas of 60 reads/min and 60 writes/min. Distributing calls across multiple service accounts reduces the risk of hitting per-account rate limits.

Each key's OAuth2 Bearer token is cached for up to ~1 hour and automatically refreshed when expired — no manual token management is required.
