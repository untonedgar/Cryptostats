from typing import Protocol, Dict
import requests
from decimal import Decimal
from django.conf import settings
from typing import Set


class BalanceProvider(Protocol):
    """Протокол для поставщиков балансов"""

    def get_balances(self, address: str) -> Dict[str, Decimal]:
        ...


class NetworkResolver(Protocol):
    """Протокол для определения сети"""

    def resolve_chain(self, network) -> str:
        ...


class TokenFilter(Protocol):
    """Протокол для фильтрации токенов"""

    def should_include(self, token_data: dict) -> bool:
        ...


class MoralisBalanceProvider:
    """Поставщик балансов через Moralis API"""

    def __init__(self, api_key: str, chain_resolver: 'NetworkResolver', token_filter: 'TokenFilter'):
        self.api_key = api_key
        self.chain_resolver = chain_resolver
        self.token_filter = token_filter

    def get_balances(self, address: str, network) -> Dict[str, Decimal]:
        """Основной метод получения балансов"""
        chain = self.chain_resolver.resolve_chain(network)

        if chain == "solana":
            return self._get_solana_balances(address)
        else:
            return self._get_evm_balances(address, chain)

    def _get_solana_balances(self, address: str) -> Dict[str, Decimal]:
        """Получение балансов Solana"""
        url = f"https://solana-gateway.moralis.io/account/mainnet/{address}/tokens"
        headers = {"X-API-Key": self.api_key}

        try:
            print(f"🌐 Solana запрос для {address[:8]}...")
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            print(f"📊 Solana: получено {len(data)} токенов от Moralis")

            # Отладочный вывод первых токенов
            for i, token in enumerate(data[:5]):
                symbol = token.get("symbol", "NO_SYMBOL")
                amount = token.get("amount", "0")
                possible_spam = token.get("possibleSpam", False)
                print(f"  Токен {i}: {symbol} = {amount}, spam={possible_spam}")

            return self._process_solana_tokens(data)

        except requests.RequestException as e:
            print(f"❌ Solana request error: {e}")
            return {}

    def _get_evm_balances(self, address: str, chain: str) -> Dict[str, Decimal]:
        """Получение балансов EVM сетей"""
        url = f"https://deep-index.moralis.io/api/v2.2/{address}/erc20"
        headers = {"X-API-Key": self.api_key}
        params = {"chain": chain, "exclude_spam": "true"}

        try:
            print(f"🌐 EVM запрос {chain}: {address[:8]}...")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            print(f"📊 EVM {chain}: получено {len(data)} токенов от Moralis")

            # Отладочный вывод
            for i, token in enumerate(data[:5]):
                symbol = token.get("symbol", "NO_SYMBOL")
                balance = token.get("balance", "0")
                decimals = token.get("decimals", 18)
                usd_price = token.get("usd_price", 0)
                print(f"  Токен {i}: {symbol} = {balance}, price={usd_price}")

            return self._process_evm_tokens(data)

        except requests.RequestException as e:
            print(f"❌ EVM request error for {chain}: {e}")
            return {}

    def _process_solana_tokens(self, tokens_data: list) -> Dict[str, Decimal]:
        """Обработка Solana токенов"""
        tokens = {}

        for token in tokens_data:
            if not self.token_filter.should_include(token):
                continue

            symbol = token.get("symbol", "").upper()
            amount_str = token.get("amount", "0")
            decimals = token.get("decimals", 9)

            try:
                # ⚡ ВАЖНОЕ ИСПРАВЛЕНИЕ:
                # Для Solana amount УЖЕ нормализован в Moralis!
                # "amount": "10734.885314" - это уже конечное количество
                amount = Decimal(amount_str)

                # ⚡ НЕ делим на decimals повторно!
                # amount = Decimal(amount_str) / (Decimal(10) ** decimals)  ← УДАЛИТЬ ЭТО!

                if amount > 0:
                    tokens[symbol] = amount.quantize(Decimal("0.00000001"))
                    print(f"  ✅ Solana: {symbol} = {amount} (decimals={decimals})")
            except Exception as e:
                print(f"⚠️ Error processing Solana token {symbol}: {e}")
                continue

        return tokens

    def _process_evm_tokens(self, tokens_data: list) -> Dict[str, Decimal]:
        """Обработка EVM токенов"""
        tokens = {}

        for token in tokens_data:
            symbol = token.get("symbol", "")

            if not self.token_filter.should_include(token):
                print(f"  ⚠️ EVM токен отфильтрован: {symbol}")
                continue

            symbol_upper = symbol.upper()
            balance_raw = token.get("balance", "0")
            decimals = token.get("decimals", 18)

            try:
                amount = Decimal(balance_raw) / (Decimal(10) ** decimals)
                if amount > 0:
                    tokens[symbol_upper] = amount.quantize(Decimal("0.00000001"))
                    print(f"  ✅ EVM добавлен: {symbol_upper} = {amount}")
            except Exception as e:
                print(f"⚠️ Error processing EVM token {symbol}: {e}")
                continue

        return tokens


