# ContractVault - Contract Lifecycle Management System

A production-grade contract lifecycle management platform with contract creation from templates, e-signature workflows, version tracking, approval chains, expiration alerts, compliance tracking, and contract analytics.

## Tech Stack

- **Backend:** Django 5.x + Django REST Framework
- **Frontend:** React 18 with Redux Toolkit
- **Database:** PostgreSQL 16
- **Cache/Broker:** Redis 7
- **Task Queue:** Celery 5
- **Reverse Proxy:** Nginx
- **Containerization:** Docker & Docker Compose

## Features

- **Contract Management:** Full CRUD with version history, clause management, and party tracking
- **Template Engine:** Create reusable contract templates with customizable fields and clauses
- **Approval Workflows:** Multi-step approval chains with role-based routing and escalation
- **E-Signatures:** Built-in signature capture with audit trails and tamper detection via SHA-256 hashing
- **Expiration Alerts:** Automated notifications for upcoming contract expirations via Celery beat
- **Compliance Tracking:** Track compliance requirements and generate compliance reports
- **Analytics Dashboard:** Contract statistics, value tracking, renewal rates, and trend analysis
- **Role-Based Access:** Organization-level multi-tenancy with granular role permissions
- **PDF Generation:** Automated PDF contract generation from templates using ReportLab
- **Notifications:** Email and in-app notifications for all contract lifecycle events

## Architecture

```
Client (React SPA)
    |
    v
Nginx (reverse proxy, static files)
    |
    v
Django / DRF (REST API)
    |
    +---> PostgreSQL (persistent data)
    +---> Redis (cache + Celery broker)
    +---> Celery Worker (async tasks)
    +---> Celery Beat (scheduled tasks)
```

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd ContractVault
   ```

2. Copy environment variables:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` with your settings (generate a new SECRET_KEY, set email credentials, etc.)

4. Build and start all services:
   ```bash
   docker compose up --build -d
   ```

5. Run database migrations:
   ```bash
   docker compose exec backend python manage.py migrate
   ```

6. Create a superuser:
   ```bash
   docker compose exec backend python manage.py createsuperuser
   ```

7. Access the application:
   - Frontend: http://localhost
   - API: http://localhost/api/
   - Admin: http://localhost/api/admin/

## Development

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend Development

```bash
cd frontend
npm install
npm start
```

### Running Celery Workers

```bash
cd backend
celery -A config worker -l info
celery -A config beat -l info
```

## API Endpoints

| Endpoint                          | Method | Description                    |
|-----------------------------------|--------|--------------------------------|
| `/api/auth/login/`               | POST   | Obtain JWT token pair          |
| `/api/auth/register/`            | POST   | Register new user              |
| `/api/auth/refresh/`             | POST   | Refresh access token           |
| `/api/contracts/`                | GET    | List contracts                 |
| `/api/contracts/`                | POST   | Create contract                |
| `/api/contracts/{id}/`           | GET    | Contract detail                |
| `/api/contracts/{id}/versions/`  | GET    | Version history                |
| `/api/contracts/{id}/submit/`    | POST   | Submit for approval            |
| `/api/templates/`                | GET    | List templates                 |
| `/api/templates/{id}/generate/`  | POST   | Generate contract from template|
| `/api/approvals/`                | GET    | List approval requests         |
| `/api/approvals/{id}/approve/`   | POST   | Approve a request              |
| `/api/approvals/{id}/reject/`    | POST   | Reject a request               |
| `/api/signatures/requests/`      | GET    | List signature requests        |
| `/api/signatures/sign/{id}/`     | POST   | Sign a contract                |
| `/api/analytics/dashboard/`      | GET    | Dashboard statistics           |
| `/api/analytics/reports/`        | GET    | Generate reports               |

## Environment Variables

See `.env.example` for the full list of configurable environment variables.

## Testing

```bash
# Backend tests
docker compose exec backend python manage.py test

# Frontend tests
docker compose exec frontend npm test
```

## License

Proprietary - All rights reserved.
