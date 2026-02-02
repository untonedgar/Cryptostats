import requests
from decimal import Decimal
import time


def fetch_solana_wallet_balances_aggregated(wallet_address: str) -> dict:
    """
    Получает балансы Solana кошелька с символами токенов.
    Возвращает: {"SOL": 1.23, "USDC": 45.67, "USDT": 100.50}
    """
    # Ваш API ключ Helius
    HELIUS_API_KEY = 'b3047845-132c-4e45-a382-9ab30433d1cd'

    result = {}

    try:
        print(f"🔍 Анализируем кошелек: {wallet_address[:8]}...{wallet_address[-4:]}")

        # 1. Получаем балансы от Helius
        helius_url = f"https://api.helius.xyz/v0/addresses/{wallet_address}/balances?api-key={HELIUS_API_KEY}"
        response = requests.get(helius_url, timeout=15)
        data = response.json()

        # 2. Обрабатываем SOL
        if 'nativeBalance' in data:
            sol_lamports = int(data['nativeBalance'])
            result['SOL'] = Decimal(str(sol_lamports)) / Decimal(1_000_000_000)
            print(f"✓ SOL: {result['SOL']}")

        # 3. Обрабатываем токены
        if 'tokens' in data:
            tokens = data['tokens']
            print(f"📊 Найдено токен-аккаунтов: {len(tokens)}")

            # Собираем mint адреса для запроса информации
            mint_to_amount = {}
            for token in tokens:
                mint = token.get('mint')
                amount = token.get('amount', 0)
                decimals = token.get('decimals', 0)

                if amount > 0 and decimals > 0:
                    actual_amount = Decimal(str(amount)) / (Decimal(10) ** decimals)
                    if actual_amount > Decimal('0.000001'):  # Игнорируем мелочь
                        mint_to_amount[mint] = actual_amount

            print(f"💰 Ненулевых токенов: {len(mint_to_amount)}")

            # 4. Получаем символы токенов (если есть токены)
            if mint_to_amount:
                symbols = get_token_symbols_batch(list(mint_to_amount.keys()))

                # Добавляем токены в результат
                for mint, amount in mint_to_amount.items():
                    symbol = symbols.get(mint, mint[:8] + "..." + mint[-4:])
                    result[symbol] = amount
                    print(f"✓ {symbol}: {amount}")

        print(f"✅ Итого монет: {len(result)}")
        return result

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return {}


def get_token_symbols_batch(mint_addresses: list) -> dict:
    """
    Получает символы для списка mint адресов.
    Пробует разные API эндпоинты.
    """
    if not mint_addresses:
        return {}

    print(f"🔍 Запрашиваем символы для {len(mint_addresses)} токенов...")

    # Пробуем разные API (один из них должен сработать)
    api_endpoints = [
        "https://api.jup.ag/api/tokens/v1",
        "https://cache.jup.ag/tokens",
        "https://tokens.jup.ag/tokens",
    ]

    all_tokens = []

    for endpoint in api_endpoints:
        try:
            print(f"Пробуем {endpoint}...")
            response = requests.get(endpoint, timeout=10)
            if response.status_code == 200:
                all_tokens = response.json()
                print(f"✓ Успешно получили {len(all_tokens)} токенов")
                break
        except Exception as e:
            print(f"⚠️ {endpoint} не сработал: {e}")
            continue

    # Если не получилось через API, используем статический список популярных
    if not all_tokens:
        print("⚠️ API не сработали, используем статический список...")
        return get_static_token_symbols(mint_addresses)

    # Создаем маппинг mint → symbol
    mint_to_symbol = {}
    for token in all_tokens:
        mint = token.get('address') or token.get('mint')
        symbol = token.get('symbol')
        if mint and symbol:
            mint_to_symbol[mint] = symbol

    # Для наших адресов
    result = {}
    found_count = 0

    for mint in mint_addresses:
        if mint in mint_to_symbol:
            result[mint] = mint_to_symbol[mint]
            found_count += 1
        else:
            # Сокращенное представление
            result[mint] = mint[:8] + "..." + mint[-4:]

    print(f"📊 Найдено символов: {found_count}/{len(mint_addresses)}")
    return result


def get_static_token_symbols(mint_addresses: list) -> dict:
    """
    Статический список самых популярных Solana токенов
    (только основные, чтобы не грузить API)
    """
    # ТОП-20 самых популярных Solana токенов
    POPULAR_TOKENS = {
        # Stablecoins
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
        "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT",

        # Major DeFi
        "SRMuApVNdxXokk5GT7XD5cUUgXMBCoAz2LHeuAoKWRt": "SRM",
        "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R": "RAY",
        "SLNDpmoWTVADgEdndyvWzroNL7zSi1dF9PC3xHGtPwp": "SLND",
        "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE": "ORCA",

        # Major Tokens
        "So11111111111111111111111111111111111111112": "wSOL",
        "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So": "mSOL",
        "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj": "stSOL",

        # Meme Tokens
        "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU": "SAMO",

        # Other Popular
        "StepAscQoEioFxxWGnh2sLBDFp9d8rvKz2Yp39iDpyT": "STEP",
        "MERt85fc5boKw3BW1eYdxonEuJNvXbiMbs6hvheau5K": "MER",

        # WORMHOLE TOKENS (W)
        "85VBFQZC9TZkfaptBWjvUw7YbZjy52A6mjtPGjstQAmQ": "WETH",  # Wormhole Wrapped ETH
        "A9mUU4qviSctJVPJdBJWkb28deg915LYJKrzQ19ji3FM": "WUSDC",  # Wormhole Wrapped USDC
        "DYDWu4hE4MN3a311YPM1k8wFfHVefZFAAddLqYqcnwtG": "WUSDT",  # Wormhole Wrapped USDT
        "3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh": "WBTC",  # Wormhole Wrapped BTC
        "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3": "W",  # Wormhole Token (W)
        "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm": "WDAI",  # Wormhole DAI
        "5goWRao6a3yNC4d6UjMdQxonkCMvKBwdpubU3qhfcdf1": "WMATIC",  # Wormhole MATIC

        # Jupiter aggregator
        "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN": "JUP",  # Jupiter token
    }

    result = {}
    for mint in mint_addresses:
        if mint in POPULAR_TOKENS:
            result[mint] = POPULAR_TOKENS[mint]
        else:
            # Сокращаем для незнакомых токенов
            result[mint] = mint[:8] + "..." + mint[-4:]

    return result