class MoralisNetworkResolver:
    """Преобразует названия сетей в коды Moralis"""

    CHAIN_MAPPING: Dict[str, str] = {
        "ethereum": "eth",
        "polygon": "polygon",
        "bsc": "bsc",
        "arbitrum": "arbitrum",
        "avalanche": "avalanche",
        "fantom": "fantom",
        "solana": "solana",
        "optimism": "optimism",
        "cronos": "cronos",
    }

    def resolve_chain(self, network) -> str:
        """Преобразует сеть в код Moralis"""
        if hasattr(network, 'name'):
            network_name = network.name.lower()
        else:
            network_name = str(network).lower()

        chain = self.CHAIN_MAPPING.get(network_name)

        if not chain:
            raise ValueError(f"Unsupported network for Moralis: {network_name}")

        return chain


class DefaultTokenFilter:
    """Фильтр токенов по умолчанию для EVM сетей - БЕЗ проверки цены!"""

    SPAM_SYMBOLS: Set[str] = {"SPAM", "DUST", "TEST", "FAKE", "SCAM", "ERC20"}
    MAX_SYMBOL_LENGTH = 20

    def should_include(self, token_data: dict) -> bool:
        """Определяет, нужно ли включать токен в результат"""
        symbol = token_data.get("symbol", "")

        # Проверка символа
        if not symbol:
            return False

        symbol_upper = symbol.upper()

        # Проверка на спам символы
        if symbol_upper in self.SPAM_SYMBOLS:
            return False

        # Проверка длины символа
        if len(symbol_upper) > self.MAX_SYMBOL_LENGTH:
            return False

        # ⚡ ВАЖНОЕ ИЗМЕНЕНИЕ: НЕ проверяем usd_price!
        # Moralis часто возвращает price=0, но это не значит что токен бесполезен
        # Цены будем получать отдельно через fetch_prices_for_symbols

        return True


class SolanaTokenFilter:
    """Фильтр токенов для Solana"""

    SPAM_SYMBOLS: Set[str] = {"SPAM", "DUST", "TEST", "FAKE", "SCAM"}
    MAX_SYMBOL_LENGTH = 30

    def should_include(self, token_data: dict) -> bool:
        """Определяет, нужно ли включать токен в результат для Solana"""
        symbol = token_data.get("symbol", "")

        # Если нет символа, можно проверить по mint (контракту)
        if not symbol:
            mint = token_data.get("mint", "")
            if not mint:
                return False

            # Известные контракты Solana
            known_mints = {
                "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
                "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT",
                "85VBFQZC9TZkfaptBWjvUw7YbZjy52A6mjtPGjstQAmQ": "W",  # Wormhole
            }
            if mint in known_mints:
                return True

            # Неизвестный токен без символа
            return False

        symbol_upper = symbol.upper()

        # Проверка на спам символы
        if symbol_upper in self.SPAM_SYMBOLS:
            return False

        # Проверка длины символа
        if len(symbol_upper) > self.MAX_SYMBOL_LENGTH:
            return False

        # Проверяем possibleSpam от Moralis
        possible_spam = token_data.get("possibleSpam", False)
        if possible_spam:
            return False

        # Проверка количества
        amount_str = token_data.get("amount", "0")
        try:
            amount = float(amount_str)
            if amount <= 0:
                return False
        except ValueError:
            return False

        return True


