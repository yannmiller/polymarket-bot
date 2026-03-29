from .models import Market, MarketQuote, RankedMarket


def classify(score: float) -> str:
    if score < 20:
        return "MORT"
    if score < 40:
        return "MOYEN"
    if score < 60:
        return "SURVEILLER"
    return "OPPORTUNITÉ"


def score_market(market: Market, quote: MarketQuote) -> RankedMarket:
    score = 0.0
    reasons = []

    # Spread
    if quote.spread is None:
        score -= 15
        reasons.append("spread inconnu")
    elif quote.spread <= 0.02:
        score += 35
        reasons.append("spread très serré")
    elif quote.spread <= 0.05:
        score += 22
        reasons.append("spread correct")
    elif quote.spread <= 0.10:
        score += 10
        reasons.append("spread moyen")
    elif quote.spread <= 0.20:
        score -= 5
        reasons.append("spread large")
    else:
        score -= 20
        reasons.append("spread énorme")

    # Prix
    if quote.price is not None:
        if 0.15 <= quote.price <= 0.85:
            score += 12
            reasons.append("prix exploitable")
        elif 0.05 <= quote.price <= 0.95:
            score += 4
            reasons.append("prix acceptable")
        else:
            score -= 6
            reasons.append("prix extrême")
    else:
        score -= 4
        reasons.append("prix absent")

    # Bid
    if quote.best_bid is not None:
        if quote.best_bid >= 0.10:
            score += 12
            reasons.append("bid solide")
        elif quote.best_bid >= 0.03:
            score += 5
            reasons.append("bid présent")
        elif quote.best_bid > 0:
            score -= 6
            reasons.append("bid trop faible")
        else:
            score -= 10
            reasons.append("pas de bid")
    else:
        score -= 10
        reasons.append("bid absent")

    # Ask
    if quote.best_ask is not None:
        if quote.best_ask <= 0.90:
            score += 12
            reasons.append("ask réaliste")
        elif quote.best_ask <= 0.97:
            score += 4
            reasons.append("ask haute")
        else:
            score -= 8
            reasons.append("ask extrême")
    else:
        score -= 10
        reasons.append("ask absente")

    # Liquidité
    liquidity = market.liquidity_num or 0.0
    if liquidity >= 100000:
        score += 24
        reasons.append("forte liquidité")
    elif liquidity >= 25000:
        score += 16
        reasons.append("bonne liquidité")
    elif liquidity >= 5000:
        score += 8
        reasons.append("liquidité correcte")
    elif liquidity > 0:
        score += 2
        reasons.append("liquidité faible")
    else:
        score -= 6
        reasons.append("pas de liquidité")

    # Volume
    volume = market.volume_num or 0.0
    if volume >= 100000:
        score += 18
        reasons.append("volume élevé")
    elif volume >= 10000:
        score += 10
        reasons.append("volume correct")
    elif volume > 0:
        score += 2
        reasons.append("volume faible")
    else:
        score -= 6
        reasons.append("pas de volume")

    # Horizon
    days = market.days_to_end()
    if days is not None:
        if 0 <= days <= 14:
            score += 10
            reasons.append("horizon proche")
        elif 14 < days <= 60:
            score += 5
            reasons.append("horizon raisonnable")
        elif 60 < days <= 180:
            score += 1
            reasons.append("horizon long")
        elif days > 365:
            score -= 10
            reasons.append("horizon trop lointain")

    # Bonus/malus structurels
    if market.enable_order_book:
        score += 5
        reasons.append("orderbook activé")

    # Malus si le carnet ressemble à un marché mort
    if (
        quote.best_bid is not None
        and quote.best_ask is not None
        and quote.best_bid <= 0.01
        and quote.best_ask >= 0.99
    ):
        score -= 20
        reasons.append("carnet quasi mort")

    score = round(score, 1)
    status = classify(score)

    return RankedMarket(
        market=market,
        quote=quote,
        score=score,
        status=status,
        reasons=reasons,
    )