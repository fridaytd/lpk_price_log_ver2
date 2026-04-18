from datetime import datetime
from typing import Final
import asyncio

from pydantic import BaseModel

from app import config, logger

# Removed: fri_a1_range_to_grid_range was used only in the removed find_cell_to_update function
# from app.sheet.utils import fri_a1_range_to_grid_range
from .sheet import async_sheets_client

from .lapakgaming.api_client import lapakgaming_api_client
from .lapakgaming.consts import COUNTRY_CODES
from .lapakgaming.models import Product as LapakgamingProduct

# Removed: CheckType was used only in the removed FILL_IN check
# from .sheet.enums import CheckType
# Removed: BatchCellUpdatePayload was used only in the removed batch_update_price function
# from .sheet.models import BatchCellUpdatePayload
from .sheet.models import RowModel, ListingRowModel
from ._config import SheetEntry
from .utils import note_message, split_list, derive_codes_for_row, formated_datetime

SEPERATED_CHAR: Final[str] = ","

LISTING_START_ROW: Final[int] = 4
LOG_START_ROW: Final[int] = 3


class InExKeywordMapping(BaseModel):
    include_keywords: dict[str, list[str] | None]
    exclude_keywords: dict[str, list[str] | None]


# Removed: rowcol_to_a1 was used only in the removed find_cell_to_update function
# def rowcol_to_a1(row: int, col: int) -> str:
#     """Convert row and column numbers to A1 notation (e.g., 1, 1 -> A1)."""
#     if col < 1 or row < 1:
#         raise ValueError("Both row and column must be >= 1")
#
#     col_str = ""
#     while col > 0:
#         col -= 1
#         col_str = chr(ord("A") + (col % 26)) + col_str
#         col //= 26
#     return f"{col_str}{row}"


def to_product_dict(
    products: list[LapakgamingProduct],
) -> dict[str, LapakgamingProduct]:
    return {product.code: product for product in products}


def product_code_from_str(
    str_code: str,
) -> list[str]:
    return [code.strip() for code in str_code.split(SEPERATED_CHAR)]


def is_valid_product(
    row_model: RowModel,
    lapakgaming_product: LapakgamingProduct,
) -> bool:
    # Removed: STATUS and process_time were removed from RowModel
    # if row_model.STATUS and lapakgaming_product.status not in row_model.STATUS:
    #     return False

    # if (
    #     row_model.process_time
    #     and lapakgaming_product.process_time > row_model.process_time
    # ):
    #     return False

    return True


def filter_valid_products(
    row_model: RowModel,
    lapakgaming_products: list[LapakgamingProduct],
) -> list[LapakgamingProduct]:
    valid_products: list[LapakgamingProduct] = []
    for lapakgaming_product in lapakgaming_products:
        if is_valid_product(
            row_model=row_model, lapakgaming_product=lapakgaming_product
        ):
            valid_products.append(lapakgaming_product)

    return valid_products


def min_lapakgaming_products(
    row_model: RowModel,
    lapakgaming_products: list[LapakgamingProduct],
) -> LapakgamingProduct | None:
    valid_products = filter_valid_products(row_model, lapakgaming_products)
    if len(valid_products) == 0:
        return None
    min_price_products: list[LapakgamingProduct] = []

    for product in valid_products:
        if len(min_price_products) == 0:
            min_price_products.append(product)

        elif product.price == min_price_products[0].price:
            min_price_products.append(product)

        elif product.price < min_price_products[0].price:
            min_price_products = [product]

    if len(min_price_products) == 0:
        return None

    if len(min_price_products) == 1 or row_model.country_code_priority is None:
        return min_price_products[0]

    for country_code in [
        code.strip() for code in row_model.country_code_priority.split(SEPERATED_CHAR)
    ]:
        for product in min_price_products:
            if product.country_code in country_code:
                return product

    return min_price_products[0]


