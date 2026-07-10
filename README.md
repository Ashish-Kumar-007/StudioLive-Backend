# 🎬 StudioLive Backend

Production-Grade FastAPI + PostgreSQL Modular Monolith backend for a Photography Studio Quick-Commerce Platform. Designed for high availability, double-booking prevention, secure digital delivery, and seamless checkout.

---

## 🗺️ Project Roadmap & Current Status

The backend is being built iteratively using a modular monolith design. Here is the current roadmap and implementation status:

| Phase | Description | Status | Target Date |
| :--- | :--- | :---: | :--- |
| **Phase 1** | **Backend Foundation & Boilerplate** <br> FastAPI setup, configuration (`pydantic-settings`), structural JSON logging (`structlog`), exceptions wrapper, database session setup, and pytest framework. | **Done** | June 26, 2026 |
| **Phase 2** | **Authentication & OTP Verification** <br> `User` & `OTPState` DB tables, Alembic migrations, secure 6-digit OTP generation, SHA-256 hashing, timing-attack protection, Redis rate-limiting (IP/Phone), AWS SNS provider integration, JWT issuance, and Role-Based Access Control (RBAC) guards. | **Done (Current)** | July 10, 2026 |
| **Phase 3** | **Studio & Service Catalog** <br> Multi-tenant `Studio` setups, packages, add-ons, dynamic pricing engine, and administrative CRUD endpoints. | *Pending* | - |
| **Phase 4** | **Availability & Booking Engine** <br> Range-based double-booking protection, calendar allocations, and reservation holds. | *Pending* | - |
| **Phase 5** | **Cart & Payments** <br> Customer carts, packages configuration, pricing checkouts, and payment gateway callbacks. | *Pending* | - |
| **Phase 6** | **Photographer Assignment & Booking Workflows** <br> Auto-matching, notifications, status workflows, and photographer calendar synchronization. | *Pending* | - |
| **Phase 7** | **Digital Galleries & Selection** <br> AWS S3 private asset uploads, pre-signed download URLs, and selection status tracking. | *Pending* | - |
| **Phase 8** | **Notifications & Admin Dashboard** <br> Email/SMS alerts, analytics endpoints, and administrative management interface. | *Pending* | - |

***

## 🛠️ Tech Stack
- **Framework**: FastAPI (Python 3.12+)
- **Database**: PostgreSQL (SQLAlchemy 2.0 Async Engine / `asyncpg` Driver)
- **Migrations**: Alembic
- **Caching & Limits**: Redis (`redis-py` async client)
- **SMS Integration**: AWS SNS (Transactional SMS Gateway) with Async executor fallback
- **Authentication**: JWT (JSON Web Tokens) & Cryptographic OTP verification
- **Structured Logging**: `structlog` (JSON logs for production, pretty console logs for development)
- **Test Framework**: `pytest` + `pytest-asyncio` + `httpx` (Mocked Redis/SMS transports)

***

## 📁 Project Structure
```text
studiolive-backend/
├── app/
│   ├── core/              # Config, security, logging, exceptions, and middlewares
│   ├── db/                # DB Session setup and Base Declarative models
│   ├── infrastructure/    # External adapters (AWS SNS, S3, etc.)
│   └── modules/           # Domain sub-modules
│       ├── auth/          # OTP generation, rate limiting, and verification endpoints
│       └── users/         # User profiles and Role configurations
├── migrations/            # Alembic DB migration versions
├── tests/                 # Unit and E2E integration test suite
├── .env.example           # Example local environment configurations
├── pytest.ini             # Pytest framework settings
├── requirements.txt       # Project python dependencies
└── README.md              # Project overview
```

***

## 🚀 Local Installation & Setup

### 1. Requirements
Ensure you have **Python 3.12+**, **PostgreSQL**, and **Redis** running locally.

### 2. Set Up Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate    # macOS/Linux
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the root directory:
```env
APP_NAME="StudioLive"
APP_ENV="dev"
DATABASE_URL="postgresql+asyncpg://postgres:Ashish@localhost:5432/studiolive"
REDIS_URL="redis://localhost:6379/0"
SECRET_KEY="your-super-secret-jwt-key"
AWS_REGION="us-east-1"
AWS_SNS_ENABLED="false"
```

### 4. Database Migrations
Apply the migrations to upgrade your database schema:
```bash
alembic upgrade head
```

### 5. Running the Dev Server
Start the FastAPI hot-reloading server:
```bash
uvicorn app.main:app --reload
```
You can view the interactive documentation at:
*   Swagger UI: http://127.0.0.1:8000/docs
*   ReDoc: http://127.0.0.1:8000/redoc

### 6. Running Tests
Run the pytest test suite:
```bash
pytest
```
*Note: The test suite automatically drops and recreates test tables and flushes Redis caches between test runs to ensure clean test states.*

---

## ⚖️ License
MIT
