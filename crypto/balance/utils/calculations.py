from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from balance.models import PortfolioSnapshot

def unrealized_pnl(user, total_balance_usd: Decimal):
    """
    Возвращает словарь с PnL за день и за месяц:
    {
        "daily_usd": Decimal | None,
        "daily_percent": Decimal | None,
        "monthly_usd": Decimal | None,
        "monthly_percent": Decimal | None,
    }
    """

    now = timezone.now()

    # 🔹 начало сегодняшнего дня
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 🔹 начало дня месяц назад (30 дней)
    start_of_month_ago = start_of_today - timedelta(days=30)
    end_of_month_ago = start_of_month_ago + timedelta(days=1)

    result = {
        "daily_usd": None,
        "daily_percent": None,
        "monthly_usd": None,
        "monthly_percent": None,
    }

    daily_snapshot = (
        PortfolioSnapshot.objects
        .filter(user=user, snapshot_time__gte=start_of_today)
        .order_by("snapshot_time")
        .first()
    )

    if daily_snapshot and daily_snapshot.total_value_usd > 0:
        daily_usd = total_balance_usd - daily_snapshot.total_value_usd
        daily_percent = (daily_usd / daily_snapshot.total_value_usd) * Decimal("100")
        result["daily_usd"] = daily_usd.quantize(Decimal("0.01"))
        result["daily_percent"] = daily_percent.quantize(Decimal("0.01"))

    monthly_snapshot = (
        PortfolioSnapshot.objects
        .filter(user=user,
                snapshot_time__gte=start_of_month_ago,
                snapshot_time__lt=end_of_month_ago)
        .order_by("snapshot_time")
        .first()
    )

    if monthly_snapshot and monthly_snapshot.total_value_usd > 0:
        monthly_usd = total_balance_usd - monthly_snapshot.total_value_usd
        monthly_percent = (monthly_usd / monthly_snapshot.total_value_usd) * Decimal("100")
        result["monthly_usd"] = monthly_usd.quantize(Decimal("0.01"))
        result["monthly_percent"] = monthly_percent.quantize(Decimal("0.01"))

    return result