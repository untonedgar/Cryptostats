from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.cache import cache
from django.utils import timezone
from django_prometheus.models import ExportModelOperationsMixin
import uuid
from decimal import Decimal
import datetime
import time
class User(ExportModelOperationsMixin('user'), AbstractUser):
    """Пользователь с расширенными полями для крипто-трекинга"""
    timezone = models.CharField(max_length=50, default='UTC')
    default_currency = models.CharField(max_length=10, default='USD')
    telegram_id = models.CharField(max_length=100, blank=True, null=True)
    settings = models.JSONField(default=dict, blank=True)  # {notifications: true, theme: 'dark'}

    groups = models.ManyToManyField(
        Group,
        related_name='balance_user_set',  # Добавляем custom related_name
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='balance_user_permissions',  # Добавляем custom related_name
        blank=True
    )
    class Meta:
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
        ]
        verbose_name_plural = "Пользователи"


class Cryptocurrency(models.Model):
    """Справочник криптовалют (нормализация)"""
    symbol = models.CharField(max_length=50, unique=True)  # BTC, ETH
    name = models.CharField(max_length=100)  # Bitcoin
    cmc_id = models.IntegerField(blank=True, null=True)  # CoinMarketCap ID
    logo_url = models.URLField(blank=True, null=True)
    is_stablecoin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    decimals = models.IntegerField(default=8)  # Точность (для отображения)

    class Meta:
        verbose_name_plural = "Криптовалюты"
        indexes = [
            models.Index(fields=['symbol']),
            models.Index(fields=['is_active', 'symbol']),
        ]

    def __str__(self):
        return f"{self.symbol} ({self.name})"


class Exchange(models.Model):
    """Справочник бирж"""
    EXCHANGE_CHOICES = [
        ('binance', 'Binance'),
        ('bybit', 'Bybit'),
        ('kucoin', 'KuCoin'),
        ('okx', 'OKX'),
        ('coinbase', 'Coinbase'),
        ('huobi', 'Huobi'),
        ('gate', 'Gate.io'),
        ('mexc', 'MEXC'),
        ('bitget', 'Bitget'),
    ]

    name = models.CharField(max_length=50, choices=EXCHANGE_CHOICES, unique=True)
    display_name = models.CharField(max_length=100)
    api_docs_url = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    supports = models.JSONField(default=list)  # ['spot', 'futures', 'margin']

    class Meta:
        verbose_name_plural = "Биржи"
        indexes = [
            models.Index(fields=['name', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name}"


class UserExchangeConnection(models.Model):
    """Подключение пользователя к бирже (API ключи)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exchange_connections')
    exchange = models.ForeignKey(Exchange, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=100, blank=True, null=True)  # Пользовательское имя

    # Зашифрованные поля (используйте django-cryptography на проде)
    api_key = models.CharField(max_length=500)
    api_secret = models.CharField(max_length=500)
    api_passphrase = models.CharField(max_length=500, blank=True, null=True)  # Для OKX, Coinbase

    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(blank=True, null=True)
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('syncing', 'Syncing'),
        ],
        blank=True, null=True
    )
    error_message = models.TextField(blank=True, null=True)
    permissions = models.JSONField(default=list)  # ['read', 'trade', 'withdraw']

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Подключения"
        unique_together = ['user', 'exchange', 'nickname']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['last_sync_at']),
        ]

CACHE_TIMEOUT = 300  # 5 минут
PRICE_MAX_AGE = 300  # 5 минут

class BlockchainNetwork(models.Model):
    """Простая таблица сетей"""
    name = models.CharField(max_length=100)  # Ethereum
    slug = models.CharField(max_length=50)  # eth
    chain_id = models.IntegerField()  # 1
    native_coin = models.CharField(max_length=20)  # ETH

    class Meta:
        verbose_name_plural = "Сети"
        db_table = 'blockchain_networks'

    def __str__(self):
        return f"{self.name}"

class UserWalletConnection(models.Model):
    """Подключение пользователя к кошельку или сети (адрес)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wallet_connections')

    # Сеть блокчейна, например Ethereum, BSC, Solana
    network = models.ForeignKey(BlockchainNetwork, on_delete=models.CASCADE)

    # Адрес пользователя в сети
    address = models.CharField(max_length=100)

    nickname = models.CharField(max_length=100, blank=True, null=True)  # Пользовательское имя

    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(blank=True, null=True)
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('success', 'Success'),
            ('failed', 'Failed'),
            ('syncing', 'Syncing'),
        ],
        blank=True, null=True
    )
    error_message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Подключения кошельков"
        unique_together = ['user', 'network', 'address']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['last_sync_at']),
        ]

    def __str__(self):
        return f"{self.network} — {self.address[:6]}…"


