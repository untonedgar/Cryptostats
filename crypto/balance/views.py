from django.shortcuts import render, get_object_or_404, redirect
from balance.models import Exchange, UserExchangeConnection, UserWalletConnection, BlockchainNetwork
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from balance.utils.calculations import unrealized_pnl
from balance.utils.utils_for_view import *
from balance.tasks.tasks import process_users_balance_task
from asgiref.sync import sync_to_async

class ExchangeList (LoginRequiredMixin, ListView):
    model = Exchange
    context_object_name = 'Exchanges'
    template_name = 'list_of_exchanges.html'
    login_url = '/sign/login/'



@login_required(login_url='/sign/login/')
def add_exchange(request, exchange_id):
    exchange = get_object_or_404(
        Exchange,
        id=exchange_id,
        is_active=True
    )

    if request.method == 'POST':
        api_key = request.POST.get('api_key')
        api_secret = request.POST.get('api_secret')
        api_passphrase = request.POST.get('api_passphrase')
        nickname = request.POST.get('nickname')

        if not api_key or not api_secret:
            return render(request, 'add_exchange.html', {
                'exchange': exchange,
                'error': 'API Key и Secret обязательны'
            })

        UserExchangeConnection.objects.create(
            user=request.user,
            exchange=exchange,
            nickname=nickname,
            api_key=api_key,
            api_secret=api_secret,
            api_passphrase=api_passphrase,
            permissions=['read'],
            sync_status='syncing'
        )

        return redirect('main')  # ← поменяешь под себя

    return render(request, 'add_exchange.html', {
        'exchange': exchange
    })

@login_required(login_url='/sign/login/')
def add_wallet(request):
    networks = BlockchainNetwork.objects.all().order_by('name')

    # 🔹 существующие nickname пользователя
    existing_nicknames = (
        UserWalletConnection.objects
        .filter(user=request.user, nickname__isnull=False)
        .values_list('nickname', flat=True)
        .distinct()
    )

    if request.method == 'POST':
        network_id = request.POST.get('network')
        address = request.POST.get('address', '').strip()
        selected_nickname = request.POST.get('existing_nickname', '').strip()
        new_nickname = request.POST.get('new_nickname', '').strip()

        if not network_id:
            return render(request, 'add_wallet.html', {
                'networks': networks,
                'existing_nicknames': existing_nicknames,
                'error': 'Выберите сеть'
            })

        if not address:
            return render(request, 'add_wallet.html', {
                'networks': networks,
                'existing_nicknames': existing_nicknames,
                'error': 'Адрес кошелька обязателен'
            })

        network = BlockchainNetwork.objects.get(id=network_id)

        nickname = new_nickname or selected_nickname or None

        if UserWalletConnection.objects.filter(
            user=request.user,
            network=network,
            address=address
        ).exists():
            return render(request, 'add_wallet.html', {
                'networks': networks,
                'existing_nicknames': existing_nicknames,
                'error': 'Этот адрес уже добавлен'
            })

        UserWalletConnection.objects.create(
            user=request.user,
            network=network,
            address=address,
            nickname=nickname,
            sync_status='syncing'
        )

        return redirect('main')

    return render(request, 'add_wallet.html', {
        'networks': networks,
        'existing_nicknames': existing_nicknames
    })


class UserExchangesListView(LoginRequiredMixin, ListView):
    template_name = 'user_exchanges.html'
    context_object_name = 'connections'

    def get_queryset(self):
        user = self.request.user

        # Получаем все подключения бирж
        exchanges = list(UserExchangeConnection.objects.filter(
            user=user
        ).select_related('exchange'))

        # Получаем все кошельки и группируем их по nickname
        wallets = UserWalletConnection.objects.filter(
            user=user
        ).select_related('network')

        # Группируем кошельки по nickname
        wallet_groups = defaultdict(list)
        for wallet in wallets:
            nickname = wallet.nickname or 'Без имени'
            wallet_groups[nickname].append(wallet)

        # Создаем конечный список подключений
        connections_list = []

        # 1. Добавляем все биржи как отдельные объекты
        connections_list.extend(exchanges)

        # 2. Добавляем сгруппированные кошельки как словари
        for nickname, wallet_list in wallet_groups.items():
            connections_list.append({
                'type': 'wallet_group',
                'nickname': nickname,
                'wallets': wallet_list,
                'is_active': any(w.is_active for w in wallet_list),
                'last_sync_at': max(
                    (w.last_sync_at for w in wallet_list if w.last_sync_at),
                    default=None
                ),
                'total_count': len(wallet_list),
                'display_name': nickname,
            })

        return connections_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Статистика
        total_exchanges = UserExchangeConnection.objects.filter(user=user).count()
        total_wallets = UserWalletConnection.objects.filter(user=user).count()

        # Считаем сгруппированные кошельки
        wallet_groups_count = len(set(
            w.nickname or 'Без имени'
            for w in UserWalletConnection.objects.filter(user=user)
        ))

        # Последняя синхронизация
        last_exchange_sync = UserExchangeConnection.objects.filter(
            user=user, last_sync_at__isnull=False
        ).order_by('-last_sync_at').first()

        last_wallet_sync = UserWalletConnection.objects.filter(
            user=user, last_sync_at__isnull=False
        ).order_by('-last_sync_at').first()

        last_sync = None
        if last_exchange_sync and last_wallet_sync:
            last_sync = max(last_exchange_sync.last_sync_at, last_wallet_sync.last_sync_at)
        elif last_exchange_sync:
            last_sync = last_exchange_sync.last_sync_at
        elif last_wallet_sync:
            last_sync = last_wallet_sync.last_sync_at

        context.update({
            'total_exchanges': total_exchanges,
            'total_wallets': total_wallets,
            'wallet_groups': wallet_groups_count,
            'total_connections': total_exchanges + total_wallets,
            'last_sync': last_sync.strftime('%H:%M') if last_sync else '--:--',
        })

        return context


@login_required
def delete_exchange(request, pk):
    connection = get_object_or_404(UserExchangeConnection, pk=pk, user=request.user)
    if request.method == "POST":
        connection.delete()
    return redirect('my_exchanges')


@login_required
async def view_user_balances(request):
    exchange_connections = await sync_to_async(
        lambda: list(UserExchangeConnection.objects.filter(user=request.user))
    )()

    wallet_connections = await sync_to_async(
        lambda: list(UserWalletConnection.objects.filter(user=request.user))
    )()
    # Создаем обработчики
    handlers = [ExchangeConnectionHandler(c) for c in exchange_connections]
    handlers += [WalletConnectionHandler(c) for c in wallet_connections]

    # Агрегируем баланс
    summary_by_connection, total_balance_usd, overall_coins,  = await aggregate_balances(handlers)

    # PnL статисвстика
    statistic = await sync_to_async(unrealized_pnl)(request.user, total_balance_usd)

    context = {
        "summary_by_connection": summary_by_connection,
        "total_balance_usd": total_balance_usd,
        "overall_coins": overall_coins,
        "statistic": statistic,
    }
    return render(request, "user_balances.html", context)

@login_required
def delete_wallet(request, pk):
    connection = get_object_or_404(UserWalletConnection, pk=pk, user=request.user)
    if request.method == "POST":
        connection.delete()
    return redirect('my_exchanges')
