# Balanced Scorecard (BSC) Generator

A Django-based open-source web application for generating and managing Balanced Scorecards for multiple organizations. Supports user registration with role-based access control (RBAC) for Admins and Employees, and organization-specific dashboards.

## Features
- User registration with email, username, password, role (Admin/Employee), and organization/company name
- Secure authentication and login
- Role-based dashboard: Admins have full control, Employees have view-only access
- Organization-specific data separation
- PostgreSQL database support

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

## License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details. 