class PriceHistoryManager(models.Manager):
    """Менеджер для работы с историей цен с bulk-операциями"""

    def get_current_prices_bulk(self, cryptocurrency_ids: list[int]) -> dict[int, Decimal]:
        if not cryptocurrency_ids:
            return {}

        start_time = time.perf_counter()
        print(f"📊 Запрашиваем цены для {len(cryptocurrency_ids)} криптовалют")

        # 1. ВСЕГДА получаем последние цены из базы для ВСЕХ криптовалют
        latest_prices_qs = self.filter(
            cryptocurrency_id__in=cryptocurrency_ids
        ).order_by('cryptocurrency_id', '-timestamp').distinct('cryptocurrency_id')

        latest_by_crypto = {price.cryptocurrency_id: price for price in latest_prices_qs}

        # 2. Разделяем на свежие и устаревшие
        fresh_prices = {}
        outdated_ids = []
        now = timezone.now()

        for crypto_id in cryptocurrency_ids:
            latest_price = latest_by_crypto.get(crypto_id)

            if latest_price:
                price_age = (now - latest_price.timestamp).total_seconds()
                if price_age <= PRICE_MAX_AGE:
                    # Цена свежая - обновляем кэш и результат
                    cache.set(f'price_{crypto_id}_current', str(latest_price.price_usd), CACHE_TIMEOUT)
                    fresh_prices[crypto_id] = latest_price.price_usd
                else:
                    outdated_ids.append(crypto_id)
            else:
                outdated_ids.append(crypto_id)

        print(f"✅ Из базы (свежие): {len(fresh_prices)}, нужно у CMC: {len(outdated_ids)}")

        # 3. Запрашиваем устаревшие у CMC
        result = fresh_prices.copy()

        if outdated_ids:
            outdated_cryptos = Cryptocurrency.objects.filter(id__in=outdated_ids)
            outdated_symbols = [crypto.symbol for crypto in outdated_cryptos]

            if outdated_symbols:
                print(f"🌐 Запрашиваем у CMC {len(outdated_symbols)} символов")

                from balance.utils.cryptocurrency import fetch_and_save_cmc_prices_bulk
                cmc_prices = fetch_and_save_cmc_prices_bulk(outdated_symbols)

                for crypto in outdated_cryptos:
                    price = cmc_prices.get(crypto.symbol)
                    if price is not None:
                        cache.set(f'price_{crypto.id}_current', str(price), CACHE_TIMEOUT)
                        result[crypto.id] = price
                    else:
                        result[crypto.id] = Decimal("0")

        elapsed = time.perf_counter() - start_time
        print(f"⏱️ Получено {len(result)} цен за {elapsed:.2f} сек")

        return result



class PriceHistory(models.Model):
    """История цен (партиционируется по месяцам)"""
    cryptocurrency = models.ForeignKey(Cryptocurrency, on_delete=models.CASCADE, related_name='price_history')
    price_usd = models.DecimalField(max_digits=20, decimal_places=8)
    price_btc = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    market_cap = models.DecimalField(max_digits=30, decimal_places=2, null=True, blank=True)
    volume_24h = models.DecimalField(max_digits=30, decimal_places=2, null=True, blank=True)
    timestamp = models.DateTimeField()
    source = models.CharField(max_length=50, default='coingecko')

    objects = PriceHistoryManager()

    class Meta:
        unique_together = ['cryptocurrency', 'timestamp']
        indexes = [
            models.Index(fields=['cryptocurrency', '-timestamp']),
            models.Index(fields=['timestamp']),  # Для партиционирования по дате
        ]
        verbose_name_plural = "История цен"

    def save(self, *args, **kwargs):
        # Кешируем текущую цену при сохранении
        super().save(*args, **kwargs)
        cache.set(f'price_{self.cryptocurrency_id}_current', self.price_usd, timeout=300)


