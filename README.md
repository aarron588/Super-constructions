# Super-constructions

Construction operations platform built with **Django + SQLite**.

## Scope covered
- Billing and invoices (including estimate mode, tax, payments, due reminders, PDF export)
- Attendance tracking (check-in/check-out, correction, approval, monthly lock)
- Employee/project/client/expense management
- Attendance-to-billing linkage
- Dashboard and summary reports
- Role-based access: `admin`, `accountant`, `site_manager`, `worker`
- Audit logging for key business actions

## Tech stack
- Backend: Django 6.1.1
- Database: SQLite (default)
- Auth: Django session authentication (password hashing built-in)

## Quick start
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
3. Start the server:
   ```bash
   python manage.py runserver
   ```

## API overview
All APIs are under `/api/`.

### Auth
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`

### Core entities
- `GET/POST /api/employees`
- `GET/POST /api/clients`
- `GET/POST /api/projects`
- `GET/POST /api/expenses`

### Attendance
- `GET/POST /api/attendance`
- `POST /api/attendance/<id>/check-out`
- `POST /api/attendance/<id>/correct`
- `POST /api/attendance/<id>/approve`
- `POST /api/attendance/lock`

### Billing
- `GET/POST /api/invoices`
- `POST /api/invoices/generate-from-attendance`
- `POST /api/invoices/<id>/items`
- `POST /api/invoices/<id>/send`
- `POST /api/invoices/<id>/payments`
- `GET /api/invoices/<id>/pdf`
- `GET /api/invoices/reminders`

### Reporting
- `GET /api/dashboard`
- `GET /api/reports/summary`

## Deployment and operations plan
- Use **staging** and **production** environments.
- Set environment variables: `DJANGO_SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`.
- Put app behind HTTPS reverse proxy.
- Enable centralized monitoring and error logging.
- Back up SQLite or move to managed PostgreSQL in production.
- Run a parallel manual process for one billing cycle before full rollout.

## Validation
Run tests:
```bash
python manage.py test
```
