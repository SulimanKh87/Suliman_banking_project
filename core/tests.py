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
