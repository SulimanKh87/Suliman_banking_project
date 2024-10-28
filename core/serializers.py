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
    """
      Serializer for UserProfile model.

      Handles the serialization and validation of UserProfile instances,
      including password hashing and validation of name and password lengths.
      """
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
        read_only_fields = ['id', 'is_active', 'is_staff']  # Make 'id' read-only

    def create(self, validated_data):
        """
          Create a new UserProfile instance.

          Populates the UserProfile with validated data, hashes the password,
          and saves the user. Returns the created user instance.
          """
        password = validated_data.pop('password')
        user = UserProfile(**validated_data)
        user.set_password(password)
        user.save()
        return user


# Customer Serializer
class CustomerSerializer(serializers.ModelSerializer):
    """
    Serializer for Customer model.

    Handles the serialization and validation of Customer instances,
    including nested serialization for the associated UserProfile.
    """
    user = UserProfileSerializer()

    class Meta:
        model = Customer
        fields = ['id', 'user', 'phone', 'address']
        read_only_fields = ['id']  # Make 'id' read-only, cannot be altered when creating or updating

    """ example
    {
    "id1": 1, # is primary key for Customer
    "user": {   
        "id2": 1, # is primary key for User
        "email": "user@example.com",
        "name": "John Doe"
    },
    "phone": "123-456-7890",
    "address": "123 Main Street"
    }

    """

    def create(self, validated_data):
        """
             Create a new Customer instance.

             Extracts user data, creates a UserProfile instance, and then
             creates a Customer instance with the remaining validated data.
             Returns the created customer instance.
             """
        user_data = validated_data.pop('user')
        user = UserProfileSerializer().create(user_data)
        customer = Customer.objects.create(user=user, **validated_data)
        return customer


# BankAccount Serializer
class BankAccountSerializer(serializers.ModelSerializer):
    """
    Serializer for BankAccount model.

    Handles the serialization of BankAccount instances,
    restricting access to 'id' and 'customer' fields to read-only.
    """

    class Meta:
        model = BankAccount
        fields = ['id', 'customer', 'balance', 'is_suspended']
        read_only_fields = ['id', 'customer', 'is_suspended']


# Currency Serializer
class CurrencySerializer(serializers.ModelSerializer):
    """
      Serializer for Currency model.

      Handles the serialization of Currency instances, including fields
      for currency code and exchange rate.
      """

    class Meta:
        model = Currency
        fields = ['id', 'code', 'exchange_rate']
        read_only_fields = ['id', 'code']

        # change rate is writeable to allow api to edit it daily for bonus task
        # help to log unusual hack attempts to the exchange rate
        def validate_exchange_rate(self, value):
            if value <= 0:
                raise serializers.ValidationError("Exchange rate must be positive.")
            if value > 100:
                raise serializers.ValidationError("Exchange rate seems unusually high.")
            return value


# Transaction Serializer
class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for Transaction model.

    Handles the serialization and validation of Transaction instances,
    including calculating transaction fees based on type and amount.
    """
    currency = serializers.PrimaryKeyRelatedField(queryset=Currency.objects.all())

    class Meta:
        model = Transaction
        fields = ['id', 'account', 'amount', 'transaction_type', 'fee', 'currency']
        read_only_fields = ['id']

    @staticmethod
    def validate_transaction_type(value):
        """
               Validate the transaction type.

               Ensures the transaction type is one of the allowed values
               (deposit, withdraw, or transfer). Raises a validation error if not.
               """
        if value not in ['deposit', 'withdraw', 'transfer']:
            raise serializers.ValidationError("Invalid transaction type.")
        return value

    def create(self, validated_data):
        """
             Create a new Transaction instance.

             Calculates the transaction fee based on the provided amount,
             updates the account based on the transaction type (deposit, withdraw,
             or transfer), and saves the transaction. Returns the created transaction.
             """
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
    """
      Serializer for Loan model.

      Handles the serialization and validation of Loan instances,
      including checks on loan amounts and bank fund availability.
      """

    class Meta:
        model = Loan
        fields = ['id', 'customer', 'amount', 'is_repaid']

    def create(self, validated_data):
        """
            Create a new Loan instance.

            Validates the requested loan amount and checks if the bank
            has sufficient funds. If valid, creates and returns the Loan instance.
            """
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
    """
      Serializer for handling deposit operations.

      Validates the deposit amount and currency, and creates
      corresponding Transaction instances.
      """
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField(max_length=3)

    @staticmethod
    def validate_currency(value):
        """
              Validate the currency code.

              Checks if the currency code exists in the Currency model.
              Raises a validation error if the currency is invalid.
              """
        if not Currency.objects.filter(code__iexact=value).exists():
            raise serializers.ValidationError("Invalid currency code.")
        return value

    def create(self, validated_data):
        """
        Create a new deposit transaction.

        Extracts the amount and currency, creates a Transaction instance
        for the deposit, and returns the created transaction.
        """
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
        """
        Update an existing deposit transaction.

        Allows modification of the deposit amount and currency,
        and saves the changes to the instance.
        """
        instance.amount = validated_data.get('amount', instance.amount)
        instance.currency = validated_data.get('currency', instance.currency)
        instance.save()
        return instance


# Deposit View


class DepositView(APIView):
    """
    View for handling deposit requests.

    Processes POST requests to create deposits on a specific bank account.
    """

    def post(self, request, account_id):
        """
        Handle a POST request for depositing into a bank account.

        Fetches the account based on account_id, validates the request data
        with DepositSerializer, and attempts to create a deposit.
        Returns success or error responses accordingly.
        """
        try:

            account = BankAccount.objects.get(id=account_id)
        except BankAccount.DoesNotExist:
            return Response({"error": "Account not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = DepositSerializer(data=request.data, context={'account': account})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Deposit successful."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
