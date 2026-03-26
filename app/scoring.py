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
        score -= 10
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
    else:
        score -= 20
        reasons.append("spread large")

    # Prix exploitable
    if quote.price is not None:
        if 0.15 <= quote.price <= 0.85:
            score += 12
            reasons.append("prix exploitable")
        elif 0.05 <= quote.price <= 0.95:
            score += 4
            reasons.append("prix acceptable")
        else:
            score -= 5
            reasons.append("prix extrême")

    # Bid / Ask réalistes
    if quote.best_bid is not None:
        if quote.best_bid >= 0.10:
            score += 12
            reasons.append("bid solide")
        elif quote.best_bid >= 0.03:
            score += 5
            reasons.append("bid présent")
        else:
            score -= 8
            reasons.append("bid faible")

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
    else:
        score -= 4
        reasons.append("liquidité faible")

    # Volume
    volume = market.volume_num or 0.0
    if volume >= 100000:
        score += 18
        reasons.append("volume élevé")
    elif volume >= 10000:
        score += 10
        reasons.append("volume correct")
    else:
        score -= 3
        reasons.append("volume faible")

    # Horizon
    days = market.days_to_end()
    if days is not None:
        if 0 <= days <= 14:
            score += 10
            reasons.append("horizon proche")
        elif 14 < days <= 60:
            score += 5
            reasons.append("horizon raisonnable")
        elif days > 365:
            score -= 8
            reasons.append("horizon trop lointain")

    # Bonus si orderbook dispo
    if market.enable_order_book:
        score += 5
        reasons.append("orderbook activé")

    score = round(score, 1)
    status = classify(score)

    return RankedMarket(
        market=market,
        quote=quote,
        score=score,
        status=status,
        reasons=reasons,
    )