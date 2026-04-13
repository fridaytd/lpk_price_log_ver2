from typing import Final

import httpx

from .. import config
from . import logger
from .models import ProductResponse, Response
from ..shared.retry_policies import LAPAK_API_RETRY

LAPAKGAMING_BASE_URL: Final[str] = "https://www.lapakgaming.com"


class LapakgamingAPIClient:
    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=30.0)
        self.base_url = LAPAKGAMING_BASE_URL

    @LAPAK_API_RETRY
    async def get_all_products(self, country_code: str = "id") -> Response[ProductResponse]:
        logger.info(f"LapakgamingAPIClient.get_all_products: country_code={country_code}")

        headers = {
            "Authorization": f"Bearer {config.LAPAK_API_KEY}",
        }

        res = await self.client.get(
            f"{self.base_url}/api/all-products?country_code={country_code}",
            headers=headers,
        )

        try:
            res.raise_for_status()
        except httpx.HTTPStatusError:
            logger.error(f"LapakgamingAPIClient: HTTP {res.status_code} error on {res.url.path}")
            logger.debug(f"LapakgamingAPIClient: response body length={len(res.text)}")
            raise

        return Response[ProductResponse].model_validate(res.json())


lapakgaming_api_client = LapakgamingAPIClient()
