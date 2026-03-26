from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Market(BaseModel):
    id: str
    question: str
    slug: Optional[str] = None
    active: bool = False
    closed: bool = False
    enable_order_book: bool = Field(default=False, alias="enableOrderBook")
    end_date_iso: Optional[str] = Field(default=None, alias="endDateIso")
    liquidity_num: Optional[float] = Field(default=None, alias="liquidityNum")
    volume_num: Optional[float] = Field(default=None, alias="volumeNum")
    clob_token_ids: Optional[str] = Field(default=None, alias="clobTokenIds")
    category: Optional[str] = None

    model_config = {"populate_by_name": True}

    def yes_token_id(self) -> Optional[str]:
        if not self.clob_token_ids:
            return None
        raw = self.clob_token_ids.strip()
        if raw.startswith("[") and raw.endswith("]"):
            raw = raw[1:-1]
        parts = [p.strip().strip('"').strip("'") for p in raw.split(",") if p.strip()]
        return parts[0] if parts else None

    def days_to_end(self) -> Optional[float]:
        if not self.end_date_iso:
            return None
        try:
            dt = datetime.fromisoformat(self.end_date_iso.replace("Z", "+00:00"))
            now = datetime.now(dt.tzinfo)
            return (dt - now).total_seconds() / 86400
        except Exception:
            return None


class MarketQuote(BaseModel):
    token_id: str
    price: Optional[float] = None
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    midpoint: Optional[float] = None
    spread: Optional[float] = None


class RankedMarket(BaseModel):
    market: Market
    quote: MarketQuote
    score: float
    status: str
    reasons: list[str]