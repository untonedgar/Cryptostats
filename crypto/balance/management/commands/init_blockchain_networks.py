from django.core.management.base import BaseCommand
from balance.models import BlockchainNetwork


NETWORKS = [
    {"name": "Ethereum", "slug": "eth", "chain_id": 1, "native_coin": "ETH"},
    {"name": "Arbitrum", "slug": "arbitrum", "chain_id": 42161, "native_coin": "ETH"},
    {"name": "Optimism", "slug": "optimism", "chain_id": 10, "native_coin": "ETH"},
    {"name": "Polygon", "slug": "polygon", "chain_id": 137, "native_coin": "MATIC"},
    {"name": "BNB Smart Chain", "slug": "bsc", "chain_id": 56, "native_coin": "BNB"},
    {"name": "Avalanche", "slug": "avax", "chain_id": 43114, "native_coin": "AVAX"},
]


class Command(BaseCommand):
    help = "Init blockchain networks"

    def handle(self, *args, **kwargs):
        for net in NETWORKS:
            BlockchainNetwork.objects.update_or_create(
                chain_id=net["chain_id"],
                defaults=net,
            )

        self.stdout.write(self.style.SUCCESS("Blockchain networks initialized"))