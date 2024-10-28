from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from decimal import Decimal
from .models import UserProfile, Customer, BankAccount, Currency, Transaction, Loan, Bank
from .serializers import UserProfileSerializer, CustomerSerializer, BankAccountSerializer, CurrencySerializer, \
    TransactionSerializer, LoanSerializer


class UserProfileTests(TestCase):
    def setUp(self):
        self.user_data = {'email': 'test@example.com', 'name': 'Test User', 'password': 'testpassword'}
        self.user = UserProfile.objects.create_user(**self.user_data)

    def test_create_user(self):
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertTrue(self.user.check_password('testpassword'))

    def test_user_serializer(self):
        serializer = UserProfileSerializer(instance=self.user)
        self.assertEqual(serializer.data['email'], self.user_data['email'])


class CustomerTests(TestCase):
    def setUp(self):
        self.user = UserProfile.objects.create_user(email='customer@example.com', name='Customer Test',
                                                    password='password')
        self.customer = Customer.objects.create(user=self.user, phone='1234567890', address='Test Address')

    def test_customer_creation(self):
        self.assertEqual(self.customer.user.email, 'customer@example.com')
        self.assertEqual(self.customer.phone, '1234567890')

    def test_customer_serializer(self):
        serializer = CustomerSerializer(instance=self.customer)
        self.assertEqual(serializer.data['user']['email'], 'customer@example.com')


class BankAccountTests(TestCase):
    def setUp(self):
        self.user = UserProfile.objects.create_user(email='accountuser@example.com', name='Account User',
                                                    password='password')
        self.customer = Customer.objects.create(user=self.user, phone='1234567890', address='Test Address')
        self.account = BankAccount.objects.create(customer=self.customer, balance=100.00)

    def test_deposit(self):
        self.account.deposit(50)
        self.assertEqual(self.account.balance, 150.00)

    def test_withdraw(self):
        self.account.withdraw(30)
        self.assertEqual(self.account.balance, 70.00)

    def test_transfer(self):
        target_account = BankAccount.objects.create(customer=self.customer, balance=200.00)
        self.account.transfer(target_account, 50)
        self.assertEqual(self.account.balance, 50.00)
        self.assertEqual(target_account.balance, 250.00)

    def test_account_serializer(self):
        serializer = BankAccountSerializer(instance=self.account)
        self.assertEqual(serializer.data['balance'], '100.00')


class CurrencyTests(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code='USD', exchange_rate=3.5)

    def test_currency_creation(self):
        self.assertEqual(self.currency.code, 'USD')
        self.assertEqual(self.currency.exchange_rate, 3.5)

    def test_currency_serializer(self):
        serializer = CurrencySerializer(instance=self.currency)
        self.assertEqual(serializer.data['code'], 'USD')


class TransactionTests(TestCase):
    def setUp(self):
        self.user = UserProfile.objects.create_user(email='transuser@example.com', name='Trans User',
                                                    password='password')
        self.customer = Customer.objects.create(user=self.user, phone='1234567890', address='Test Address')
        self.account = BankAccount.objects.create(customer=self.customer, balance=100.00)
        self.currency = Currency.objects.create(code='USD', exchange_rate=3.5)
        self.transaction_data = {'account': self.account, 'amount': 20, 'transaction_type': 'deposit',
                                 'currency': self.currency}

    def test_transaction_creation(self):
        transaction = Transaction.objects.create(**self.transaction_data)
        self.assertEqual(transaction.amount, 20)
        self.assertEqual(transaction.transaction_type, 'deposit')

    def test_transaction_serializer(self):
        transaction = Transaction.objects.create(**self.transaction_data)
        serializer = TransactionSerializer(instance=transaction)
        self.assertEqual(serializer.data['amount'], '20.00')


class LoanTests(TestCase):
    def setUp(self):
        self.bank = Bank.objects.create(balance=100000.00)
        self.user = UserProfile.objects.create_user(email='loanuser@example.com', name='Loan User', password='password')
        self.customer = Customer.objects.create(user=self.user, phone='1234567890', address='Test Address')
        self.loan_data = {'customer': self.customer, 'amount': 5000}

    def test_loan_creation(self):
        loan = Loan.objects.create(**self.loan_data)
        self.assertEqual(loan.amount, 5000)
        self.assertFalse(loan.is_repaid)

    def test_loan_serializer(self):
        loan = Loan.objects.create(**self.loan_data)
        serializer = LoanSerializer(instance=loan)
        self.assertEqual(serializer.data['amount'], '5000.00')

    def test_grant_loan(self):
        loan = Loan.objects.create(**self.loan_data)
        self.bank.grant_loan(loan.amount)
        self.bank.refresh_from_db()
        self.assertEqual(self.bank.balance, 95000.00)


class BankAccountViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserProfile.objects.create_user(email='deposituser@example.com', name='Deposit User',
                                                    password='password')
        self.client.login(email='deposituser@example.com', password='password')
        self.customer = Customer.objects.create(user=self.user, phone='1234567890', address='Test Address')
        self.account = BankAccount.objects.create(customer=self.customer, balance=100.00)
        self.deposit_url = f'/api/accounts/{self.account.id}/deposit/'

    def test_deposit_successful(self):
        data = {'amount': Decimal('50.00')}
        response = self.client.post(self.deposit_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, Decimal('150.00'))

    def test_deposit_invalid_amount(self):
        data = {'amount': Decimal('-50.00')}
        response = self.client.post(self.deposit_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_deposit_suspended_account(self):
        self.account.is_suspended = True
        self.account.save()
        data = {'amount': Decimal('50.00')}
        response = self.client.post(self.deposit_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class LoanViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.bank = Bank.objects.create(balance=100000.00)
        self.user = UserProfile.objects.create_user(email='loanuser@example.com', name='Loan User', password='password')
        self.client.login(email='loanuser@example.com', password='password')
        self.customer = Customer.objects.create(user=self.user, phone='1234567890', address='Test Address')
        self.loan_data = {'customer': self.customer.id, 'amount': 5000}
        self.loan_url = '/api/loans/'

    def test_create_loan_successful(self):
        response = self.client.post(self.loan_url, self.loan_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['amount'], '5000.00')

    def test_create_loan_insufficient_bank_funds(self):
        self.bank.balance = 1000  # Set bank balance lower than loan amount
        self.bank.save()
        response = self.client.post(self.loan_url, self.loan_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_loan_repayment_invalid_amount(self):
        # Create a loan for the customer first with valid fields
        loan = Loan.objects.create(customer=self.customer, amount=3000)  # Adjust based on your model
        repayment_url = f'/api/loans/{loan.id}/repay/'
        data = {'repayment_amount': 6000}  # More than the loan amount

        # Make the request to repay the loan
        response = self.client.post(repayment_url, data, format='json')

        # Check that the response is a bad request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)  # Ensure that an error key exists in the response

    def test_loan_repayment_successful(self):
        # Create a loan for the customer first, ensuring that self.loan_data does not include 'customer'
        self.loan_data = {'amount': 3000}  # Adjust according to your Loan model fields
        loan = Loan.objects.create(customer=self.customer, **self.loan_data)  # This should work now

        repayment_url = f'/api/loans/{loan.id}/repay/'
        data = {'repayment_amount': 1000}  # A valid repayment amount

        # Make the request to repay the loan
        response = self.client.post(repayment_url, data, format='json')

        # Check that the response is successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Optionally, check if the loan balance is updated correctly
        loan.refresh_from_db()  # Refresh the loan object from the database
        self.assertEqual(loan.remaining_balance, 2000)  # Adjust based on your Loan model's logic

    def test_get_customer_loans(self):
        # Create the customer first if not already created
        self.customer = Customer.objects.create(user=self.user, phone='1234567890', address='Test Address')

        # Create loans for the customer
        Loan.objects.create(customer=self.customer, amount=3000)
        Loan.objects.create(customer=self.customer, amount=2000)

        loans_url = f'/api/loans/customer/{self.customer.id}/'
        response = self.client.get(loans_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Check if two loans are returned

    def test_get_loan_details(self):
        # Create a loan for the customer first
        loan = Loan.objects.create(customer=self.customer, amount=3000)
        loan_url = f'/api/loans/{loan.id}/'

        response = self.client.get(loan_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['amount'], '3000.00')

    def test_loan_not_found(self):
        loan_id = 9999  # Assuming this ID does not exist
        loan_url = f'/api/loans/{loan_id}/'

        response = self.client.get(loan_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_loan(self):
        # Create a loan first
        loan = Loan.objects.create(customer=self.customer, amount=3000)
        loan_url = f'/api/loans/{loan.id}/'
        data = {'amount': 4000}  # Update the loan amount

        response = self.client.patch(loan_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        loan.refresh_from_db()
        self.assertEqual(loan.amount, 4000)

    def test_delete_loan(self):
        # Create a loan first
        loan = Loan.objects.create(customer=self.customer, amount=3000)
        loan_url = f'/api/loans/{loan.id}/'

        response = self.client.delete(loan_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Loan.objects.filter(id=loan.id).exists())


def test_get_customer_loans(self):
    # Create the customer first if not already created
    self.customer = Customer.objects.create(name='Test Customer')  # Create a test customer

    # Create loans for the customer
    Loan.objects.create(customer=self.customer, amount=3000)
    Loan.objects.create(customer=self.customer, amount=2000)
    # Loan.objects.create(customer=self.customer, amount=3000, interest_rate=5, duration=12)
    # Loan.objects.create(customer=self.customer, amount=2000, interest_rate=5, duration=12)

    loans_url = f'/api/loans/customer/{self.customer.id}/'
    response = self.client.get(loans_url)

    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(len(response.data), 2)  # Check if two loans are returned
