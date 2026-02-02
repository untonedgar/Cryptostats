from django.urls import path
from django.contrib.auth.views import TemplateView
from balance.views import ExchangeList, UserExchangesListView, add_exchange, delete_exchange, view_user_balances, add_wallet, delete_wallet


urlpatterns = [
    path('', TemplateView.as_view(template_name="main.html"), name="main",),
    path('list_of_exchanges/', ExchangeList.as_view(), name="list_of_exchanges",),
    path('add_exchange/<int:exchange_id>/', add_exchange, name='add_exchange'),
    path('my_exchanges/', UserExchangesListView.as_view(), name='my_exchanges'),
    path('delete_exchange/<int:pk>/', delete_exchange, name='delete_exchange'),
    path('balances/', view_user_balances, name='user_balances'),
    path('add_wallet/', add_wallet, name='add_wallet'),
    path('delete_wallet/<int:pk>/', delete_wallet, name='delete_wallet'),
]