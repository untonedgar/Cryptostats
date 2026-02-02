from abc import ABC, abstractmethod
from typing import List, Dict
from balance.utils.utils import update_balance_of_wallet_for_connection, update_balance_for_connection


class ConnectionHandler(ABC):
    """
    Абстрактный обработчик подключений (биржа или кошелек)
    """
    @abstractmethod
    def get_normalized_balances(self) -> List[Dict]:
        """
        Должен возвращать список словарей:
        [
            {"crypto": crypto_obj, "total": Decimal(...), "usd_value": Decimal(...)}
        ]
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Имя подключения для отображения (биржа или nickname кошелька)
        """
        pass


class WalletConnectionHandler(ConnectionHandler):
    def __init__(self, user_wallet_connection):
        self.user_wallet_connection = user_wallet_connection

    def get_normalized_balances(self):
        return update_balance_of_wallet_for_connection(self.user_wallet_connection)

    def get_name(self):
        return self.user_wallet_connection.nickname or "Wallet"


class ExchangeConnectionHandler(ConnectionHandler):
    def __init__(self, user_connection):
        self.user_connection = user_connection

    def get_normalized_balances(self):
        return update_balance_for_connection(self.user_connection)

    def get_name(self):
        name = self.user_connection.exchange.name
        return name

from collections import defaultdict
from decimal import Decimal


def aggregate_balances(handlers: list):
    """Версия с процентами от общего баланса"""
    grouped = {}
    total_coins = defaultdict(lambda: {"total": Decimal("0"), "usd_value": Decimal("0")})
    total_balance_usd = Decimal("0")

    for handler in handlers:
        name = handler.get_name()

        try:
            normalized = handler.get_normalized_balances()
            significant_coins = [bal for bal in normalized if bal["usd_value"] > 10]

            if name not in grouped:
                grouped[name] = {
                    "connection_name": name,
                    "total_usd": Decimal("0"),
                    "significant_coins": [],
                    "error": None,
                }

            grouped[name]["total_usd"] += sum(b["usd_value"] for b in significant_coins)
            grouped[name]["significant_coins"].extend(significant_coins)

            for bal in normalized:
                symbol = bal["crypto"].symbol
                total_coins[symbol]["total"] += bal["total"]
                total_coins[symbol]["usd_value"] += bal["usd_value"]
                total_balance_usd += bal["usd_value"]

        except Exception as e:
            grouped[name] = {
                "connection_name": name,
                "total_usd": Decimal("0"),
                "significant_coins": [],
                "error": str(e),
            }

    for conn_data in grouped.values():
        if total_balance_usd > 0:
            conn_data["percent_of_total"] = (conn_data["total_usd"] / total_balance_usd * 100).quantize(Decimal("0.01"))
        else:
            conn_data["percent_of_total"] = Decimal("0")

        conn_data["significant_coins"].sort(key=lambda x: x["usd_value"], reverse=True)

        for coin in conn_data["significant_coins"]:
            if conn_data["total_usd"] > 0:
                coin["percent_of_connection"] = (coin["usd_value"] / conn_data["total_usd"] * 100).quantize(
                    Decimal("0.01"))
            else:
                coin["percent_of_connection"] = Decimal("0")

    overall_coins = []
    for symbol, data in total_coins.items():
        if data["usd_value"] > 10:
            percent_of_total = (data["usd_value"] / total_balance_usd * 100).quantize(
                Decimal("0.01")) if total_balance_usd > 0 else Decimal("0")

            overall_coins.append({
                "symbol": symbol,
                "total": data["total"],
                "usd_value": data["usd_value"],
                "percent_of_total": percent_of_total
            })

    overall_coins.sort(key=lambda x: x["usd_value"], reverse=True)

    sorted_grouped = sorted(grouped.values(), key=lambda x: x["total_usd"], reverse=True)

    return sorted_grouped, total_balance_usd, overall_coins