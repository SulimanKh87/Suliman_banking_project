# core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin, Group, Permission
from django.core.exceptions import ValidationError


# Custom User Manager
class UserProfileManager(BaseUserManager):
    def create_user(self, email, name, password=None):
        if not email:
            raise ValueError("Email must be provided")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name)
        # encryption
        user.set_password(password)
        # save to database
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password):
        user = self.create_user(email, name, password)
        user.is_superuser = True
        user.is_staff = True
        # save again after superuser modification were added
        user.save(using=self._db)
        return user


# Custom User Model
class UserProfile(AbstractUser, PermissionsMixin):
    email = models.EmailField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    objects = UserProfileManager()

    # Override related fields to avoid clashes
    groups = models.ManyToManyField(
        Group,
        related_name='user_profiles',
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='user_profiles_permissions',
        blank=True,
    )

    def __str__(self):
        return "Email = {}, Name = {}".format(self.email, self.name)


class Customer(models.Model):
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.user.email}"


class Currency(models.Model):
    code = models.CharField(max_length=3, unique=True)  # E.g., 'USD', 'EUR'
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4)  # Rate against NIS

    def __str__(self):
        return self.code


class BankAccount(models.Model):
    id = models.AutoField(primary_key=True)  # Explicitly define the id field (optional)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_suspended = models.BooleanField(default=False)

    def close(self):
        if self.balance < 0:
            raise ValidationError("Cannot close account with negative balance.")
        self.is_suspended = True
        self.save()

    def deposit(self, amount, currency=None):
        if self.is_suspended:
            raise ValidationError("Account is suspended.")
        if amount <= 0:
            raise ValidationError("Deposit amount must be positive.")
        if currency:
            if not isinstance(currency, Currency):
                raise ValidationError("Invalid currency provided.")
            # Convert the amount based on currency exchange rate
            amount *= currency.exchange_rate
        self.balance += amount
        self.save()

    def withdraw(self, amount, currency=None):
        if currency:
            if not isinstance(currency, Currency):
                raise ValidationError("Invalid currency provided.")
            amount *= currency.exchange_rate
        if self.balance - amount < -1000:  # Example limit for negative balance
            raise ValidationError("Insufficient funds or exceeds overdraft limit.")
        self.balance -= amount
        self.save()

    def transfer(self, to_account, amount, currency=None):
        self.withdraw(amount, currency)
        to_account.deposit(amount, currency)

    def get_balance(self):
        return self.balance

    def __str__(self):
        return f"Account {self.id} - {self.customer.user.email}"


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdraw', 'Withdraw'),
        ('transfer', 'Transfer'),
    ]
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    fee = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    fee_percentage = 0.02

    def save(self, *args, **kwargs):
        if self.transaction_type in ['withdraw', 'transfer']:
            self.fee = self.amount * self.fee_percentage
            self.amount -= self.fee  # Adjust amount for fee
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_type.capitalize()} - {self.amount}"


class Loan(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_repaid = models.BooleanField(default=False)

    def clean(self):
        if self.amount > 50000:
            raise ValidationError("Maximum loan is 50,000 NIS")
        if self.amount <= 0:
            raise ValidationError("Loan amount must be positive.")

    def repay(self, repayment_amount):
        if repayment_amount <= 0:
            raise ValidationError("Repayment amount must be positive.")
        if repayment_amount > self.amount:
            raise ValidationError("Repayment amount cannot exceed loan amount.")
        self.amount -= repayment_amount
        if self.amount <= 0:
            self.is_repaid = True
        self.save()

    def get_loans(self):
        return Loan.objects.filter(customer=self)

    def __str__(self):
        return f"Loan of {self.amount} to {self.customer.user.email}"


class Bank(models.Model):
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=10000000)  # Starting balance for the bank

    def grant_loan(self, loan_amount):
        if self.balance - loan_amount < 0:
            raise ValidationError("Bank does not have enough funds for this loan.")
        self.balance -= loan_amount
        self.save()

    def __str__(self):
        return f"Bank Balance: {self.balance}"
