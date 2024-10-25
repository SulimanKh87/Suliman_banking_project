# core/serializers.py
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import UserProfile, Customer, BankAccount, Transaction, Loan, Currency, Bank
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.validators import MinLengthValidator, MaxLengthValidator


# UserProfile Serializer
class UserProfileSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[
            MinLengthValidator(8),  # Minimum length for password
            MaxLengthValidator(20)  # Maximum length for password
        ]
    )
    name = serializers.CharField(
        validators=[
            MinLengthValidator(2),  # Minimum length for name
            MaxLengthValidator(20)  # Maximum length for name
        ]
    )

    class Meta:
        model = UserProfile
        fields = ['id', 'email', 'name', 'password', 'is_active', 'is_staff']
        read_only_fields = ['id']  # Make 'id' read-only

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = UserProfile(**validated_data)
        user.set_password(password)
        user.save()
        return user


# Customer Serializer
class CustomerSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer()

    class Meta:
        model = Customer
        fields = ['id', 'user', 'phone', 'address']
        read_only_fields = ['id']  # Make 'id' read-only

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserProfileSerializer().create(user_data)
        customer = Customer.objects.create(user=user, **validated_data)
        return customer


# BankAccount Serializer
class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ['id', 'customer', 'balance', 'is_suspended']
        read_only_fields = ['id', 'customer']


# Currency Serializer
class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['id', 'code', 'exchange_rate']


# Transaction Serializer
class TransactionSerializer(serializers.ModelSerializer):
    currency = serializers.PrimaryKeyRelatedField(queryset=Currency.objects.all())

    class Meta:
        model = Transaction
        fields = ['id', 'account', 'amount', 'transaction_type', 'fee', 'currency']
        read_only_fields = ['id']

    @staticmethod
    def validate_transaction_type(value):
        if value not in ['deposit', 'withdraw', 'transfer']:
            raise serializers.ValidationError("Invalid transaction type.")
        return value

    def create(self, validated_data):
        account = validated_data['account']
        fee_percentage = 0.02
        amount = validated_data['amount']
        transaction_type = validated_data['transaction_type']

        validated_data['fee'] = amount * fee_percentage

        try:
            if transaction_type == 'deposit':
                account.deposit(amount)
            elif transaction_type == 'withdraw':
                account.withdraw(amount)
            elif transaction_type == 'transfer':
                target_account_id = validated_data.pop('target_account_id')
                target_account = BankAccount.objects.get(id=target_account_id)
                account.transfer(amount, target_account)
            else:
                raise ValidationError("Invalid transaction type.")
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
        bank = Bank.objects.first()
        amount = validated_data['amount']

        if amount > 50000:
            raise serializers.ValidationError("Maximum loan is 50,000 NIS.")

        if bank.balance < amount:
            raise serializers.ValidationError("Bank does not have enough funds for this loan.")

        bank.grant_loan(amount)
        loan = Loan.objects.create(**validated_data)
        return loan


# Deposit Serializer
class DepositSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3)

    @staticmethod
    def validate_currency(value):
        if not Currency.objects.filter(code__iexact=value).exists():
            raise serializers.ValidationError("Invalid currency code.")
        return value

    def create(self, validated_data):
        amount = validated_data['amount']
        currency_code = validated_data['currency']
        currency = Currency.objects.get(code=currency_code)

        transaction = Transaction.objects.create(
            account=self.context['account'],
            amount=amount,
            transaction_type='deposit',
            currency=currency
        )
        return transaction

    def update(self, instance, validated_data):
        instance.amount = validated_data.get('amount', instance.amount)
        instance.currency = validated_data.get('currency', instance.currency)
        instance.save()
        return instance


# Deposit View
class DepositView(APIView):
    def post(self, request, account_id):
        try:
            account = BankAccount.objects.get(id=account_id)
        except BankAccount.DoesNotExist:
            return Response({"error": "Account not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = DepositSerializer(data=request.data, context={'account': account})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Deposit successful."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
