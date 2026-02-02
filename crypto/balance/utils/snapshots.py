from balance.models import BalanceSnapshot, PortfolioSnapshot
from django.utils import timezone


def snapshot_balance(user_connection, normalized_balances):

    for bal in normalized_balances:
        BalanceSnapshot.objects.create(
            user=user_connection.user,
            exchange_connection=user_connection,
            cryptocurrency=bal["crypto"],
            total_amount=bal["total"],
            available_amount=bal["available"],
            locked_amount=bal["locked"],
            price_at_snapshot=None,
            usd_value=bal["usd_value"],
            snapshot_time=timezone.now())

def snapshot_portfolio(user, total_value_usd):
    PortfolioSnapshot.objects.create(
        user= user,
        total_value_usd=total_value_usd,
        total_value_btc=None,
        total_invested_usd=None,
        top_coins=None,
        exchange_allocation=None,
        snapshot_time=timezone.now())