# Removed: find_cell_to_update used fields (FILL_IN, ID_SHEET, SHEET, COL_NOTE, CODE, COL_CODE)
# that were removed from RowModel.
# async def find_cell_to_update(
#     row_models: list[RowModel], sheet_id: str
# ) -> dict[str, str]:
#     mapping_dict: dict[str, str] = {}
#
#     sheet_get_batch_dict: dict[str, dict[str, list[str]]] = {}
#
#     for row_model in row_models:
#         if (
#             row_model.FILL_IN
#             and row_model.ID_SHEET
#             and row_model.SHEET
#             and row_model.COL_NOTE
#             and row_model.CODE
#             and row_model.COL_CODE
#         ):
#             range_code = f"{row_model.COL_CODE}:{row_model.COL_CODE}"
#             if row_model.ID_SHEET not in sheet_get_batch_dict:
#                 sheet_get_batch_dict[row_model.ID_SHEET] = {}
#                 sheet_get_batch_dict[row_model.ID_SHEET][row_model.SHEET] = [range_code]
#             else:
#                 if row_model.SHEET not in sheet_get_batch_dict[row_model.ID_SHEET]:
#                     sheet_get_batch_dict[row_model.ID_SHEET][row_model.SHEET] = [
#                         range_code
#                     ]
#                 else:
#                     sheet_get_batch_dict[row_model.ID_SHEET][row_model.SHEET].append(
#                         range_code
#                     )
#
#     # Use async_sheets_client instead of gspread
#     ranges_to_read = []
#     for id_sheet, sheet_names in sheet_get_batch_dict.items():
#         for name, ranges in sheet_names.items():
#             for range_code in ranges:
#                 ranges_to_read.append(f"{name}!{range_code}")
#
#     if not ranges_to_read:
#         return mapping_dict
#
#     response = await async_sheets_client.batch_get(sheet_id, ranges_to_read)
#     value_ranges = response.get("valueRanges", [])
#
#     # Build result dict similar to original
#     sheet_get_batch_result_dict: dict[str, dict[str, dict[str, list]]] = {}
#     range_index = 0
#
#     for id_sheet, sheet_names in sheet_get_batch_dict.items():
#         for name, ranges in sheet_names.items():
#             for range_code in ranges:
#                 if range_index < len(value_ranges):
#                     values = value_ranges[range_index].get("values", [])
#                     if id_sheet not in sheet_get_batch_result_dict:
#                         sheet_get_batch_result_dict[id_sheet] = {}
#                     if name not in sheet_get_batch_result_dict[id_sheet]:
#                         sheet_get_batch_result_dict[id_sheet][name] = {}
#                     sheet_get_batch_result_dict[id_sheet][name][range_code] = values
#                 range_index += 1
#
#     for row_model in row_models:
#         if (
#             row_model.ID_SHEET
#             and row_model.SHEET
#             and row_model.COL_NOTE
#             and row_model.CODE
#             and row_model.COL_CODE
#         ):
#             # Convert to A1 notation
#             range_code = f"{row_model.COL_CODE}:{row_model.COL_CODE}"
#             range_note = f"{row_model.COL_NOTE}:{row_model.COL_NOTE}"
#
#             codes_grid = (
#                 sheet_get_batch_result_dict.get(row_model.ID_SHEET, {})
#                 .get(row_model.SHEET, {})
#                 .get(range_code, [])
#             )
#
#             code_grid_range = fri_a1_range_to_grid_range(range_code)
#             note_grid_range = fri_a1_range_to_grid_range(range_note)
#             for i, code_row in enumerate(codes_grid):
#                 for j, code_col in enumerate(code_row):
#                     if (
#                         isinstance(code_col, str)
#                         and row_model.CODE.strip() == code_col.strip()
#                     ):
#                         target_row_index = i + 1 + code_grid_range.startRowIndex
#                         target_col_index = j + 1 + note_grid_range.startColumnIndex
#                         mapping_dict[str(row_model.index)] = rowcol_to_a1(
#                             target_row_index, target_col_index
#                         )
#
#     return mapping_dict