class NativeBalanceService:
    """Сервис для получения нативных балансов"""

    NATIVE_SYMBOLS: Dict[str, str] = {
        "eth": "ETH",
        "polygon": "MATIC",
        "bsc": "BNB",
        "arbitrum": "ETH",
        "avalanche": "AVAX",
        "fantom": "FTM",
        "solana": "SOL",
        "optimism": "ETH",
        "cronos": "CRO",
    }

    DECIMALS: Dict[str, int] = {
        "solana": 9,
        "default": 18,
    }

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_native_balance(self, address: str, chain: str) -> Decimal:
        """Получает нативный баланс"""
        if chain == "solana":
            return self._get_solana_balance(address)
        else:
            return self._get_evm_native_balance(address, chain)

    def _get_solana_balance(self, address: str) -> Decimal:
        """Баланс SOL"""
        url = f"https://solana-gateway.moralis.io/account/mainnet/{address}/balance"
        headers = {"X-API-Key": self.api_key}

        try:
            print(f"🌐 Solana native запрос для {address[:8]}...")
            response = requests.get(url, headers=headers, timeout=5)
            data = response.json()
            balance_str = data.get("solana", "0")
            balance = self._normalize_amount(balance_str, "solana")
            print(f"  Solana native balance: {balance} SOL")
            return balance
        except Exception as e:
            print(f"⚠️ Solana native balance error: {e}")
            return Decimal("0")

    def _get_evm_native_balance(self, address: str, chain: str) -> Decimal:
        """Баланс нативной валюты EVM"""
        url = f"https://deep-index.moralis.io/api/v2/{address}/balance"
        headers = {"X-API-Key": self.api_key}
        params = {"chain": chain}

        try:
            print(f"🌐 EVM native запрос {chain}: {address[:8]}...")
            response = requests.get(url, headers=headers, params=params, timeout=5)
            data = response.json()
            balance_str = data.get("balance", "0")
            balance = self._normalize_amount(balance_str, "default")
            print(f"  {chain} native balance: {balance} {self.get_native_symbol(chain)}")
            return balance
        except Exception as e:
            print(f"⚠️ EVM native balance error for {chain}: {e}")
            return Decimal("0")

    def _normalize_amount(self, balance_str: str, chain_type: str) -> Decimal:
        """Нормализует количество с учетом decimals"""
        try:
            decimals = self.DECIMALS.get(chain_type, 18)
            amount = Decimal(balance_str) / (Decimal(10) ** decimals)
            return amount.quantize(Decimal("0.00000001"))
        except Exception:
            return Decimal("0")

    def get_native_symbol(self, chain: str) -> str:
        """Возвращает символ нативной валюты"""
        return self.NATIVE_SYMBOLS.get(chain, chain.upper())


class WalletBalanceService:
    """Основной сервис для получения балансов кошелька"""

    def __init__(
            self,
            balance_provider: MoralisBalanceProvider,
            native_balance_service: NativeBalanceService,
            network_resolver: MoralisNetworkResolver
    ):
        self.balance_provider = balance_provider
        self.native_balance_service = native_balance_service
        self.network_resolver = network_resolver

    def get_wallet_balances(self, address: str, network) -> Dict[str, Decimal]:
        """
        Получает все балансы кошелька (токены + нативные)
        """
        print(f"🌐 Запрос балансов для сети '{network}' {address[:8]}...")

        # Получаем балансы токенов
        tokens = self.balance_provider.get_balances(address, network)

        # Получаем нативный баланс
        try:
            chain = self.network_resolver.resolve_chain(network)
            print(f"  Chain resolved: {chain}")

            native_balance = self.native_balance_service.get_native_balance(address, chain)

            if native_balance > 0:
                native_symbol = self.native_balance_service.get_native_symbol(chain)

                # Добавляем нативный баланс только если его еще нет
                if native_symbol not in tokens:
                    tokens[native_symbol] = native_balance
                    print(f"  ✅ Добавлен нативный баланс: {native_symbol} = {native_balance}")
                else:
                    print(f"  ℹ️ Нативный токен {native_symbol} уже есть в списке")

        except ValueError as e:
            print(f"⚠️ Cannot get native balance: {e}")
        except Exception as e:
            print(f"⚠️ Error getting native balance: {e}")

        print(f"✅ Найдено {len(tokens)} токенов: {list(tokens.keys())}")
        return tokens


class WalletServiceFactory:
    """Фабрика для создания сервисов"""

    @staticmethod
    def create_service_for_network(network_name: str) -> WalletBalanceService:
        """Создает сервис с учетом типа сети"""
        # Создаем компоненты
        network_resolver = MoralisNetworkResolver()

        # Создаем фильтр в зависимости от сети
        if network_name.lower() == "solana":
            print("🔧 Используем SolanaTokenFilter")
            token_filter = SolanaTokenFilter()
        else:
            print("🔧 Используем DefaultTokenFilter (без проверки цены)")
            token_filter = DefaultTokenFilter()

        # Создаем провайдер балансов
        balance_provider = MoralisBalanceProvider(
            api_key=settings.MORALIS_API_KEY,
            chain_resolver=network_resolver,
            token_filter=token_filter
        )

        # Создаем сервис нативных балансов
        native_service = NativeBalanceService(api_key=settings.MORALIS_API_KEY)

        # Создаем основной сервис
        return WalletBalanceService(
            balance_provider=balance_provider,
            native_balance_service=native_service,
            network_resolver=network_resolver
        )