from django.contrib import admin
from balance.models import User, Exchange, UserExchangeConnection, BalanceSnapshot, Cryptocurrency, PriceHistory, PortfolioSnapshot, BlockchainNetwork, UserWalletConnection


class ExchangeAdmin(admin.ModelAdmin):
    list_display = ('name', 'api_docs_url', 'supports')

    search_fields = ('name', 'supports')

class UserExchangeConnectionAdmin(admin.ModelAdmin):
    list_display = ('user', 'exchange')

class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('cryptocurrency', 'price_usd', 'timestamp')

class BalanceSnapshotAdmin(admin.ModelAdmin):
    list_display = ('user', 'cryptocurrency', 'total_amount', 'usd_value', 'created_at')

class PortfolioSnapshotAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_value_usd', 'snapshot_time')

class BlockchainNetworkAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'chain_id', 'native_coin')

class UserWalletConnectionAdmin(admin.ModelAdmin):
    list_display = ('user', 'network', 'nickname')

admin.site.register(User)
admin.site.register(Exchange, ExchangeAdmin)
admin.site.register(UserExchangeConnection, UserExchangeConnectionAdmin)
admin.site.register(BalanceSnapshot, BalanceSnapshotAdmin)
admin.site.register(Cryptocurrency)
admin.site.register(PriceHistory, PriceHistoryAdmin)
admin.site.register(PortfolioSnapshot, PortfolioSnapshotAdmin)
admin.site.register(BlockchainNetwork, BlockchainNetworkAdmin)
admin.site.register(UserWalletConnection, UserWalletConnectionAdmin)
# Register your models here.