# Removed: batch_update_price used fields (ID_SHEET, SHEET, COL_NOTE) removed from RowModel,
# and calls find_cell_to_update which is also removed.
# async def batch_update_price(
#     to_be_updated_row_models: list[RowModel],
#     sheet_id: str,
#     sheet_name: str,
# ):
#     update_dict: dict[str, dict[str, list[BatchCellUpdatePayload]]] = {}
#
#     update_cell_mapping = await find_cell_to_update(to_be_updated_row_models, sheet_id)
#
#     for row_model in to_be_updated_row_models:
#         if row_model.ID_SHEET and row_model.SHEET and row_model.COL_NOTE:
#             if row_model.ID_SHEET not in update_dict:
#                 update_dict[row_model.ID_SHEET] = {}
#
#             if row_model.SHEET not in update_dict[row_model.ID_SHEET]:
#                 update_dict[row_model.ID_SHEET][row_model.SHEET] = []
#
#             if str(row_model.index) in update_cell_mapping:
#                 update_dict[row_model.ID_SHEET][row_model.SHEET].append(
#                     BatchCellUpdatePayload[str](
#                         cell=update_cell_mapping[str(row_model.index)],
#                         value=row_model.LOWEST_PRICE if row_model.LOWEST_PRICE else "",
#                     )
#                 )
#
#     for sheet_id, sheet_names in update_dict.items():
#         for sheet_name, update_batch in sheet_names.items():
#             await RowModel.free_style_batch_update(
#                 sheet_id=sheet_id, sheet_name=sheet_name, update_payloads=update_batch
#             )


async def batch_process(
    lapakgaming_product_dict: dict[str, LapakgamingProduct],
    indexes: list[int],
    sheet_id: str,
    sheet_name: str,
    listing_codes: list[str | None],
    listing_country_codes: list[str | None],
):
    # Get all run row from sheet
    logger.info(
        f"batch_process: reading rows {indexes[0]}–{indexes[-1]} from {sheet_name}"
    )
    row_models = await RowModel.batch_get(
        sheet_id=sheet_id,
        sheet_name=sheet_name,
        indexes=indexes,
    )

    # Process for each row model
    for row_model in row_models:
        # Derive product codes from listing data
        codes = derive_codes_for_row(
            col_a_prefix=row_model.Code_Prefix,
            col_f_country_filter=row_model.country_code_priority,
            listing_codes=listing_codes,
            listing_country_codes=listing_country_codes,
        )
        row_model.code = SEPERATED_CHAR.join(codes)

        product_codes = product_code_from_str(row_model.code)
        __products = [
            lapakgaming_product_dict[code]
            for code in product_codes
            if code in lapakgaming_product_dict
        ]

        min_price_product = min_lapakgaming_products(
            row_model=row_model, lapakgaming_products=__products
        )

        if min_price_product is None:
            row_model.LOWEST_PRICE = ""
            row_model.NOTE = note_message(datetime.now(), min_price_product, __products)
            row_model.LOG_CODE = ""
            row_model.LOG_COUNTRY = ""

        else:
            row_model.LOWEST_PRICE = str(min_price_product.price)
            row_model.NOTE = note_message(
                datetime.now(),
                min_price_product,
                [
                    product
                    for product in __products
                    if product.code != min_price_product.code
                ],
            )
            row_model.LOG_CODE = min_price_product.code
            row_model.LOG_COUNTRY = min_price_product.country_code

    logger.info(f"batch_process: writing sheet for rows {indexes[0]}–{indexes[-1]}")
    await RowModel.batch_update(
        sheet_id=sheet_id,
        sheet_name=sheet_name,
        list_object=row_models,
    )

    logger.info(
        f"batch_process: complete — sheet={sheet_name} "
        f"rows={indexes[0]}–{indexes[-1]} "
        f"rows_read={len(row_models)}"
    )


