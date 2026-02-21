from balance.utils.get_balances.moralic import WalletServiceFactory
from decimal import Decimal
from typing import Dict
from balance.utils.optimizathion import timer

@timer
def fetch_wallet_raw_balances(address: str, network) -> Dict[str, Decimal]:
    """
    ОДИН запрос → ВСЕ токены кошелька в конкретной сети

    Использование в вашем коде:
    symbol_amounts = fetch_wallet_raw_balances(address, wallet_network)
    """
    try:
        # Получаем имя сети
        if hasattr(network, 'name'):
            network_name = network.name
        else:
            network_name = str(network)

        print(f"🔍 Получение балансов для {network_name}: {address[:8]}...")

        # Создаем сервис для конкретной сети
        service = WalletServiceFactory.create_service_for_network(network_name)

        # Получаем балансы
        return service.get_wallet_balances(address, network)

    except Exception as e:
        print(f"❌ Error in fetch_wallet_raw_balances: {e}")
        return {}