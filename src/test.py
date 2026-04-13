from app.lapakgaming.models import Product as LapakgamingProduct

from app.processes import _fetch_products_for_country
from app.lapakgaming.consts import COUNTRY_CODES


async def main():
    # Step 1: Fetch all lapakgaming products in parallel (one task per country code)
    print("process: fetching lapakgaming products for all country codes in parallel")
    country_codes = list(COUNTRY_CODES.keys())
    results = await asyncio.gather(
        *[_fetch_products_for_country(cc) for cc in country_codes],
        return_exceptions=True,
    )

    all_products: list[LapakgamingProduct] = []
    for cc, result in zip(country_codes, results):
        if isinstance(result, BaseException):
            print(f"process: country_code={cc} fetch failed: {result}")
        else:
            all_products.extend(result)

    print(f"process: total products fetched = {len(all_products)}")

    available_products = [p for p in all_products if p.status == "available"]

    print(f"process: available products count = {len(available_products)}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