async def process_sheet(
    sheet: SheetEntry,
    lapakgaming_product_dict: dict[str, LapakgamingProduct],
    listing_codes: list[str | None],
    listing_country_codes: list[str | None],
):
    """Process a single logging sheet: derive codes then fetch/update prices."""
    logger.info(
        f"process_sheet: starting sheet='{sheet.name}' id={sheet.spreadsheet_id[:8]}…"
    )

    # Step 1: Get active run indexes from col A (non-empty value)
    run_indexes = await RowModel.get_run_indexes(
        sheet_id=sheet.spreadsheet_id,
        sheet_name=sheet.name,
    )

    # Filter run index
    run_indexes = [index for index in run_indexes if index >= LOG_START_ROW]

    logger.info(
        f"process_sheet: sheet='{sheet.name}' total_run_indexes={len(run_indexes)}"
    )

    if not run_indexes:
        logger.info(f"process_sheet: no active rows — sheet='{sheet.name}'")
        return

    # Step 2: Process price updates in parallel batches (code derivation happens inside each batch)
    batches = split_list(run_indexes, config.PROCESS_BATCH_SIZE)
    batch_groups = split_list(batches, config.PARALLEL_BATCH_COUNT)
    for group_idx, group in enumerate(batch_groups):
        first_row = group[0][0] if group and group[0] else "?"
        last_row = group[-1][-1] if group and group[-1] else "?"
        logger.info(
            f"process_sheet: sheet='{sheet.name}' dispatching group {group_idx + 1}/{len(batch_groups)} "
            f"({len(group)} batches, rows {first_row}–{last_row})"
        )
        results = await asyncio.gather(
            *[
                batch_process(
                    lapakgaming_product_dict=lapakgaming_product_dict,
                    indexes=batch,
                    sheet_id=sheet.spreadsheet_id,
                    sheet_name=sheet.name,
                    listing_codes=listing_codes,
                    listing_country_codes=listing_country_codes,
                )
                for batch in group
            ],
            return_exceptions=True,
        )
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                batch = group[i]
                logger.error(
                    f"process_sheet: batch failed — sheet='{sheet.name}' "
                    f"rows={batch[0]}–{batch[-1]}: {result}",
                    exc_info=result,
                )
        logger.info(
            f"process_sheet: group {group_idx + 1}/{len(batch_groups)} complete — sheet='{sheet.name}'"
        )

    logger.info(
        f"process_sheet: all batches complete — sheet='{sheet.name}' "
        f"total_run_indexes={len(run_indexes)}"
    )


async def get_include_exclude_keywords(
    sheet_id: str, sheet_name: str
) -> InExKeywordMapping:
    """Read include/exclude keyword config from listing sheet rows 2 and 3."""
    rows = await ListingRowModel.batch_get(
        sheet_id=sheet_id,
        sheet_name=sheet_name,
        indexes=[2, 3],  # row 2 = include keywords, row 3 = exclude keywords
    )

    updated_fields = ListingRowModel.updated_mapping_fields()  # B–J fields only

    include_dict: dict[str, list[str] | None] = {}
    exclude_dict: dict[str, list[str] | None] = {}

    include_row = (
        rows[0]
        if len(rows) > 0
        else ListingRowModel(sheet_id=sheet_id, sheet_name=sheet_name, index=2)
    )
    exclude_row = (
        rows[1]
        if len(rows) > 1
        else ListingRowModel(sheet_id=sheet_id, sheet_name=sheet_name, index=3)
    )

    for field_name in updated_fields:
        inc_val = getattr(include_row, field_name)
        include_dict[field_name] = (
            [k.strip() for k in inc_val.split(SEPERATED_CHAR) if k.strip()]
            if inc_val
            else None
        )
        exc_val = getattr(exclude_row, field_name)
        exclude_dict[field_name] = (
            [k.strip() for k in exc_val.split(SEPERATED_CHAR) if k.strip()]
            if exc_val
            else None
        )

    return InExKeywordMapping(
        include_keywords=include_dict,
        exclude_keywords=exclude_dict,
    )


