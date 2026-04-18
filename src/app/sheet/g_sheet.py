import asyncio
import logging
from typing import Any, Final

import httpx

from ..shared.retry_policies import SHEETS_READ_RETRY, SHEETS_WRITE_RETRY

logger = logging.getLogger(__name__)

# P2: Final[str] annotation per project constant convention
SHEETS_BASE_URL: Final[str] = "https://sheets.googleapis.com/v4/spreadsheets"


class AsyncSheetsClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=None)

    def _handle_response(self, resp: httpx.Response, key_filename: str) -> None:
        if resp.status_code == 403:
            logger.error(
                f"AsyncSheetsClient: HTTP 403 for key: {key_filename} — permission denied"
            )
            raise PermissionError(f"Google Sheets 403 for key: {key_filename}")
        if not resp.is_success:
            logger.error(
                f"AsyncSheetsClient: HTTP {resp.status_code} for key: {key_filename}"
            )
        resp.raise_for_status()

    async def _execute_with_key_rotation(
        self,
        make_request,  # async callable(headers: dict) -> httpx.Response
    ) -> tuple[str, httpx.Response]:
        """
        Execute `make_request` with automatic key rotation on HTTP 429.

        Rotation strategy:
        - On each call, fetch the next key from the pool.
        - If a key returns 429, log the event and immediately try the next key.
        - Once every key in the pool has been tried (detected by seeing a key we
          already tried this cycle), log the all-keys-exhausted event, sleep
          RATE_LIMIT_WAIT_SECONDS, then restart the tried-set and continue.
        - Non-429 errors fall through: `_handle_response` raises them for the
          tenacity decorators (SHEETS_READ_RETRY / SHEETS_WRITE_RETRY) to handle.
        """
        from . import key_rotation_pool, token_cache  # Lazy import to avoid circular
        from .. import config

        tried: set[str] = set()
        pool_size = key_rotation_pool.pool_size

        while True:
            filename, key_data = key_rotation_pool.get_next_key()
            token = await token_cache.get_token(filename, key_data)
            headers = {"Authorization": f"Bearer {token}"}

            if filename in tried:
                # Full cycle exhausted — all keys returned 429
                wait_secs = config.RATE_LIMIT_WAIT_SECONDS
                if pool_size == 1:
                    logger.warning(
                        f"AsyncSheetsClient: only 1 key available, key {filename} hit 429 — "
                        f"waiting {wait_secs}s before retry"
                    )
                else:
                    logger.warning(
                        f"AsyncSheetsClient: all {len(tried)} key(s) hit 429 — "
                        f"waiting {wait_secs}s before restarting key cycle"
                    )
                await asyncio.sleep(wait_secs)
                tried.clear()

            tried.add(filename)
            logger.info(f"AsyncSheetsClient: using key {filename}")

            resp = await make_request(headers)

            if resp.status_code == 429:
                logger.warning(
                    f"AsyncSheetsClient: 429 rate-limit on key {filename} — rotating to next key "
                    f"({len(tried)}/{pool_size} keys tried this cycle)"
                )
                continue

            # Non-429: delegate error handling (raises on 403/5xx/etc.)
            self._handle_response(resp, filename)
            logger.debug(f"AsyncSheetsClient: request succeeded with key {filename}")
            return filename, resp

    @SHEETS_READ_RETRY
    async def batch_get(self, spreadsheet_id: str, ranges: list[str]) -> dict:
        # P5: skip API call on empty ranges
        if not ranges:
            return {}
        logger.info(f"AsyncSheetsClient.batch_get: spreadsheet={spreadsheet_id[:8]}…")

        async def make_request(headers: dict) -> httpx.Response:
            return await self._client.get(
                f"{SHEETS_BASE_URL}/{spreadsheet_id}/values:batchGet",
                headers=headers,
                params={"ranges": ranges, "valueRenderOption": "FORMATTED_VALUE"},
            )

        _, resp = await self._execute_with_key_rotation(make_request)
        return resp.json()

    @SHEETS_WRITE_RETRY
    async def batch_update(
        self, spreadsheet_id: str, data: list[dict[str, Any]]
    ) -> None:
        # P5: skip API call on empty data
        if not data:
            return
        logger.info(
            f"AsyncSheetsClient.batch_update: spreadsheet={spreadsheet_id[:8]}…"
        )

        async def make_request(headers: dict) -> httpx.Response:
            return await self._client.post(
                f"{SHEETS_BASE_URL}/{spreadsheet_id}/values:batchUpdate",
                headers=headers,
                json={"valueInputOption": "USER_ENTERED", "data": data},
            )

        await self._execute_with_key_rotation(make_request)

    @SHEETS_READ_RETRY
    async def get_cell_value(
        self, spreadsheet_id: str, sheet_name: str, cell: str
    ) -> Any | None:
        logger.info(
            f"AsyncSheetsClient.get_cell_value: spreadsheet={spreadsheet_id[:8]}…"
        )
        # P4: escape single-quotes in sheet_name per Google Sheets A1 notation rules
        safe_sheet_name = sheet_name.replace("'", "''")
        range_notation = f"'{safe_sheet_name}'!{cell}"

        async def make_request(headers: dict) -> httpx.Response:
            return await self._client.get(
                f"{SHEETS_BASE_URL}/{spreadsheet_id}/values/{range_notation}",
                headers=headers,
                params={"valueRenderOption": "UNFORMATTED_VALUE"},
            )

        _, resp = await self._execute_with_key_rotation(make_request)
        data = resp.json()
        values = data.get("values")
        if values and values[0]:
            return values[0][0]
        return None

    @SHEETS_READ_RETRY
    async def get_column_values(
        self, spreadsheet_id: str, sheet_name: str, col: str
    ) -> list[Any]:
        """Get all values in a column (e.g. "A") as a list.

        Returns:
             List of cell values in the column, in order from top to bottom.
             Empty cells are returned as empty strings. Trailing empty cells are not included.
             Example: ["Header", "Value1", "Value2", "", ""] -> ["Header", "Value1", "Value2"]
        """
        logger.info(
            f"AsyncSheetsClient.get_column_values: spreadsheet={spreadsheet_id[:8]}…"
        )
        # P4: escape single-quotes in sheet_name per Google Sheets A1 notation rules
        safe_sheet_name = sheet_name.replace("'", "''")
        # Read entire column (Google Sheets API automatically determines the extent)
        range_notation = f"'{safe_sheet_name}'!{col}:{col}"

        async def make_request(headers: dict) -> httpx.Response:
            return await self._client.get(
                f"{SHEETS_BASE_URL}/{spreadsheet_id}/values/{range_notation}",
                headers=headers,
                params={
                    "valueRenderOption": "FORMATTED_VALUE",
                    "majorDimension": "COLUMNS",
                },
            )

        _, resp = await self._execute_with_key_rotation(make_request)
        data = resp.json()
        values = data.get("values", [])
        return values[0] if values else []

    @SHEETS_WRITE_RETRY
    async def batch_clear(
        self, spreadsheet_id: str, ranges: list[str]
    ) -> None:
        """Clear the content of the given ranges using the batchClear API."""
        if not ranges:
            return
        logger.info(
            f"AsyncSheetsClient.batch_clear: spreadsheet={spreadsheet_id[:8]}…"
        )

        async def make_request(headers: dict) -> httpx.Response:
            return await self._client.post(
                f"{SHEETS_BASE_URL}/{spreadsheet_id}/values:batchClear",
                headers=headers,
                json={"ranges": ranges},
            )

        await self._execute_with_key_rotation(make_request)

    @SHEETS_WRITE_RETRY
    async def free_style_batch_update(
        self, spreadsheet_id: str, payload: list[Any]
    ) -> None:
        # P5: skip API call on empty payload
        if not payload:
            return
        logger.info(
            f"AsyncSheetsClient.free_style_batch_update: spreadsheet={spreadsheet_id[:8]}…"
        )
        data = [{"range": p.cell, "values": [[p.value]]} for p in payload]

        async def make_request(headers: dict) -> httpx.Response:
            return await self._client.post(
                f"{SHEETS_BASE_URL}/{spreadsheet_id}/values:batchUpdate",
                headers=headers,
                json={"valueInputOption": "USER_ENTERED", "data": data},
            )

        await self._execute_with_key_rotation(make_request)


async_sheets_client = AsyncSheetsClient()
