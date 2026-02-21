
from balance.models import Cryptocurrency
from balance.utils.get_balances.bybit_balance import fetch_bybit_raw_balances
from balance.utils.get_balances.mexc_balance import fetch_mexc_raw_balances
from balance.utils.cryptocurrency import fetch_prices_for_symbols
from balance.utils.get_balances.wallet_balances import fetch_wallet_raw_balances
from balance.utils.optimizathion import timer
from balance.utils.utils_for_view import *

@timer
def normalize_balances(
    symbol_amounts: dict[str, Decimal],
    cryptos: dict[str, Cryptocurrency],
    prices: dict[str, Decimal],
):
    normalized = []

    for symbol, total in symbol_amounts.items():
        crypto = cryptos[symbol]
        price = prices.get(symbol, Decimal("0"))

        normalized.append({
            "crypto": crypto,
            "total": total,
            "available": total,
            "locked": Decimal("0"),
            "usd_value": total * price,
            "price_usd": price,
        })

    return normalized

def update_balance_for_connection(user_connection):
    """
    Главная функция обновления баланса
    """
    exchange_name = user_connection.exchange.name.lower()

    try:
        if exchange_name == "bybit":
            symbol_amounts = fetch_bybit_raw_balances(user_connection)
        # elif exchange_name == "binance":
        #     symbol_amounts = fetch_binance_raw_balances(user_connection)
        elif exchange_name == "mexc":
            symbol_amounts = fetch_mexc_raw_balances(user_connection)
        else:
            raise NotImplementedError(f"{exchange_name} пока не поддерживается")

    except Exception as e:
        raise Exception(f"Ошибка биржи {user_connection.exchange.name}: {str(e)}")

    # 2️⃣ Получаем цены с кеша/CMC
    prices = fetch_prices_for_symbols(list(symbol_amounts.keys()))

    # 3️⃣ Берём объекты Cryptocurrency из базы
    cryptos_qs = Cryptocurrency.objects.filter(symbol__in=symbol_amounts.keys())
    cryptos = {c.symbol: c for c in cryptos_qs}

    # 4️⃣ Нормализация для snapshot (подготовка структуры для сохранения)
    normalized = normalize_balances(
        symbol_amounts=symbol_amounts,
        cryptos=cryptos,
        prices=prices,
    )
    return normalized

def update_balance_of_wallet_for_connection(user_connection):
    """
    Главная функция обновления баланса
    """
    wallet_name = user_connection.nickname.lower()
    wallet_network = user_connection.network
    address = user_connection.address

    try:
        symbol_amounts = fetch_wallet_raw_balances(address, wallet_network)
    except Exception as e:
        raise Exception(f"Ошибка кошелька {wallet_name}: {str(e)}")

    # 2️⃣ Получаем цены с кеша/CMC
    prices = fetch_prices_for_symbols(list(symbol_amounts.keys()))

    # 3️⃣ Берём объекты Cryptocurrency из базы
    cryptos_qs = Cryptocurrency.objects.filter(symbol__in=symbol_amounts.keys())
    cryptos = {c.symbol: c for c in cryptos_qs}

    # 4️⃣ Нормализация для snapshot (подготовка структуры для сохранения)
    normalized = normalize_balances(
        symbol_amounts=symbol_amounts,
        cryptos=cryptos,
        prices=prices,
    )
    return normalized


