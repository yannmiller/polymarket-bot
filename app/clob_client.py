import httpx

from .models import MarketQuote


class ClobClient:
    BASE_URL = "https://clob.polymarket.com"

    def __init__(self):
        self.client = httpx.Client(base_url=self.BASE_URL, timeout=20.0)

    def close(self):
        self.client.close()

    def get_quote(self, token_id: str) -> MarketQuote:
        best_bid = None
        best_ask = None
        price = None

        try:
            price_resp = self.client.get("/price", params={"token_id": token_id})
            if price_resp.status_code == 200:
                price_data = price_resp.json()
                if isinstance(price_data, dict) and price_data.get("price") is not None:
                    price = float(price_data["price"])
        except Exception:
            pass

        try:
            book_resp = self.client.get("/book", params={"token_id": token_id})
            if book_resp.status_code == 200:
                book = book_resp.json()
                bids = book.get("bids", [])
                asks = book.get("asks", [])

                if bids:
                    best_bid = float(bids[0]["price"])
                if asks:
                    best_ask = float(asks[0]["price"])
        except Exception:
            pass

        spread = None
        midpoint = None

        if best_bid is not None and best_ask is not None:
            spread = best_ask - best_bid
            midpoint = (best_bid + best_ask) / 2

        return MarketQuote(
            token_id=token_id,
            price=price,
            best_bid=best_bid,
            best_ask=best_ask,
            midpoint=midpoint,
            spread=spread,
        )