class BalanceSnapshot(models.Model):
    """Снимок баланса в определенный момент времени"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='balance_snapshots')
    cryptocurrency = models.ForeignKey(Cryptocurrency, on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=30, decimal_places=10)  # Всего монет
    usd_value = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    snapshot_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Снимки балансов"
        indexes = [
            # Для быстрого получения последнего снимка
            models.Index(fields=['user', 'cryptocurrency', '-snapshot_time']),
            models.Index(fields=['user', '-snapshot_time']),
            models.Index(fields=['-snapshot_time']),
        ]

#
# class Transaction(models.Model):
#     """Транзакция пользователя"""
#     TRANSACTION_TYPES = [
#         ('buy', 'Buy'),
#         ('sell', 'Sell'),
#         ('deposit', 'Deposit'),
#         ('withdrawal', 'Withdrawal'),
#         ('transfer', 'Transfer'),
#         ('staking_reward', 'Staking Reward'),
#         ('airdrop', 'Airdrop'),
#         ('fee', 'Fee'),
#     ]
#
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
#
#     transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
#     cryptocurrency = models.ForeignKey(Cryptocurrency, on_delete=models.CASCADE)
#
#     amount = models.DecimalField(max_digits=30, decimal_places=10)
#     price_per_unit = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
#     total_value = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
#
#     fee = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
#     fee_currency = models.ForeignKey(
#         Cryptocurrency,
#         on_delete=models.SET_NULL,
#         null=True, blank=True,
#         related_name='fee_transactions'
#     )
#
#     # Для депозитов/выводов
#     from_address = models.CharField(max_length=255, blank=True, null=True)
#     to_address = models.CharField(max_length=255, blank=True, null=True)
#     transaction_hash = models.CharField(max_length=255, blank=True, null=True)
#
#     # Для торгов
#     exchange_connection = models.ForeignKey(
#         UserExchangeConnection,
#         on_delete=models.SET_NULL,
#         null=True, blank=True
#     )
#     exchange_tx_id = models.CharField(max_length=255, blank=True, null=True)
#
#     # Для связки buy/sell (если нужно)
#     related_transaction = models.ForeignKey(
#         'self',
#         on_delete=models.SET_NULL,
#         null=True, blank=True
#     )
#
#     notes = models.TextField(blank=True, null=True)
#     transaction_time = models.DateTimeField()
#     recorded_at = models.DateTimeField(auto_now_add=True)
#
#     class Meta:
#         indexes = [
#             # Основные запросы:
#             models.Index(fields=['user', '-transaction_time']),  # История транзакций
#             models.Index(fields=['user', 'cryptocurrency', '-transaction_time']),  # История по монете
#             models.Index(fields=['user', 'transaction_type', '-transaction_time']),
#             models.Index(fields=['transaction_time']),  # Для партиционирования
#         ]
#         ordering = ['-transaction_time']
#
#
# class TaxLot(models.Model):
#     """Лот для расчета налогов (FIFO/LIFO)"""
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tax_lots')
#     cryptocurrency = models.ForeignKey(Cryptocurrency, on_delete=models.CASCADE)
#
#     buy_transaction = models.ForeignKey(
#         Transaction,
#         on_delete=models.CASCADE,
#         related_name='buy_lots'
#     )
#     sell_transaction = models.ForeignKey(
#         Transaction,
#         on_delete=models.SET_NULL,
#         null=True, blank=True,
#         related_name='sell_lots'
#     )
#
#     amount = models.DecimalField(max_digits=30, decimal_places=10)
#     purchase_price = models.DecimalField(max_digits=20, decimal_places=8)  # Цена покупки за единицу
#     purchase_date = models.DateTimeField()
#
#     sell_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
#     sell_date = models.DateTimeField(null=True, blank=True)
#
#     is_closed = models.BooleanField(default=False)
#     realized_pnl = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
#
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     class Meta:
#         indexes = [
#             models.Index(fields=['user', 'cryptocurrency', 'is_closed']),
#             models.Index(fields=['user', 'purchase_date']),
#         ]
#
#
class PortfolioSnapshot(models.Model):
    """Снимок портфеля (материализованное представление)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='portfolio_snapshots')

    total_value_usd = models.DecimalField(max_digits=20, decimal_places=2)
    total_value_btc = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)

    total_invested_usd = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    top_coins = models.JSONField(default=list, blank=True)  # [{"symbol": "BTC", "value": 10000, "percent": 50}]
    exchange_allocation = models.JSONField(default=dict, blank=True)  # {"binance": 5000, "bybit": 3000}

    snapshot_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Снимки портфелей"
        indexes = [
            models.Index(fields=['user', '-snapshot_time']),  # Последний снимок
            models.Index(fields=['snapshot_time']),  # Для агрегаций
        ]

#
# class AssetCache(models.Model):
#     """Кеш для агрегированных данных по активам"""
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='asset_caches')
#     cryptocurrency = models.ForeignKey(Cryptocurrency, on_delete=models.CASCADE)
#
#     total_amount = models.DecimalField(max_digits=30, decimal_places=10)
#     average_buy_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
#     current_price = models.DecimalField(max_digits=20, decimal_places=8)
#     current_value = models.DecimalField(max_digits=20, decimal_places=2)
#
#     # Распределение по биржам
#     exchange_breakdown = models.JSONField(default=dict)  # {"binance": 0.5, "bybit": 0.3}
#
#     last_updated = models.DateTimeField(auto_now=True)
#     expires_at = models.DateTimeField()  # Время устаревания кеша
#
#     class Meta:
#         unique_together = ['user', 'cryptocurrency']
#         indexes = [
#             models.Index(fields=['user', '-last_updated']),
#             models.Index(fields=['expires_at']),  # Для очистки старых кешей
#         ]

