from balance.models import BalanceSnapshot, PortfolioSnapshot
from django.utils import timezone
from balance.utils.utils_for_view import *
from balance.models import UserExchangeConnection, UserWalletConnection


def snapshot_balance(user, coin):
    from balance.models import Cryptocurrency

    # Получаем или создаем объект криптовалюты
    crypto, _ = Cryptocurrency.objects.get_or_create(symbol=coin['symbol'])

    BalanceSnapshot.objects.create(
        user=user,
        cryptocurrency=crypto,  # Нужен объект, а не строка
        total_amount=coin.get('total', 0) or 0,
        usd_value=coin.get('usd_value', 0) or 0,
        snapshot_time=timezone.now()
    )

def snapshot_portfolio(user, total_value_usd):

    if total_value_usd is None:
        total_value_usd = Decimal('0')

    PortfolioSnapshot.objects.create(
        user= user,
        total_value_usd=total_value_usd,
        total_value_btc=None,
        total_invested_usd=None,
        top_coins=[],
        snapshot_time=timezone.now())

def do_snapshots(user) -> Decimal:
    exchange_connections = UserExchangeConnection.objects.filter(user=user)
    wallet_connections = UserWalletConnection.objects.filter(user=user)

    # Создаем обработчики
    handlers = [ExchangeConnectionHandler(c) for c in exchange_connections]
    handlers += [WalletConnectionHandler(c) for c in wallet_connections]

    # Агрегируем баланс
    summary_by_connection, total_balance_usd, overall_coins = aggregate_balances(handlers)
    snapshot_portfolio(user, total_balance_usd)
    for coin in overall_coins:
        snapshot_balance(user, coin)





