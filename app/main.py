import os
import time
from typing import Dict

import httpx
import typer
from rich.console import Console
from rich.table import Table

from .clob_client import ClobClient
from .gamma_client import GammaClient
from .scoring import score_market

app = typer.Typer()
console = Console()


def send_telegram_message(text: str) -> bool:
    bot_token = os.getenv("BOT_TOKEN")
    chat_id = os.getenv("CHAT_ID")

    if not bot_token or not chat_id:
        console.print("[red]BOT_TOKEN ou CHAT_ID manquant.[/red]")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    try:
        response = httpx.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout=20.0,
        )
        response.raise_for_status()
        return True
    except Exception as exc:
        console.print(f"[red]Erreur Telegram:[/red] {exc}")
        return False


def market_url(market) -> str:
    if market.slug:
        return f"https://polymarket.com/event/{market.slug}"
    return "https://polymarket.com"


def is_interesting(item) -> bool:
    q = item.quote
    m = item.market

    if item.score < 35:
        return False

    if q.best_bid is None or q.best_ask is None:
        return False

    if q.best_bid <= 0.01 and q.best_ask >= 0.99:
        return False

    if q.spread is not None and q.spread > 0.20:
        return False

    if (m.liquidity_num or 0) <= 0 and (m.volume_num or 0) <= 0:
        return False

    return True


def fetch_ranked_markets(limit: int = 300):
    gamma = GammaClient()
    clob = ClobClient()

    try:
        markets = gamma.get_active_markets(limit)
        results = []

        for market in markets:
            if not market.enable_order_book:
                continue

            token_id = market.yes_token_id()
            if not token_id:
                continue

            quote = clob.get_quote(token_id)
            ranked = score_market(market, quote)
            results.append(ranked)

        results.sort(key=lambda x: x.score, reverse=True)
        return results
    finally:
        gamma.close()
        clob.close()


@app.command()
def scan(limit: int = 300, top: int = 20):
    console.print("[bold]Scan marchés Polymarket...[/bold]")
    results = fetch_ranked_markets(limit=limit)
    filtered = [item for item in results if is_interesting(item)]

    if not filtered:
        console.print("[yellow]Aucun marché vraiment intéressant trouvé.[/yellow]")
        return

    table = Table(title="Analyse marchés Polymarket")
    table.add_column("Score", justify="right")
    table.add_column("Statut")
    table.add_column("Question")
    table.add_column("Bid", justify="right")
    table.add_column("Ask", justify="right")
    table.add_column("Spread", justify="right")
    table.add_column("Liquidité", justify="right")
    table.add_column("Volume", justify="right")

    for item in filtered[:top]:
        table.add_row(
            f"{item.score:.1f}",
            item.status,
            item.market.question[:60],
            "-" if item.quote.best_bid is None else f"{item.quote.best_bid:.3f}",
            "-" if item.quote.best_ask is None else f"{item.quote.best_ask:.3f}",
            "-" if item.quote.spread is None else f"{item.quote.spread:.3f}",
            "-" if item.market.liquidity_num is None else f"{item.market.liquidity_num:,.0f}",
            "-" if item.market.volume_num is None else f"{item.market.volume_num:,.0f}",
        )

    console.print(table)


@app.command()
def watch(
    limit: int = 300,
    top: int = 15,
    interval: int = 60,
    alert_score: float = 50.0,
    cooldown_minutes: int = 180,
):
    console.print("[bold green]Mode surveillance lancé[/bold green]")
    console.print(f"Scan toutes les {interval} secondes")
    console.print(f"Alerte à partir du score {alert_score}")
    console.print(f"Cooldown alerte: {cooldown_minutes} min")
    console.print("Ctrl+C pour arrêter\n")

    send_telegram_message(
        f"✅ Bot Polymarket lancé\n"
        f"interval={interval}s\n"
        f"alert_score={alert_score}\n"
        f"cooldown={cooldown_minutes}min"
    )

    last_alert_ts: Dict[str, float] = {}
    first_scan = True

    try:
        while True:
            results = fetch_ranked_markets(limit=limit)
            filtered = [item for item in results if is_interesting(item)]
            top_results = filtered[:top]

            console.rule("[bold blue]Nouveau scan[/bold blue]")

            table = Table(title="Top opportunités")
            table.add_column("Score", justify="right")
            table.add_column("Statut")
            table.add_column("Question")
            table.add_column("Bid", justify="right")
            table.add_column("Ask", justify="right")
            table.add_column("Spread", justify="right")

            now = time.time()

            for item in top_results:
                table.add_row(
                    f"{item.score:.1f}",
                    item.status,
                    item.market.question[:60],
                    "-" if item.quote.best_bid is None else f"{item.quote.best_bid:.3f}",
                    "-" if item.quote.best_ask is None else f"{item.quote.best_ask:.3f}",
                    "-" if item.quote.spread is None else f"{item.quote.spread:.3f}",
                )

                previous_alert_ts = last_alert_ts.get(item.market.id, 0)
                cooldown_ok = (now - previous_alert_ts) >= cooldown_minutes * 60
                over_threshold = item.score >= alert_score
                should_alert = over_threshold and (first_scan or cooldown_ok)

                if should_alert:
                    msg = (
                        f"🚨 ALERTE POLYMARKET\n\n"
                        f"Question: {item.market.question}\n"
                        f"Score: {item.score:.1f}\n"
                        f"Statut: {item.status}\n"
                        f"Bid: {item.quote.best_bid}\n"
                        f"Ask: {item.quote.best_ask}\n"
                        f"Spread: {item.quote.spread}\n"
                        f"Liquidité: {item.market.liquidity_num}\n"
                        f"Volume: {item.market.volume_num}\n"
                        f"Raisons: {', '.join(item.reasons[:5])}\n"
                        f"Lien: {market_url(item.market)}"
                    )
                    console.print(f"[bold red]{msg}[/bold red]")
                    send_telegram_message(msg)
                    last_alert_ts[item.market.id] = now

            first_scan = False

            if top_results:
                console.print(table)
            else:
                console.print("[yellow]Aucune opportunité intéressante sur ce scan.[/yellow]")

            time.sleep(interval)

    except KeyboardInterrupt:
        console.print("\n[yellow]Surveillance arrêtée.[/yellow]")


if __name__ == "__main__":
    app()