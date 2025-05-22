import time
from datetime import datetime

from app import logger

from .lpk.models import Product as LpkProduct


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
    products: list[LpkProduct],
) -> str:
    formated = ""
    for i, product in enumerate(products):
        formated += f"{i + 1}/ {product.code}, {product.category_code}, {product.name}, {product.provider_code}, {product.price}, {product.process_time}, {product.country_code}. {product.status} \n"

    return formated


def note_message(
    now: datetime,
    min_price_product: LpkProduct | None,
    other_products: list[LpkProduct],
) -> str:
    message = f"{formated_datetime(now)} "

    if min_price_product is None:
        message += "Không tìm thấy product hợp lệ\n"

    else:
        message += f"Cập nhật thành công: code: {min_price_product.code}, {min_price_product.country_code}, {min_price_product.process_time}\n"

    if len(other_products) > 0:
        message += f"Kết quả khác:\n{format_list_products(other_products)}"

    return message
