# You can use this page as a quick reference for testing your API endpoints.
### Accessible Routes for the Banking API

#### Admin Interface
- **Django Admin Panel**:  
  `/admin/`

#### API Endpoints

1. **Customers**
   - **List/Create Customers**:  
     `/api/customers/`
   - **Retrieve/Update/Delete a Customer by ID**:  
     `/api/customers/<id>/`

2. **Bank Accounts**
   - **List/Create Bank Accounts**:  
     `/api/accounts/`
   - **Retrieve/Update/Delete a Bank Account by ID**:  
     `/api/accounts/<id>/`

3. **Transactions**
   - **List/Create Transactions**:  
     `/api/transactions/`
   - **Retrieve/Update/Delete a Transaction by ID**:  
     `/api/transactions/<id>/`

4. **Loans**
   - **List/Create Loans**:  
     `/api/loans/`
   - **Retrieve/Update/Delete a Loan by ID**:  
     `/api/loans/<id>/`

5. **Loan Repayment**
   - **Create a Loan Repayment for a Loan by ID**:  
     `/api/loans/<loan_id>/repay/`

#### API Documentation
- **Swagger UI**:  
  `/swagger/`
- **ReDoc**:  
  `/redoc/`

### Notes
- Replace `<id>` and `<loan_id>` with the actual identifiers of the resources you want to interact with.
- Ensure your Django development server is running to access these endpoints:
  ```bash
  python3 manage.py runserver
  ``` 