def is_valid_listing_product(
    product: LapakgamingProduct,
    include_keywords: dict[str, list[str] | None],
    exclude_keywords: dict[str, list[str] | None],
) -> bool:
    """Return True if product passes all include/exclude keyword filters."""
    for field_name, keywords in include_keywords.items():
        if keywords is not None:
            field_val = getattr(product, field_name, None) or ""
            if all(kw not in str(field_val) for kw in keywords):
                return False
    for field_name, keywords in exclude_keywords.items():
        if keywords is not None:
            field_val = getattr(product, field_name, None) or ""
            if any(kw in str(field_val) for kw in keywords):
                return False
    return True


async def _clear_listing_sheet_stale_rows(
    sheet_id: str,
    sheet_name: str,
    start_row: int,
) -> None:
    """Clear all rows from start_row to the last row that actually has data in the sheet.

    Uses batchClear API. The end row is derived by reading column A to find the real
    extent of data — no hardcoded lookahead constant needed.
    """
    col_b_values = await async_sheets_client.get_column_values(
        sheet_id, sheet_name, "B"
    )
    last_data_row = len(col_b_values)  # 1-based: row count == last occupied row index

    if start_row > last_data_row:
        logger.info(
            f"_clear_listing_sheet_stale_rows: nothing to clear on sheet='{sheet_name}' "
            f"(start_row={start_row} > last_data_row={last_data_row})"
        )
        return

    ranges = [f"{sheet_name}!A{start_row}:K{last_data_row}"]
    await async_sheets_client.batch_clear(sheet_id, ranges)
    logger.info(
        f"_clear_listing_sheet_stale_rows: cleared rows {start_row}–{last_data_row} on sheet='{sheet_name}'"
    )


async def process_listing_sheet(
    sheet: SheetEntry,
    all_products: list[LapakgamingProduct],
) -> list[LapakgamingProduct]:
    """Process a single listing sheet: filter products by keywords and write to sheet."""
    logger.info(
        f"process_listing_sheet: starting sheet='{sheet.name}' id={sheet.spreadsheet_id[:8]}…"
    )

    # Step 1: Read keyword config from rows 2 and 3
    keyword_mapping = await get_include_exclude_keywords(
        sheet.spreadsheet_id, sheet.name
    )

    # Step 2: Filter products
    valid_products = [
        p
        for p in all_products
        if is_valid_listing_product(
            p, keyword_mapping.include_keywords, keyword_mapping.exclude_keywords
        )
    ]
    logger.info(
        f"process_listing_sheet: sheet='{sheet.name}' valid_products={len(valid_products)}"
    )

    # Step 3: Build ListingRowModel instances starting at row 4
    row_models: list[ListingRowModel] = []
    for i, product in enumerate(valid_products):
        row_models.append(
            ListingRowModel(
                sheet_id=sheet.spreadsheet_id,
                sheet_name=sheet.name,
                index=LISTING_START_ROW + i,
                code=product.code,
                category_code=product.category_code,
                name=product.name,
                provider_code=product.provider_code,
                price=str(product.price),
                process_time=str(product.process_time),
                country_code=product.country_code,
                status=product.status,
                Note=formated_datetime(datetime.now()),
            )
        )

    # Step 4: Write in batches
    if row_models:
        batches = split_list(row_models, config.LISTING_BATCH_SIZE)
        batch_groups = split_list(batches, config.LISTING_PARALLEL_BATCH_COUNT)

        for group_idx, group in enumerate(batch_groups):
            first_row = group[0][0].index if group and group[0] else "?"
            last_row = group[-1][-1].index if group and group[-1] else "?"
            logger.info(
                f"process_listing_sheet: sheet='{sheet.name}' dispatching group {group_idx + 1}/{len(batch_groups)} "
                f"({len(group)} batches, rows {first_row}–{last_row})"
            )
            results = await asyncio.gather(
                *[
                    ListingRowModel.batch_update(
                        sheet_id=sheet.spreadsheet_id,
                        sheet_name=sheet.name,
                        list_object=batch,
                    )
                    for batch in group
                ],
                return_exceptions=True,
            )
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    batch = group[i]
                    logger.error(
                        f"process_listing_sheet: batch failed — sheet='{sheet.name}' "
                        f"rows={batch[0].index}–{batch[-1].index}: {result}",
                        exc_info=result,
                    )
            logger.info(
                f"process_listing_sheet: group {group_idx + 1}/{len(batch_groups)} complete — sheet='{sheet.name}'"
            )

    # Step 5: Clear stale rows beyond the last written row
    clear_start = LISTING_START_ROW + len(valid_products)
    await _clear_listing_sheet_stale_rows(
        sheet_id=sheet.spreadsheet_id,
        sheet_name=sheet.name,
        start_row=clear_start,
    )
    logger.info(
        f"process_listing_sheet: complete — sheet='{sheet.name}' "
        f"total_valid_products={len(valid_products)}"
    )
    return valid_products


