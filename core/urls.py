from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, BankAccountViewSet, TransactionViewSet, LoanViewSet, LoanRepaymentViewSet

# Initialize the default router
router = DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'accounts', BankAccountViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'loans', LoanViewSet)

# Define the URL patterns
urlpatterns = [
    path('', include(router.urls)),
    # Custom URL for loan repayment
    re_path(r'^loans/(?P<pk>[^/.]+)/repay/$', LoanRepaymentViewSet.as_view({'post': 'create'}), name='loan-repay'),
    # Custom URL for making a deposit, now handled by BankAccountViewSet
    # Deposit URL
    path('bankaccount/<int:account_id>/deposit/',
         BankAccountViewSet.as_view({'post': 'deposit'}), name='bankaccount-deposit'),
]
