# core/serializers.py
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import UserProfile, Customer, BankAccount, Transaction, Loan, Currency, Bank
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


# UserProfile Serializer
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'email', 'name', 'is_active', 'is_staff']


# Customer Serializer
class CustomerSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer()

    class Meta:
        model = Customer
        fields = ['id', 'user', 'phone', 'address']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserProfile.objects.create_user(**user_data)  # Create a UserProfile instance
        customer = Customer.objects.create(user=user, **validated_data)
        return customer


# BankAccount Serializer
class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ['id', 'customer', 'balance', 'is_suspended']


# Currency Serializer
class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['id', 'code', 'exchange_rate']


# Transaction Serializer
class TransactionSerializer(serializers.ModelSerializer):
    currency = CurrencySerializer()  # Include currency details in the transaction response

    class Meta:
        model = Transaction
        fields = ['id', 'account', 'amount', 'transaction_type', 'fee', 'currency']

    def create(self, validated_data):
        account = validated_data['account']
        fee_percentage = 0.02  # Example: 2% fee for all transactions
        amount = validated_data['amount']

        # Calculate the fee
        validated_data['fee'] = amount * fee_percentage

        try:
            if validated_data['transaction_type'] == 'deposit':
                account.deposit(amount)
            elif validated_data['transaction_type'] == 'withdraw':
                account.withdraw(amount)
            elif validated_data['transaction_type'] == 'transfer':
                target_account_id = validated_data.pop('target_account_id')
                target_account = BankAccount.objects.get(id=target_account_id)
                account.transfer(amount, target_account)
            else:
                raise ValidationError("Invalid transaction type.")  # Use the imported ValidationError
        except ValidationError as e:
            raise serializers.ValidationError({"error": str(e)})

        account.save()
        return super().create(validated_data)


# Loan Serializer
class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = ['id', 'customer', 'amount', 'is_repaid']

    def create(self, validated_data):
        bank = Bank.objects.first()  # Assume you have a single bank instance
        amount = validated_data['amount']

        if amount > 50000:
            raise serializers.ValidationError("Maximum loan is 50,000 NIS.")

        if bank.balance < amount:
            raise serializers.ValidationError("Bank does not have enough funds for this loan.")

        bank.grant_loan(amount)
        loan = Loan.objects.create(**validated_data)
        return loan


class DepositView(APIView):
    def post(self, request, account_id):
        account = BankAccount.objects.get(id=account_id)  # Get the bank account
        serializer = DepositSerializer(data=request.data)
        if serializer.is_valid():
            amount = serializer.validated_data['amount']
            currency_code = serializer.validated_data['currency']
            # Process deposit using the account object
            # Make sure to implement deposit method in BankAccount model
            account.deposit(amount, currency_code)
            return Response({"message": "Deposit successful."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Deposit Serializer
class DepositSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3)

    @staticmethod
    def validate_currency(value):
        if not Currency.objects.filter(code=value).exists():
            raise serializers.ValidationError("Invalid currency code.")
        return value

    def create(self, validated_data):
        amount = validated_data['amount']
        currency_code = validated_data['currency']

        # Create a new transaction for the deposit
        transaction = Transaction.objects.create(
            account=self.context['account'],  # Assuming you're passing the account in context
            amount=amount,
            transaction_type='deposit',  # Assuming you have a field for the type of transaction
            currency=currency_code
        )
        return transaction  # You might return the transaction or some other relevant data

    def update(self, instance, validated_data):
        # Here you might want to update an existing transaction if needed
        instance.amount = validated_data.get('amount', instance.amount)
        instance.currency = validated_data.get('currency', instance.currency)

        # Save the updated instance
        instance.save()
        return instance
