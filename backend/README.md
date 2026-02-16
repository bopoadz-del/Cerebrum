# Cerebrum AI Platform - Backend

A production-grade FastAPI backend for the Cerebrum AI platform with enterprise security, comprehensive audit logging, and DevOps automation.

## Features

### Core Infrastructure
- **PostgreSQL** with SQLAlchemy async ORM and connection pooling
- **PgBouncer** for database connection pooling
- **Redis** with 4 dedicated instances (Cache, Queue, Sessions, Rate Limit)
- **Alembic** migrations with zero-downtime support
- **Soft Delete** pattern with audit trail preservation

### Security
- **JWT Authentication** with 15-minute access tokens and 7-day refresh tokens
- **bcrypt Password Hashing** with salt rounds 12 and optional pepper
- **Multi-Factor Authentication (MFA)** using TOTP
- **Role-Based Access Control (RBAC)** with role hierarchy
- **Token Blacklisting** for immediate revocation
- **Server-Side Sessions** in Redis
- **Field-Level Encryption** for PII using AES-256-GCM
- **Rate Limiting** with slowapi and Redis backend
- **Security Headers** (HSTS, CSP, X-Frame-Options, etc.)

### Audit & Compliance
- **Audit Logging** with hash chain integrity
- **S3 WORM Storage** for audit log archival
- **SOC 2 Type II** controls documentation
- **GDPR Article 30** records of processing

### DevOps
- **Docker** multi-stage builds
- **Docker Compose** for local development and production
- **GitHub Actions** CI/CD pipelines
- **Health Checks** (/health, /health/live, /health/ready)
- **Structured Logging** with JSON output
- **Sentry** error tracking integration

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/cerebrum-ai/platform.git
   cd platform/backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Seed the database**
   ```bash
   python scripts/seed.py
   ```

7. **Start the development server**
   ```bash
   uvicorn app.main:app --reload
   ```

### Docker Development

```bash
# Start all services
docker-compose up -d

# Run migrations
docker-compose exec app alembic upgrade head

# Seed database
docker-compose exec app python scripts/seed.py
```

## Project Structure

```
backend/
├── app/
│   ├── api/              # API endpoints
│   │   ├── health.py     # Health check endpoints
│   │   └── v1/           # API v1 routes
│   │       ├── endpoints/
│   │       │   ├── auth.py    # Authentication endpoints
│   │       │   └── admin.py   # Admin endpoints
│   │       └── api.py
│   ├── core/             # Core functionality
│   │   ├── config.py     # Configuration management
│   │   ├── logging.py    # Structured logging
│   │   ├── sentry.py     # Sentry integration
│   │   ├── transaction.py # Transaction decorator
│   │   ├── vault.py      # HashiCorp Vault client
│   │   ├── encryption.py # Field-level encryption
│   │   ├── rate_limit.py # Rate limiting
│   │   └── security/     # Security components
│   │       ├── jwt.py
│   │       ├── password.py
│   │       ├── rbac.py
│   │       ├── mfa.py
│   │       ├── session.py
│   │       ├── token_blacklist.py
│   │       └── audit_storage.py
│   ├── db/               # Database
│   │   ├── base_class.py # Base model classes
│   │   ├── session.py    # Database sessions
│   │   ├── pgbouncer.py  # PgBouncer config
│   │   ├── redis.py      # Redis connections
│   │   ├── indexes.py    # Database indexes
│   │   ├── zero_downtime.py # Migration utilities
│   │   └── migrations/   # Alembic migrations
│   ├── middleware/       # FastAPI middleware
│   │   ├── cors.py
│   │   ├── validation.py
│   │   ├── exception.py
│   │   └── security_headers.py
│   ├── models/           # SQLAlchemy models
│   │   ├── user.py
│   │   └── audit.py
│   └── main.py           # Application entry point
├── scripts/              # Utility scripts
│   ├── seed.py
│   ├── backup_db.py
│   ├── migrate.py
│   └── security/         # Security scripts
├── tests/                # Test suite
│   ├── unit/
│   └── integration/
├── docs/                 # Documentation
│   └── compliance/
├── docker-compose.yml
├── docker-compose.prod.yml
├── Dockerfile
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

## API Documentation

When running in development mode, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_security.py

# Run integration tests
pytest tests/integration/
```

## Security Scanning

```bash
# Run all security checks
python scripts/security/safety_check.py
python scripts/security/bandit_scan.py
python scripts/security/gitleaks.py

# Run in CI
bandit -r app/
safety check
gitleaks detect
```

## Database Operations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Run migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Check migration status
python scripts/migrate.py status

# Backup database
python scripts/backup_db.py backup

# Restore database
python scripts/backup_db.py restore backup_file.sql.gz
```

## Deployment

### Production Deployment

1. **Set up environment variables**
   ```bash
   export ENVIRONMENT=production
   export DATABASE_URL=postgresql+asyncpg://...
   export SECRET_KEY=your-secret-key
   ```

2. **Deploy with Docker Compose**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Run migrations**
   ```bash
   docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
   ```

### CI/CD Pipeline

The project includes GitHub Actions workflows for:
- **CI**: Linting, testing, security scanning
- **Deploy**: Automated deployment to Render

See `.github/workflows/` for details.

## Configuration

Configuration is managed through environment variables using Pydantic Settings:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | Required |
| `REDIS_HOST` | Redis server host | localhost |
| `SECRET_KEY` | JWT signing key | Required |
| `ENVIRONMENT` | dev/staging/prod | development |
| `LOG_LEVEL` | Logging level | INFO |
| `SENTRY_DSN` | Sentry DSN | Optional |

See `app/core/config.py` for all configuration options.

## License

Proprietary - Cerebrum AI, Inc.

## Support

For support, contact:
- Email: support@cerebrum.ai
- Documentation: https://docs.cerebrum.ai
