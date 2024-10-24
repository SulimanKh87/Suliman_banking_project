# core/tests.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import UserProfile, Customer, BankAccount, Currency, Loan
from rest_framework.authtoken.models import Token


class UserProfileTests(APITestCase):
    def setUp(self):
        self.user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'name': 'Test User',
            'password': 'testpassword',
        }
        self.user = UserProfile.objects.create_user(**self.user_data)

    def test_user_creation(self):
        self.assertEqual(self.user.email, self.user_data['email'])
        self.assertEqual(self.user.username, self.user_data['username'])
        self.assertTrue(self.user.check_password(self.user_data['password']))


class CustomerTests(APITestCase):
    def setUp(self):
        self.user_data = {
            'email': 'customer@example.com',
            'username': 'customer',
            'name': 'Customer User',
            'password': 'customerpassword',
        }
        self.user = UserProfile.objects.create_user(**self.user_data)
        self.customer_data = {
            'user': {
                'email': self.user.email,
                'username': self.user.username,
                'name': self.user.name,
                'password': self.user_data['password']
            },
            'phone': '1234567890',
            'address': '123 Main St'
        }
        self.customer_url = reverse('customer-list')  # Adjust the URL name if needed

    def test_create_customer(self):
        response = self.client.post(self.customer_url, self.customer_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(Customer.objects.get().phone, self.customer_data['phone'])

    def test_customer_update(self):
        customer = Customer.objects.create(user=self.user, phone='1234567890', address='123 Main St')
        update_data = {
            'phone': '0987654321',
            'address': '456 Side St'
        }
        response = self.client.patch(reverse('customer-detail', args=[customer.id]), update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        customer.refresh_from_db()
        self.assertEqual(customer.phone, update_data['phone'])


class BankAccountTests(APITestCase):
    def setUp(self):
        # Create a currency entry for testing
        self.currency = Currency.objects.create(code='USD', exchange_rate=1.0)

        # Create a user
        self.user_data = {
            'email': 'bankaccount@example.com',
            'username': 'bankaccountuser',
            'name': 'Bank Account User',
            'password': 'bankaccountpassword',
        }
        # self.user = UserProfile.objects.create_user(**self.user_data)
        self.user = UserProfile.objects.create_user(**self.user_data)

        # Obtain a token for the user
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        # Create a customer
        self.customer = Customer.objects.create(user=self.user, phone='1234567890', address='123 Main St')

        # Create a bank account
        self.account = BankAccount.objects.create(customer=self.customer, balance=1000.00, is_suspended=False)
        self.account_url = reverse('bankaccount-list')  # Adjust the URL name if needed

    def test_create_bank_account(self):
        new_account_data = {
            'customer': self.customer.id,
            'balance': 1000.00,
            'is_suspended': False
        }
        response = self.client.post(self.account_url, new_account_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BankAccount.objects.count(), 2)  # One from setUp + one created here
        account = BankAccount.objects.last()
        self.assertEqual(account.customer, self.customer)
        self.assertEqual(account.balance, 1000.00)

    def test_bank_account_withdraw(self):
        withdraw_data = {
            'amount': 500,
            'currency': 'USD'  # Ensure the currency exists
        }
        response = self.client.post(reverse('bankaccount-withdraw', args=[self.account.id]), withdraw_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, 500.00)

        # Attempt to withdraw more than the balance
        withdraw_data['amount'] = 600
        response = self.client.post(reverse('bankaccount-withdraw', args=[self.account.id]), withdraw_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)  # Expecting a validation error

    def test_bank_account_deposit(self):
        deposit_data = {
            'amount': 500,
            'currency': 'USD'  # Make sure the currency is valid
        }

        # Make the deposit request to the correct URL
        response = self.client.post(reverse('bankaccount-deposit', args=[self.account.id]), deposit_data)

        # Assert the response status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh the account from the database and check the balance
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, 1500.00)  # Check if the balance is updated correctly

    def test_unauthenticated_user_deposit(self):
        # Remove the authorization header
        self.client.credentials()  # Reset credentials to simulate unauthenticated state

        deposit_data = {'amount': 500, 'currency': 'USD'}

        # Attempt deposit without logging in
        response = self.client.post(reverse('bankaccount-deposit', args=[self.account.id]), deposit_data)

        # Assert that the response status code indicates permission denied
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_deposit(self):
        deposit_data = {'amount': 500, 'currency': 'USD'}

        # Make the deposit request to the correct URL
        response = self.client.post(reverse('bankaccount-deposit', args=[self.account.id]), deposit_data)

        # Assert the response status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh the account from the database and check the balance
        self.account.refresh_from_db()
        self.assertEqual(self.account.balance, 1500.00)  # Check if the balance is updated correctly

    def test_unauthorized_user_deposit(self):
        # Create another user and bank account
        other_user = UserProfile.objects.create_user(email='other@example.com', password='password')
        other_customer = Customer.objects.create(user=other_user, phone='987654321', address='Other Address')
        other_account = BankAccount.objects.create(customer=other_customer, balance=1000, is_suspended=False)

        # Attempt to deposit into another user's account without logging in
        deposit_data = {'amount': 500, 'currency': 'USD'}
        response = self.client.post(reverse('bankaccount-deposit', args=[other_account.id]), deposit_data)

        # Assert that the response status code indicates permission denied
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class LoanTests(APITestCase):
    def setUp(self):
        self.user_data = {
            'email': 'loanuser@example.com',
            'username': 'loanuser',
            'name': 'Loan User',
            'password': 'loanpassword',
        }
        self.user = UserProfile.objects.create_user(**self.user_data)
        self.customer = Customer.objects.create(user=self.user, phone='1234567890', address='123 Main St')
        self.loan_data = {
            'customer': self.customer.id,
            'amount': 20000,
            'is_repaid': False
        }
        self.loan_url = reverse('loan-list')  # Adjust the URL name if needed

    def test_create_loan(self):
        response = self.client.post(self.loan_url, self.loan_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Loan.objects.count(), 1)

    def test_loan_repayment(self):
        loan = Loan.objects.create(customer=self.customer, amount=20000, is_repaid=False)
        repayment_data = {
            'repayment_amount': 5000
        }
        response = self.client.post(reverse('loan-repay', args=[loan.id]), repayment_data)  # Adjust as needed
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        loan.refresh_from_db()
        self.assertEqual(loan.amount, 15000)
