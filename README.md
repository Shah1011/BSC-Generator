# Balanced Scorecard (BSC) Generator

A Django-based open-source web application for generating and managing Balanced Scorecards for multiple organizations. This system helps organizations track their performance across four key perspectives: Financial, Customer, Internal Process, and Learning & Growth.

## What is a Balanced Scorecard?

The Balanced Scorecard is a strategic planning and management system that organizations use to:
- Communicate what they are trying to accomplish
- Align day-to-day work with strategy
- Prioritize projects, products, and services
- Measure and monitor progress towards strategic targets

## Project Workflow

### 1. User Registration & Authentication
- **Admin Registration**: Organization leaders register as admins with full system access
- **Employee Management**: Admins can create employee accounts with view-only permissions
- **Organization Isolation**: Each organization's data is completely separated

### 2. BSC Data Management
- **File Upload**: Admins upload CSV/Excel files containing BSC metrics
- **Four Perspectives**: Data is automatically categorized into Financial, Customer, Internal, and Learning & Growth perspectives
- **Batch Processing**: Each upload creates a batch for easy tracking and management
- **Real-time Status**: System calculates performance status (Good/Moderate/Bad) based on target vs actual values

### 3. Dashboard & Visualization
- **Interactive Dashboard**: View all BSC data organized by batches and perspectives
- **Performance Tracking**: Visual indicators show whether targets are being met
- **Batch Management**: Edit, rename, or delete entire batches of data
- **Export Capabilities**: Generate reports and export data for further analysis

### 4. User Management
- **Role-based Access**: Admins have full CRUD operations, employees have read-only access
- **Profile Management**: Users can update their profiles and change passwords
- **Organization Management**: Complete separation of data between different organizations

## Features
- **Multi-organization Support**: Complete data isolation between organizations
- **Role-based Access Control (RBAC)**: Admin and Employee roles with different permissions
- **File Upload Processing**: Support for CSV and Excel file formats
- **Batch Data Management**: Group related BSC entries for easier management
- **Performance Status Calculation**: Automatic calculation of performance indicators
- **Responsive Design**: Works on desktop and mobile devices
- **Secure Authentication**: Password validation and secure login system
- **Data Export**: Export BSC data in various formats
- **User Profile Management**: Complete user account management system

## Setup Instructions

### 1. Clone the repository
```sh
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git
cd bsc_generator
```

### 2. Create and activate a virtual environment
```sh
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```sh
pip install -r requirements.txt
```

### 4. Configure environment variables (optional)
- You can use a `.env` file for sensitive settings (e.g., secret key, database credentials).

### 5. Configure PostgreSQL database
- Update `bsc_gen/settings.py` with your PostgreSQL credentials:
  ```python
  DATABASES = {
      'default': {
          'ENGINE': 'django.db.backends.postgresql',
          'NAME': 'your_db_name',
          'USER': 'your_db_user',
          'PASSWORD': 'your_db_password',
          'HOST': 'localhost',
          'PORT': '5432',
      }
  }
  ```

### 6. Run migrations
```sh
python manage.py migrate
```

### 7. Start the development server
```sh
python manage.py runserver
```

## Usage
- Register as an Admin or Employee for your organization.
- Admins have full dashboard control; Employees have view-only access.
- All authentication and organization data is stored in PostgreSQL.

## Known Issues & Bugs

### Security Issues
1. **Admin Password Verification** - Admin password transmitted in plain text via POST in delete_bsc_data function
2. **Missing Rate Limiting** - No rate limiting on password reset attempts

### Data Integrity Issues
3. **Batch ID Generation** - Complex batch ID generation could fail with concurrent uploads
4. **Date Parsing Vulnerabilities** - Multiple date format attempts without proper error handling
5. **Missing Organization Validation** - Potential cross-organization data access if filtering fails

### UI/UX Issues
6. **Static File Dependencies** - Templates reference static files that may not exist:
   - `{% static 'assets/abstract.jpg' %}`
   - `{% static 'css/tailwind.build.css' %}`
7. **Error Message Inconsistency** - Mixed use of messages.error() and JSON errors

### Performance Issues
8. **Inefficient Database Queries** - Multiple separate queries instead of using unions
9. **Large File Upload Handling** - No file size limits for CSV/Excel uploads

### Minor Issues
10. **Hardcoded Values** - Password length minimum hardcoded to 6 characters
11. **Missing Validation** - No validation for numeric fields in target/actual values

### Notes
- Password reset functionality is implemented and working
- All URL patterns are properly configured
- Application is fully functional with all core features working

## Contributing
We welcome contributions! Please feel free to submit issues and pull requests to help improve the BSC Generator.

## License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details. 