async def _fetch_products_for_country(country_code: str) -> list[LapakgamingProduct]:
    """Fetch all products for a single country code. Logs errors and returns empty list on failure."""
    try:
        result = await lapakgaming_api_client.get_all_products(
            country_code=country_code
        )
        products = result.data.products
        logger.info(
            f"_fetch_products_for_country: country_code={country_code} count={len(products)}"
        )
        return products
    except Exception as e:
        logger.error(
            f"_fetch_products_for_country: failed for country_code={country_code}: {e}",
            exc_info=True,
        )
        return []


async def process():
    # Step 1: Fetch all lapakgaming products in parallel (one task per country code)
    logger.info(
        "process: fetching lapakgaming products for all country codes in parallel"
    )
    country_codes = list(COUNTRY_CODES.keys())
    results = await asyncio.gather(
        *[_fetch_products_for_country(cc) for cc in country_codes],
        return_exceptions=True,
    )

    all_products: list[LapakgamingProduct] = []
    for cc, result in zip(country_codes, results):
        if isinstance(result, BaseException):
            logger.error(
                f"process: country_code={cc} fetch failed: {result}", exc_info=result
            )
        else:
            all_products.extend(result)

    logger.info(f"process: total products fetched = {len(all_products)}")

    # Convert to dict keyed by product code (shared across all sheets)
    lapakgaming_product_dict = to_product_dict(all_products)

    # Step 2: Listing phase — update all listing sheets, collect listing data
    from app import sheets_config

    logger.info(
        f"process: listing phase — processing {len(sheets_config.listing_sheets)} listing sheet(s)"
    )
    all_listing_products: list[LapakgamingProduct] = []
    for sheet in sheets_config.listing_sheets:
        try:
            listing_products = await process_listing_sheet(sheet, all_products)
            all_listing_products.extend(listing_products)
        except Exception as e:
            logger.error(
                f"process: listing sheet='{sheet.name}' failed with unhandled error: {e}",
                exc_info=True,
            )

    logger.info("process: listing phase complete, starting logging phase")

    # Step 3: Logging phase — derive codes + process prices for each logging sheet
    all_listing_codes: list[str | None] = [p.code for p in all_listing_products]
    all_listing_country_codes: list[str | None] = [
        p.country_code for p in all_listing_products
    ]

    logger.info(
        f"process: processing {len(sheets_config.logging_sheets)} logging sheet(s) sequentially, "
        f"{len(all_listing_codes)} listing codes available"
    )
    for sheet in sheets_config.logging_sheets:
        try:
            await process_sheet(
                sheet,
                lapakgaming_product_dict,
                all_listing_codes,
                all_listing_country_codes,
            )
        except Exception as e:
            logger.error(
                f"process: sheet='{sheet.name}' failed with unhandled error: {e}",
                exc_info=True,
            )

    logger.info("process: all sheets processed")
    await asyncio.sleep(config.RELAX_AFTER_EACH_ROUND)
