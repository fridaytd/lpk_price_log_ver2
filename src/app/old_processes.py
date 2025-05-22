from datetime import datetime
from typing import Final

from app import config, logger
from .sheet.models import Product
from .lpk.api_client import lpk_api_client
from .lpk.consts import COUNTRY_CODES
from .lpk.models import Product as LpkProduct

from .utils import sleep_for, formated_datetime, split_list
from .shared.decorators import retry_on_fail

BATCH_SIZE: Final[int] = 2000


def is_valid_product(
    product: LpkProduct,
    include_keywords_dict: dict[str, list[str] | None],
    exclude_keywords_dict: dict[str, list[str] | None],
) -> bool:
    product_fields = list(LpkProduct.model_fields.keys())
    for field_name in product_fields:
        include_keywords = include_keywords_dict[field_name]
        if include_keywords is not None:
            if all(
                [
                    keyword not in getattr(product, field_name)
                    for keyword in include_keywords
                ]
            ):
                return False

        exclude_keywords = exclude_keywords_dict[field_name]
        if exclude_keywords is not None:
            if any(
                [
                    keyword in getattr(product, field_name)
                    for keyword in exclude_keywords
                ]
            ):
                return False
    return True


@retry_on_fail()
def process():
    stater_info = Product.get_include_exclude_keywords_mapping_relax_time(
        config.SPREADSHEET_KEY, config.SHEET_NAME
    )
    start_index = Product.get_start_index()
    include_keywords_dict = stater_info.include_keywords
    exclude_keywords_dict = stater_info.exclude_keywords

    lpk_products: list[LpkProduct] = []
    for country_code in COUNTRY_CODES.keys():
        __lpk_products = lpk_api_client.get_all_products(
            country_code=country_code
        ).data.products
        logger.info(
            f"Total product for country code {country_code}: {len(__lpk_products)}"
        )
        lpk_products.extend(__lpk_products)

    logger.info(f"Total product: {len(lpk_products)}")

    sheet_products: list[Product] = []

    for product in lpk_products:
        if is_valid_product(product, include_keywords_dict, exclude_keywords_dict):
            sheet_products.append(
                Product(
                    sheet_id=config.SPREADSHEET_KEY,
                    sheet_name=config.SHEET_NAME,
                    index=len(sheet_products) + start_index,
                    **(product.model_dump(mode="json")),
                    Note=formated_datetime(datetime.now()),
                )
            )

    logger.info(f"Total valid product: {len(sheet_products)}")

    product_batchs = split_list(sheet_products, BATCH_SIZE)
    logger.info("Sheet updating")
    for i, batch in enumerate(product_batchs):
        logger.info(f"Updating batch: {i + 1}")
        Product.batch_update(
            sheet_id=config.SPREADSHEET_KEY,
            sheet_name=config.SHEET_NAME,
            list_object=batch,
        )

    Product.clear_sheet(
        sheet_id=config.SPREADSHEET_KEY,
        sheet_name=config.SHEET_NAME,
        start_row=len(sheet_products) + start_index,
    )
    sleep_for(stater_info.relax_time)
