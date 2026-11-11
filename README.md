# Equipment Resource Manager API

A Django REST API for managing shared equipment and reserving finite inventory.
Reservations use half-open time ranges (`start_at <= t < end_at`), so one booking
may start when another ends. Database transactions lock each resource while
validating and writing bookings, preventing concurrent requests from reserving
more units than exist. **MySQL is the only supported database.**

## Requirements and setup

- Python 3.12 or newer
- MySQL 8.0.16+ (InnoDB tables) and the system libraries needed to build `mysqlclient`

Create a MySQL database and user, then configure the environment using
`.env.example` as a reference (Django does not load `.env` files automatically):

```powershell
$env:MYSQL_DATABASE = "equipment_manager"
$env:MYSQL_USER = "equipment_manager"
$env:MYSQL_PASSWORD = ""
$env:MYSQL_HOST = "127.0.0.1"
$env:MYSQL_PORT = "3306"
$env:DJANGO_SECRET_KEY = ""
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The custom user role is `member`, `manager`, or `admin`. New registrations are
always members; privileged roles are assigned by a Django admin/superuser.
Superusers are treated as administrators regardless of their stored role.

## Authentication and permissions

Get a DRF token with `POST /api/auth/token/` and JSON `{"username":"…",
"password":"…"}`. Send it on subsequent requests as
`Authorization: Token <key>`. Registration is `POST /api/auth/register/`;
`GET /api/auth/me/` returns the authenticated profile.

- Any authenticated user can view active resources and create/read/update their
  own bookings. Booking lists are scoped to the current user.
- Managers and administrators can create, edit, and delete resources, and view
  inactive resources and manage all bookings.
- Resources with booking history cannot be deleted; deactivate them instead.
- `DELETE /api/bookings/{id}/` soft-cancels a booking; canceled reservations do
  not consume inventory. A user cannot read or cancel someone else's booking.
- A booking's resource and status cannot be changed after creation. Its dates
  and quantity can be updated while availability is revalidated.

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/auth/register/` | Create a member account |
| `POST` | `/api/auth/token/` | Obtain an authentication token |
| `GET` | `/api/auth/me/` | Get current user and role |
| `GET` | `/api/resources/` | List active resources |
| `GET` | `/api/resources/{id}/` | View a resource |
| `POST`, `PUT`, `PATCH`, `DELETE` | `/api/resources/{id}/` | Manager/admin resource management |
| `GET`, `POST` | `/api/bookings/` | List visible bookings or reserve inventory |
| `GET`, `PUT`, `PATCH`, `DELETE` | `/api/bookings/{id}/` | View/update/cancel a booking |

Booking input includes `resource` (resource ID), ISO-8601 `start_at` and
`end_at`, and positive integer `quantity`. Responses include resource/user
names and timestamps. Collection endpoints use page-number pagination.

## Validation

Tests use the configured MySQL database and require a working MySQL server:

```powershell
python manage.py test
python manage.py check
```

The test runner uses the configured MySQL database.
