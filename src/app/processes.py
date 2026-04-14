from datetime import datetime
from typing import Final
import asyncio

from app import config, logger
# Removed: fri_a1_range_to_grid_range was used only in the removed find_cell_to_update function
# from app.sheet.utils import fri_a1_range_to_grid_range
# Removed: async_sheets_client was used only in the removed find_cell_to_update function
# from .sheet import async_sheets_client

from .lapakgaming.api_client import lapakgaming_api_client
from .lapakgaming.consts import COUNTRY_CODES
from .lapakgaming.models import Product as LapakgamingProduct

# Removed: CheckType was used only in the removed FILL_IN check
# from .sheet.enums import CheckType
# Removed: BatchCellUpdatePayload was used only in the removed batch_update_price function
# from .sheet.models import BatchCellUpdatePayload
from .sheet.models import RowModel
from ._config import SheetEntry
from .utils import note_message, split_list

SEPERATED_CHAR: Final[str] = ","


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
            # Removed: FILL_IN / batch_update_price were removed from RowModel
            # if row_model.FILL_IN == CheckType.RUN.value:
            #     to_be_updated_row_models.append(row_model)

    # Removed: batch_update_price is removed (depended on FILL_IN, ID_SHEET, SHEET, COL_NOTE, COL_CODE)
    # if to_be_updated_row_models:
    #     await batch_update_price(to_be_updated_row_models, sheet_id, sheet_name)

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
):
    """Process a single sheet: fetch run indexes, then process batches in parallel groups."""
    logger.info(
        f"process_sheet: starting sheet='{sheet.name}' id={sheet.spreadsheet_id[:8]}…"
    )

    logger.info("Getting run indexes from sheet")
    # Get run_indexes from sheet
    run_indexes = await RowModel.get_run_indexes(
        sheet_id=sheet.spreadsheet_id,
        sheet_name=sheet.name,
        col="B",
    )

    logger.info(
        f"process_sheet: sheet='{sheet.name}' total_run_indexes={len(run_indexes)}"
    )

    # Split into individual batches, then group batches for parallel dispatch
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

    # Step 2: Process each sheet sequentially
    from app import sheets_config

    logger.info(
        f"process: processing {len(sheets_config.sheets)} sheet(s) sequentially"
    )
    for sheet in sheets_config.sheets:
        try:
            await process_sheet(sheet, lapakgaming_product_dict)
        except Exception as e:
            logger.error(
                f"process: sheet='{sheet.name}' failed with unhandled error: {e}",
                exc_info=True,
            )

    logger.info("process: all sheets processed")
