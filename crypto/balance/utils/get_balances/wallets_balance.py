import requests
from decimal import Decimal

COVALENT_API_KEY = "вставить ключ"

# Минимальная стоимость токена в USD, ниже — считаем мусором
MIN_USD_VALUE = Decimal("1")


def fetch_wallet_raw_balances(address: str, network) -> dict[str, Decimal]:
    """
    ОДИН запрос → ВСЕ токены кошелька в конкретной сети

    Возвращает:
    {
        "ETH": Decimal("1.23"),
        "USDT": Decimal("500"),
    }
    """

    url = f"https://api.covalenthq.com/v1/{network.chain_id}/address/{address}/balances_v2/"

    params = {
        "key": COVALENT_API_KEY,
        "nft": "false",
        "no-nft-fetch": "true",
        "quote-currency": "USD",
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()

    data = response.json()
    items = data.get("data", {}).get("items", [])

    tokens: dict[str, Decimal] = {}

    for item in items:
        symbol = item.get("contract_ticker_symbol")
        balance_raw = item.get("balance")
        decimals = item.get("contract_decimals")
        quote = item.get("quote")  # USD value from Covalent

        # --- ЖЁСТКАЯ ФИЛЬТРАЦИЯ СПАМА ---
        if not symbol:
            continue
        if not balance_raw or not decimals:
            continue
        if not quote or Decimal(str(quote)) < MIN_USD_VALUE:
            continue
        if symbol.upper() in {"SPAM", "DUST"}:
            continue

        amount = Decimal(balance_raw) / (Decimal(10) ** decimals)

        if amount <= 0:
            continue

        tokens[symbol.upper()] = amount.quantize(Decimal("0.00000001"))

    return tokens

