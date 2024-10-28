# core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin, Group, Permission
from django.core.exceptions import ValidationError

""" 
Custom User Manager
Manages user creation, including normalizing emails and password hashing.
"""


class UserProfileManager(BaseUserManager):
    """
      Create a regular user with an email, name, and password.
      Raises ValueError if email is not provided.
      """

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
        """
          Create a superuser with specific permissions.
          """
        user = self.create_user(email, name, password)
        user.is_superuser = True
        user.is_staff = True
        # save again after superuser modification were added
        user.save(using=self._db)
        return user


""" 
Custom User Model
Extends AbstractUser to create a custom user profile with additional fields.
"""


class UserProfile(AbstractUser, PermissionsMixin):
    """
    Custom User Model
    Extends AbstractUser to create a custom user profile with additional fields.
    """
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
    """
    Customer Model
    Represents a customer profile linked to a UserProfile.
    """
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.user.email}"


class Currency(models.Model):
    """
    Currency Model
    Represents a currency type with its exchange rate against NIS.
    """
    code = models.CharField(max_length=3, unique=True)  # E.g., 'USD', 'EUR'
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=4)  # Rate against NIS

    def __str__(self):
        return self.code


class BankAccount(models.Model):
    """
    BankAccount Model
    Represents a bank account linked to a customer.
    """
    id = models.AutoField(primary_key=True)  # Explicitly define the id field (optional)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_suspended = models.BooleanField(default=False)

    """
            Close the account if the balance is not negative.
            """

    def close(self):
        if self.balance < 0:
            raise ValidationError("Cannot close account with negative balance.")
        self.is_suspended = True
        self.save()

    """ 
    Deposit an amount into the account, adjusting for currency if provided.
    Raises ValidationError for various error conditions.
    """

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

    """ 
    Withdraw an amount from the account, adjusting for currency if provided.
    Raises ValidationError for insufficient funds or invalid conditions.
    """

    def withdraw(self, amount, currency=None):
        if currency:
            if not isinstance(currency, Currency):
                raise ValidationError("Invalid currency provided.")
            amount *= currency.exchange_rate
        if self.balance - amount < -1000:  # Example limit for negative balance
            raise ValidationError("Insufficient funds or exceeds overdraft limit.")
        self.balance -= amount
        self.save()

    """ 
    Transfer an amount to another bank account.
    """

    def transfer(self, to_account, amount, currency=None):
        self.withdraw(amount, currency)
        to_account.deposit(amount, currency)

    """ 
    Get the current balance of the account.
    """

    def get_balance(self):
        return self.balance

    def __str__(self):
        return f"Account {self.id} - {self.customer.user.email}"


""" 
Transaction Model
Represents a financial transaction related to a bank account.
"""


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
    """ 
    Override save method to calculate fees for withdraw and transfer transactions.
    """

    def save(self, *args, **kwargs):
        if self.transaction_type in ['withdraw', 'transfer']:
            self.fee = self.amount * self.fee_percentage
            self.amount -= self.fee  # Adjust amount for fee
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_type.capitalize()} - {self.amount}"


""" 
Loan Model
Represents a loan issued to a customer.
"""


class Loan(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Total loan amount
    repaid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Amount repaid
    is_repaid = models.BooleanField(default=False)  # Repayment status
    # duration = models.IntegerField()  # Duration in months
    # interest_rate = models.DecimalField(max_digits=5, decimal_places=2)  # Interest rate

    @property
    def remaining_balance(self):
        return self.amount - self.repaid_amount  # Correct remaining balance calculation

    """ 
    Clean method to enforce loan constraints.
    """

    def clean(self):
        if self.amount > 50000:
            raise ValidationError("Maximum loan is 50,000 NIS")
        if self.amount <= 0:
            raise ValidationError("Loan amount must be positive.")
        # if self.duration <= 0:
        #     raise ValidationError("Loan duration must be positive.")
        # if self.interest_rate < 0:
        #     raise ValidationError("Interest rate cannot be negative.")

    """ 
    Repay part of the loan.
    """

    def repay(self, repayment_amount):
        if repayment_amount <= 0:
            raise ValidationError("Repayment amount must be positive.")
        if repayment_amount > self.remaining_balance:  # Check against remaining balance
            raise ValidationError("Repayment amount cannot exceed remaining balance.")

        self.repaid_amount += repayment_amount  # Update repaid amount

        if self.remaining_balance <= 0:  # If fully repaid
            self.is_repaid = True

        self.save()

    """ 
    Get all loans for the customer.
    """

    def get_loans(self):
        return Loan.objects.filter(customer=self)

    def __str__(self):
        return f"Loan of {self.amount} to {self.customer.user.email}"


""" 
Bank Model
Represents the bank's finances.
"""


class Bank(models.Model):
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=10000000)  # Starting balance for the bank
    """ 
    Grant a loan from the bank's balance.
    Raises ValidationError if insufficient funds.
    """

    def grant_loan(self, loan_amount):
        if self.balance - loan_amount < 0:
            raise ValidationError("Bank does not have enough funds for this loan.")
        self.balance -= loan_amount
        self.save()

    def __str__(self):
        return f"Bank Balance: {self.balance}"
