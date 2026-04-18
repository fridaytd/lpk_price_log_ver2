import re
import time
from datetime import datetime

from app import logger

from .lapakgaming.models import Product as LapakgamingProduct


def sleep_for(delay: float) -> None:
    logger.info(f"Sleep for {delay} seconds")
    time.sleep(delay)


def formated_datetime(
    now: datetime,
) -> str:
    formatted_date = now.strftime("%d/%m/%Y %H:%M:%S")
    return formatted_date


def split_list(lst: list, chunk_size: int) -> list[list]:
    """
    Split a list into smaller chunks of specified size

    Args:
        lst (list): Input list to split
        chunk_size (int): Size of each chunk

    Returns:
        list: List containing sublists of specified chunk size
    """
    return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]


def format_list_products(
    products: list[LapakgamingProduct],
) -> str:
    formated = ""
    for i, product in enumerate(products):
        formated += f"{i + 1}/ {product.code}, {product.category_code}, {product.name}, {product.provider_code}, {product.price}, {product.process_time}, {product.country_code}. {product.status} \n"

    return formated


def derive_codes_for_row(
    col_a_prefix: str | None,
    col_f_country_filter: str | None,
    listing_codes: list[str | None],
    listing_country_codes: list[str | None],
) -> list[str]:
    """Derive product codes for a logging row by scanning listing sheet data.

    Args:
        col_a_prefix: The game prefix from logging col A (e.g. "GAME")
        col_f_country_filter: Optional country keyword from logging col F (e.g. "ID")
        listing_codes: All product codes from listing sheet col B
        listing_country_codes: Corresponding country codes from listing sheet col H (same order/length)

    Returns:
        List of matched product code strings (empty list if no match or col_a_prefix is falsy).
    """
    if not col_a_prefix:
        return []

    prefix_pattern = re.compile(rf"(?i)\b({re.escape(col_a_prefix)}-)")
    country_pattern = (
        re.compile(rf"(?i)\b({re.escape(col_f_country_filter)})")
        if col_f_country_filter
        else None
    )

    matched: list[str] = []
    for code, country in zip(listing_codes, listing_country_codes):
        if not code:
            continue
        if not prefix_pattern.search(code):
            continue
        if country_pattern is not None:
            if not country or not country_pattern.search(country):
                continue
        matched.append(code)

    return matched


def note_message(
    now: datetime,
    min_price_product: LapakgamingProduct | None,
    other_products: list[LapakgamingProduct],
) -> str:
    message = f"{formated_datetime(now)} "

    if min_price_product is None:
        message += "Không tìm thấy product hợp lệ\n"

    else:
        message += f"Cập nhật thành công: code: {min_price_product.code}; country_code = {min_price_product.country_code}, process_time = {min_price_product.process_time}\n"

    if len(other_products) > 0:
        message += f"Kết quả khác:\n{format_list_products(other_products)}"

    return message
