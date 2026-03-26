from typing import List

import httpx

from .models import Market


class GammaClient:
    BASE_URL = "https://gamma-api.polymarket.com"

    def __init__(self):
        self.client = httpx.Client(base_url=self.BASE_URL, timeout=20.0)

    def close(self):
        self.client.close()

    def get_active_markets(self, limit: int = 100) -> List[Market]:
        resp = self.client.get(
            "/markets",
            params={"active": "true", "closed": "false", "limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()

        markets = []
        for item in data:
            try:
                markets.append(Market.model_validate(item))
            except Exception:
                continue

        return markets