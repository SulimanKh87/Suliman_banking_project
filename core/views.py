# core/views.py
from rest_framework import viewsets, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from decimal import Decimal
from rest_framework.decorators import action
from .models import UserProfile, Customer, BankAccount, Transaction, Loan, Bank
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    CustomerSerializer,
    BankAccountSerializer,
    TransactionSerializer,
    LoanSerializer,
    UserProfileSerializer
)


# Customer ViewSet
class CustomerViewSet(viewsets.ModelViewSet):
    """
       ViewSet for handling CRUD operations for Customer instances.
       """
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
               Create a new customer instance.
               """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
         Update an existing customer instance.
         """
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
          Delete a customer instance.
          """
        return super().destroy(request, *args, **kwargs)


class BankAccountViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing operations related to bank accounts, including deposits and withdrawals.
    """
    queryset = BankAccount.objects.all()
    serializer_class = BankAccountSerializer

    @action(detail=True, methods=['post'])
    def deposit(self, request, pk=None):
        """
        Handle deposits to a bank account.
        """
        account = self.get_object()  # Fetch the account using the primary key (pk)

        # Check if the account is suspended
        if account.is_suspended:  # Assuming you have an `is_suspended` field in your model
            return Response({'error': 'Cannot deposit to a suspended account.'}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure amount is provided in the request
        amount = request.data.get('amount', 0)
        if amount <= 0:
            return Response({'error': 'Invalid deposit amount'}, status=status.HTTP_400_BAD_REQUEST)

        # Update account balance
        account.balance += Decimal(amount)
        account.save()

        return Response({'success': 'Deposit successful', 'new_balance': account.balance}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """
        Handle withdrawals from a bank account.
        """
        account = self.get_object()  # Fetch the account using the primary key (pk)

        # Check if the account is suspended
        if account.is_suspended:  # Assuming you have an `is_suspended` field in your model
            return Response({'error': 'Cannot withdraw from a suspended account.'}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure amount is provided in the request
        amount = request.data.get('amount', 0)
        if amount <= 0:
            return Response({'error': 'Invalid withdrawal amount'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if there are sufficient funds for withdrawal
        if account.balance < Decimal(amount):
            return Response({'error': 'Insufficient funds for withdrawal'}, status=status.HTTP_400_BAD_REQUEST)

        # Update account balance
        account.balance -= Decimal(amount)
        account.save()

        return Response({'success': 'Withdrawal successful', 'new_balance': account.balance}, status=status.HTTP_200_OK)


# Transaction ViewSet
class TransactionViewSet(viewsets.ModelViewSet):
    """
        ViewSet for handling CRUD operations for transactions related to accounts.
        """
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """ Return transactions associated with the authenticated user's accounts. """
        user = self.request.user
        return Transaction.objects.filter(account__customer__user=user)


# Loan ViewSet
class LoanViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing loan operations including creation and repayments.
    """
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
             Create a new loan if the bank has sufficient funds.
             """
        amount = request.data.get('amount')
        bank = Bank.objects.first()  # Assuming only one bank instance

        if bank.balance < amount:
            return Response({"error": "Bank does not have enough funds for this loan."},
                            status=status.HTTP_400_BAD_REQUEST)

        bank.grant_loan(amount)  # Grant loan logic in the model
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
           Update an existing loan instance.
           """
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
              Delete a loan instance.
              """
        return super().destroy(request, *args, **kwargs)

    def repay(self, request, pk=None):  # Include pk parameter for consistency
        """
         Handle loan repayment for a specific loan instance.
         """
        loan = self.get_object()
        repayment_amount = request.data.get('repayment_amount')
        loan.repay(repayment_amount)  # Repay logic in the model
        return Response({"message": "Loan repayment successful."}, status=status.HTTP_200_OK)

    @staticmethod
    def get_customer_loans(customer_id):
        """
             Retrieve all loans associated with a specific customer.
             """
        loans = Loan.objects.filter(customer__id=customer_id)
        serializer = LoanSerializer(loans, many=True)
        return Response(serializer.data)


# Loan Repayment ViewSet
class LoanRepaymentViewSet(viewsets.ViewSet):
    """
    ViewSet specifically for managing loan repayment requests.
    """
    permission_classes = [IsAuthenticated]

    def create(self, request, pk=None):
        """
           Process a loan repayment for a specified loan.
           """
        loan = Loan.objects.get(pk=pk)
        repayment_amount = request.data.get('repayment_amount')

        try:
            loan.repay(repayment_amount)
            return Response({"message": "Loan repayment successful."}, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# User Profile ViewSet
class UserProfileViewSet(viewsets.ModelViewSet):
    """ ViewSet for handling CRUD operations for user profiles.
        Only allow authenticated users to edit their own profile data."""
    serializer_class = UserProfileSerializer
    authentication_classes = [TokenAuthentication]
    # IsAuthenticated will allow the user to perform the actions defined in,
    # on their own profile
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        return UserProfile.objects.filter(user=user)
    # queryset = UserProfile.objects.all()
