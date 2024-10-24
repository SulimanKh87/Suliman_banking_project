from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, BankAccountViewSet, TransactionViewSet, LoanViewSet, LoanRepaymentViewSet
from .views import DepositView

# Initialize the default router
router = DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'accounts', BankAccountViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'loans', LoanViewSet)

# Define the URL patterns
urlpatterns = [
    path('', include(router.urls)),
    re_path(r'^loans/(?P<pk>[^/.]+)/repay/$', LoanRepaymentViewSet.as_view({'post': 'create'}), name='loan-repay'),
    path('bankaccount/<int:account_id>/deposit/', DepositView.as_view(), name='bankaccount-deposit'),  # Deposit URL
]
