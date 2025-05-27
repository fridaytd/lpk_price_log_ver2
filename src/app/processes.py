from datetime import datetime
from typing import Final

from app import config, logger

from .lpk.api_client import lpk_api_client
from .lpk.consts import COUNTRY_CODES
from .lpk.models import Product as LpkProduct
from .shared.decorators import retry_on_fail
from .sheet.enums import CheckType
from .sheet.models import BatchCellUpdatePayload, RowModel
from .utils import note_message, sleep_for, split_list

SEPERATED_CHAR: Final[str] = ","
RELAX_TIME_CELL: Final[str] = "O2"


def to_product_dict(
    products: list[LpkProduct],
) -> dict[str, LpkProduct]:
    return {product.code: product for product in products}


def lpk_product_code_from_str(
    str_code: str,
) -> list[str]:
    return [code.strip() for code in str_code.split(SEPERATED_CHAR)]


def is_valid_product(
    row_model: RowModel,
    lpk_product: LpkProduct,
) -> bool:
    if row_model.STATUS and lpk_product.status not in row_model.STATUS:
        return False

    if row_model.process_time and lpk_product.process_time > row_model.process_time:
        return False

    return True


def filter_valid_products(
    row_model: RowModel,
    lpk_products: list[LpkProduct],
) -> list[LpkProduct]:
    valid_products: list[LpkProduct] = []
    for lpk_product in lpk_products:
        if is_valid_product(row_model=row_model, lpk_product=lpk_product):
            valid_products.append(lpk_product)

    return valid_products


def min_lpk_products(
    row_model: RowModel,
    lpk_products: list[LpkProduct],
) -> LpkProduct | None:
    valid_products = filter_valid_products(row_model, lpk_products)
    if len(valid_products) == 0:
        return None
    min_price_products: list[LpkProduct] = []

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


def batch_update_price(
    to_be_updated_row_models: list[RowModel],
):
    update_dict: dict[str, dict[str, list[BatchCellUpdatePayload]]] = {}
    for row_model in to_be_updated_row_models:
        if row_model.ID_SHEET and row_model.SHEET and row_model.CELL:
            if row_model.ID_SHEET not in update_dict:
                update_dict[row_model.ID_SHEET] = {}
                update_dict[row_model.ID_SHEET][row_model.SHEET] = [
                    BatchCellUpdatePayload[str](
                        cell=row_model.CELL,
                        value=row_model.LOWEST_PRICE if row_model.LOWEST_PRICE else "",
                    )
                ]

            else:
                if row_model.SHEET not in update_dict[row_model.ID_SHEET]:
                    update_dict[row_model.ID_SHEET][row_model.SHEET] = [
                        BatchCellUpdatePayload[str](
                            cell=row_model.CELL,
                            value=row_model.LOWEST_PRICE
                            if row_model.LOWEST_PRICE
                            else "",
                        )
                    ]
                else:
                    update_dict[row_model.ID_SHEET][row_model.SHEET].append(
                        BatchCellUpdatePayload[str](
                            cell=row_model.CELL,
                            value=row_model.LOWEST_PRICE
                            if row_model.LOWEST_PRICE
                            else "",
                        )
                    )

    for sheet_id, sheet_names in update_dict.items():
        for sheet_name, update_batch in sheet_names.items():
            RowModel.free_style_batch_update(
                sheet_id=sheet_id, sheet_name=sheet_name, update_payloads=update_batch
            )


@retry_on_fail(max_retries=5, sleep_interval=10)
def batch_process(
    lpk_product_dict: dict[str, LpkProduct],
    indexes: list[int],
):
    # Get all run row from sheet
    logger.info(f"Get all run row from sheet: {indexes}")
    row_models = RowModel.batch_get(
        sheet_id=config.SPREADSHEET_KEY,
        sheet_name=config.SHEET_NAME,
        indexes=indexes,
    )

    to_be_updated_row_models: list[RowModel] = []

    # Process for each row model

    logger.info("Processing")
    for row_model in row_models:
        lpk_codes = lpk_product_code_from_str(row_model.code)
        __products = [
            lpk_product_dict[code] for code in lpk_codes if code in lpk_product_dict
        ]

        min_price_product = min_lpk_products(
            row_model=row_model, lpk_products=__products
        )

        if min_price_product is None:
            row_model.LOWEST_PRICE = ""
            row_model.NOTE = note_message(datetime.now(), min_price_product, __products)

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
            if row_model.FILL_IN == CheckType.RUN.value:
                to_be_updated_row_models.append(row_model)

    logger.info("Price sheet updating")
    batch_update_price(to_be_updated_row_models)

    logger.info("Sheet updating")
    RowModel.batch_update(
        sheet_id=config.SPREADSHEET_KEY,
        sheet_name=config.SHEET_NAME,
        list_object=row_models,
    )

    sleep_for(config.RELAX_TIME_EACH_BATCH)


def process():
    # Get all products from lapakgaming
    lpk_products: list[LpkProduct] = []
    logger.info("# Getting products from Lapakgaming")
    for country_code in COUNTRY_CODES.keys():
        __lpk_products = lpk_api_client.get_all_products(
            country_code=country_code
        ).data.products
        logger.info(
            f"### Total product for country code {country_code}: {len(__lpk_products)}"
        )
        lpk_products.extend(__lpk_products)

    logger.info(f"## Total product: {len(lpk_products)}")

    # Convert to dict with key: LpkProduct.code
    lpk_product_dict = to_product_dict(lpk_products)

    # Get run_indexes from sheet
    run_indexes = RowModel.get_run_indexes(
        sheet_id=config.SPREADSHEET_KEY,
        sheet_name=config.SHEET_NAME,
        col_index=2,
    )

    for batch_indexes in split_list(run_indexes, config.PROCESS_BATCH_SIZE):
        batch_process(
            lpk_product_dict=lpk_product_dict,
            indexes=batch_indexes,
        )

    str_relax_time = RowModel.get_cell_value(
        sheet_id=config.SPREADSHEET_KEY,
        sheet_name=config.SHEET_NAME,
        cell=RELAX_TIME_CELL,
    )

    sleep_for(float(str_relax_time) if str_relax_time else 10)
