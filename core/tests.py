# core/tests.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import UserProfile, Customer, BankAccount, Loan


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
        self.user_data = {
            'email': 'bankaccount@example.com',
            'username': 'bankaccountuser',
            'name': 'Bank Account User',
            'password': 'bankaccountpassword',
        }
        self.user = UserProfile.objects.create_user(**self.user_data)
        self.customer = Customer.objects.create(user=self.user, phone='1234567890', address='123 Main St')
        self.account_data = {
            'customer': self.customer.id,
            'balance': 1000.00,
            'is_suspended': False
        }
        self.account_url = reverse('bankaccount-list')  # Adjust the URL name if needed

    def test_create_bank_account(self):
        response = self.client.post(self.account_url, self.account_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BankAccount.objects.count(), 1)

    def test_bank_account_deposit(self):
        account = BankAccount.objects.create(customer=self.customer, balance=1000, is_suspended=False)
        deposit_data = {
            'amount': 500,
            'currency': None  # Set as needed
        }
        response = self.client.post(reverse('bankaccount-deposit', args=[account.id]), deposit_data)  # Adjust as needed
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        account.refresh_from_db()
        self.assertEqual(account.balance, 1500.00)

    def test_bank_account_withdraw(self):
        account = BankAccount.objects.create(customer=self.customer, balance=1000, is_suspended=False)
        withdraw_data = {
            'amount': 500,
            'currency': None  # Set as needed
        }
        response = self.client.post(reverse('bankaccount-withdraw', args=[account.id]),
                                    withdraw_data)  # Adjust as needed
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        account.refresh_from_db()
        self.assertEqual(account.balance, 500.00)


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
