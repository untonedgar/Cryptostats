from balance.models import Cryptocurrency, PriceHistory
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
import requests


def create_cryptocurrency_if_missing(symbol, name=None, cmc_id=None):
    crypto, _ = Cryptocurrency.objects.get_or_create(
        symbol=symbol,
        defaults={
            "name": name or symbol,
            "cmc_id": cmc_id,
        }
    )
    return crypto


def fetch_and_save_cmc_prices(symbols: list[str]):
    """
    Получает цены из CoinMarketCap и сохраняет их в PriceHistory
    """

    if not symbols:
        return

    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

    headers = {
        "X-CMC_PRO_API_KEY": "вставьте свой ключ",
        "Accept": "application/json",
    }

    params = {
        "symbol": ",".join(symbols),
        "convert": "USD",
    }

    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()

    data = response.json().get("data", {})
    now = timezone.now()

    for symbol, payload in data.items():
        quote = payload.get("quote", {}).get("USD")
        if not quote:
            continue

        crypto = create_cryptocurrency_if_missing(
            symbol=symbol,
            name=payload.get("name"),
            cmc_id=payload.get("id"),
        )

        PriceHistory.objects.create(
            cryptocurrency=crypto,
            price_usd=Decimal(str(quote["price"])),
            market_cap=Decimal(str(quote.get("market_cap", 0))),
            volume_24h=Decimal(str(quote.get("volume_24h", 0))),
            timestamp=now,
            source="coinmarketcap",
        )

def fetch_prices_for_symbols(symbols: list[str]) -> dict[str, Decimal]:
    """
    Возвращает актуальные цены для списка символов.
    Использует кеш, базу и при необходимости обновляет с CoinMarketCap.
    """
    prices = {}

    for crypto in Cryptocurrency.objects.filter(symbol__in=symbols):
        price = PriceHistory.objects.get_current_price(crypto.id)
        prices[crypto.symbol] = price

    return prices
