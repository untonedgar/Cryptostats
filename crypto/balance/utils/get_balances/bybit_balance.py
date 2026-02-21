from decimal import Decimal
from pybit.unified_trading import HTTP
from balance.utils.cryptocurrency import create_cryptocurrency_if_missing
from balance.utils.optimizathion import timer

@timer
def fetch_bybit_raw_balances(user_connection) -> dict[str, Decimal]:
    """
    Возвращает агрегированный баланс монет:
    {
        "BTC": Decimal("0.1"),
        "ETH": Decimal("2.3")
    }
    """

    session = HTTP(
        api_key=user_connection.api_key,
        api_secret=user_connection.api_secret,
    )

    result: dict[str, Decimal] = {}

    # --- UNIFIED ---
    unified = session.get_wallet_balance(accountType="UNIFIED")
    coins = unified.get("result", {}).get("list", [])[0].get("coin", [])

    for coin in coins:
        symbol = coin["coin"]
        amount = Decimal(coin.get("walletBalance", "0") or "0")
        result[symbol] = result.get(symbol, Decimal("0")) + amount

    # --- FUNDING ---
    fund = session.get_coins_balance(accountType="FUND")
    balances = fund.get("result", {}).get("balance", [])

    for coin in balances:
        symbol = coin["coin"]
        amount = Decimal(coin.get("walletBalance", "0") or "0")
        result[symbol] = result.get(symbol, Decimal("0")) + amount

    return {s: a for s, a in result.items() if a > 0}