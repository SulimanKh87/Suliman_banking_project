# Django Banking System

## Overview
This is a banking management system built using Django. It provides features for user management, bank account operations, loan management, and more.

## Features
- User Management (Create, Update, Delete)
- Bank Account Operations (Create, Suspend, Close)
- Transaction Management (Deposit, Withdraw, Transfer)
- Loan Management (Grant Loan, Loan Repayment)
- Authentication for Customer Profiles

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/SulimanKh87/Suliman_banking_project.git
2. Create virtualenv name_of_venv
python3 -m venv suliman_venv
3. Activate venv
source suliman_venv/bin/activate
# if you need to deactivate the venv: bash command - type: 
deactivate 
## Install dependencies: 
4. Install dependencies:   
   cd suliman_banking_project3
   pip install -r requirements.txt
# or
# run the following commands, may require to run this commands in IDE such as pycharm as well as on ubuntu/linux bash command menu
pip install asgiref==3.8.1
pip install Django==5.1.2
pip install djangorestframework==3.15.2
pip install drf-yasg==1.21.8
pip install inflection==0.5.1
pip install packaging==24.1
pip install pip==22.0.2
pip install pytz==2024.2
pip install PyYAML==6.0.2
pip install setuptools==59.6.0
pip install sqlparse==0.5.1
pip install typing_extensions==4.12.2
pip install uritemplate==4.1.1
pip install --upgrade drf-yasg
# after installation, you can verify that the correct versions are installed by running:
# pip list
