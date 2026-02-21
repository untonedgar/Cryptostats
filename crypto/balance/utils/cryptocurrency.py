from balance.models import Cryptocurrency, PriceHistory
from decimal import Decimal
from django.utils import timezone
from django.conf import settings
import requests
from balance.utils.optimizathion import timer

@timer
def create_cryptocurrency_if_missing(symbol, name=None, cmc_id=None):
    crypto, _ = Cryptocurrency.objects.get_or_create(
        symbol=symbol,
        defaults={
            "name": name or symbol,
            "cmc_id": cmc_id,
        }
    )
    return crypto

@timer
def fetch_and_save_cmc_prices_bulk(symbols: list[str]) -> dict[str, Decimal]:
    """
    Получает цены из CoinMarketCap для МНОГИХ символов
    Возвращает словарь {symbol: price}
    """
    if not symbols:
        return {}

    # Ограничиваем количество символов
    max_symbols = 30
    symbols_to_fetch = symbols[:max_symbols]

    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"

    headers = {
        "X-CMC_PRO_API_KEY": settings.X_CMC_PRO_API_KEY,
        "Accept": "application/json",
    }

    params = {
        "symbol": ",".join(symbols_to_fetch),
        "convert": "USD",
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

        data = response.json().get("data", {})
        now = timezone.now()

        prices = {}
        price_objects = []
        cryptos_to_update = []

        # Сначала получаем все существующие криптовалюты
        existing_cryptos = Cryptocurrency.objects.filter(symbol__in=symbols_to_fetch)
        crypto_by_symbol = {c.symbol: c for c in existing_cryptos}

        for symbol, payload in data.items():
            quote = payload.get("quote", {}).get("USD")
            if not quote:
                continue

            # Получаем или создаем криптовалюту
            crypto = crypto_by_symbol.get(symbol)
            if not crypto:
                crypto = create_cryptocurrency_if_missing(
                    symbol=symbol,
                    name=payload.get("name"),
                    cmc_id=payload.get("id"),
                )
                crypto_by_symbol[symbol] = crypto
            elif payload.get("name") and crypto.name != payload.get("name"):
                # Обновляем название если изменилось
                crypto.name = payload.get("name")
                cryptos_to_update.append(crypto)

            price = Decimal(str(quote["price"]))
            prices[symbol] = price

            price_objects.append(
                PriceHistory(
                    cryptocurrency=crypto,
                    price_usd=price,
                    market_cap=Decimal(str(quote.get("market_cap", 0))),
                    volume_24h=Decimal(str(quote.get("volume_24h", 0))),
                    timestamp=now,
                    source="coinmarketcap",
                )
            )

        # Bulk create всех цен
        if price_objects:
            PriceHistory.objects.bulk_create(price_objects)

        # Bulk update названий криптовалют
        if cryptos_to_update:
            Cryptocurrency.objects.bulk_update(cryptos_to_update, ['name'])

        # Заполняем нулями отсутствующие
        for symbol in symbols_to_fetch:
            if symbol not in prices:
                prices[symbol] = Decimal("0")

        return prices

    except Exception as e:
        print(f"❌ Ошибка при bulk-запросе к CMC: {e}")
        return {symbol: Decimal("0") for symbol in symbols_to_fetch}


# Для обратной совместимости
def fetch_and_save_cmc_prices(symbols: list[str]) -> dict[str, Decimal]:
    """Алиас для старого кода"""
    return fetch_and_save_cmc_prices_bulk(symbols)

@timer
def fetch_prices_for_symbols(symbols: list[str]) -> dict[str, Decimal]:
    """
    Упрощенная версия - использует новый bulk-метод
    """
    if not symbols:
        return {}

    # Получаем или создаем криптовалюты
    cryptos = []
    for symbol in symbols:
        if not symbol:
            continue

        symbol_upper = symbol.upper()
        try:
            crypto = Cryptocurrency.objects.get(symbol=symbol_upper)
        except Cryptocurrency.DoesNotExist:
            crypto = create_cryptocurrency_if_missing(symbol=symbol_upper, name=symbol_upper)

        cryptos.append(crypto)

    crypto_ids = [crypto.id for crypto in cryptos]
    prices_by_id = PriceHistory.objects.get_current_prices_bulk(crypto_ids)

    # Конвертируем в {symbol: price}
    result = {}
    for crypto in cryptos:
        result[crypto.symbol] = prices_by_id.get(crypto.id, Decimal("0"))

    return result
