import time
import hmac
import hashlib
from urllib.parse import urlencode
from decimal import Decimal
import requests


def fetch_mexc_raw_balances(user_connection) -> dict[str, Decimal]:
    """Возвращает баланс монет на MEXC в виде { 'BTC': Decimal('0.12'), ... }"""

    api_key = user_connection.api_key
    api_secret = user_connection.api_secret

    # 1) Формируем параметры и подпись
    timestamp = int(time.time() * 1000)
    params = {
        "timestamp": timestamp,
        "recvWindow": 5000,
    }
    query_string = urlencode(params)

    signature = hmac.new(
        api_secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    params["signature"] = signature

    headers = {
        "X-MEXC-APIKEY": api_key,
        "Content-Type": "application/json",
    }

    url = "https://api.mexc.com/api/v3/account"

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        result: dict[str, Decimal] = {}

        # 2) Извлекаем balances
        balances = data.get("balances", [])
        for item in balances:
            symbol = item.get("asset")
            free = Decimal(item.get("free", "0") or "0")
            locked = Decimal(item.get("locked", "0") or "0")
            total = free + locked

            if total > 0:
                result[symbol] = result.get(symbol, Decimal("0")) + total

        return result

    except Exception as e:
        # Пробрасываем ошибку так, чтобы view смог её обработать
        raise Exception(f"MEXC API error: {str(e)}")