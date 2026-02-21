from celery import shared_task
import time
from balance.utils.snapshots import do_snapshots


@shared_task(bind=True, max_retries=3)
def process_user_snapshot(self, user_id: int) -> dict:
    """
    Создает снапшоты для конкретного пользователя
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)
        print(f"📸 [Task {self.request.id}] Создание снапшотов для {user.email}")

        start_time = time.perf_counter()

        # Создаем снапшоты
        total_usd = do_snapshots(user)

        elapsed = time.perf_counter() - start_time

        return {
            'status': 'success',
            'user_id': user_id,
            'total_usd': float(total_usd),
            'elapsed': elapsed,
            'task_id': self.request.id
        }

    except User.DoesNotExist:
        print(f"❌ Пользователь {user_id} не найден")
        return {'status': 'error', 'error': 'User not found'}

    except Exception as e:
        print(f"❌ Ошибка для пользователя {user_id}: {e}")

        if self.request.retries < self.max_retries:
            self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        else:
            return {
                'status': 'failed',
                'user_id': user_id,
                'error': str(e)
            }


@shared_task
def process_all_users_snapshots(snapshot_type: str = 'daily'):
    """
    Создает снапшоты для ВСЕХ пользователей
    Запускается по расписанию
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    print(f"\n{'=' * 60}")
    print(f"📸 ЗАПУСК {snapshot_type.upper()} СНАПШОТОВ ДЛЯ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ")
    print('=' * 60)

    start_time = time.perf_counter()

    # Получаем всех активных пользователей
    users = User.objects.filter(is_active=True)
    print(f"📊 Найдено {users.count()} активных пользователей")

    # Запускаем задачи для всех пользователей
    tasks = []
    for user in users:
        task = process_user_snapshot.delay(user.id)
        tasks.append({
            'user_id': user.id,
            'task_id': task.id
        })

    elapsed = time.perf_counter() - start_time

    return {
        'status': 'started',
        'snapshot_type': snapshot_type,
        'users_count': users.count(),
        'tasks': tasks,
        'elapsed': elapsed,
    }


@shared_task(bind=True, max_retries=3)
def process_users_balance_task(self, user_id):
    """Асинхронный расчет балансов пользователя"""
    try:
        from django.contrib.auth import get_user_model
        from celery import shared_task
        import time
        from balance.utils.snapshots import do_snapshots
        from balance.utils.calculations import unrealized_pnl
        from balance.utils.utils_for_view import WalletConnectionHandler, ExchangeConnectionHandler, aggregate_balances
        from django.core.cache import cache
        from django.shortcuts import render, get_object_or_404, redirect
        from balance.models import Exchange, UserExchangeConnection, UserWalletConnection, BlockchainNetwork, User
        from django.views.generic import ListView
        from django.contrib.auth.mixins import LoginRequiredMixin
        from django.contrib.auth.decorators import login_required

        User = get_user_model()
        user = User.objects.get(id=user_id)

        print(f"🔄 [Task {self.request.id}] Расчет балансов для {user.email}")

        # Получаем подключения
        exchange_connections = UserExchangeConnection.objects.filter(user=user)
        wallet_connections = UserWalletConnection.objects.filter(user=user)

        # Создаем обработчики
        handlers = [ExchangeConnectionHandler(c) for c in exchange_connections]
        handlers += [WalletConnectionHandler(c) for c in wallet_connections]

        # Агрегируем баланс
        summary_by_connection, total_balance_usd, overall_coins = aggregate_balances(handlers)
        statistic = unrealized_pnl(user, total_balance_usd)

        # Возвращаем словарь (Celery сам сериализует)
        return {
            'summary_by_connection': summary_by_connection,
            'total_balance_usd': float(total_balance_usd),
            'overall_coins': overall_coins,
            'statistic': statistic,
        }

    except Exception as e:
        print(f"❌ Ошибка в задаче: {e}")
        # Пробрасываем исключение, чтобы Celery знал об ошибке
        raise self.retry(exc=e, countdown=60)