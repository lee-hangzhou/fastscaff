# FastScaff

FastAPI project scaffolding tool - quickly generate standardized FastAPI project structures.

[中文文档](README_CN.md)

## Installation

```bash
pip install fastscaff
```

## Commands

### Create Project

```bash
fastscaff new myproject --orm sqlalchemy
```

Options:
- `--orm` - ORM choice: `sqlalchemy` or `tortoise` (default: `tortoise`)
- `--output` - Output directory (default: current directory)
- `--with-rbac` - Include Casbin RBAC support
- `--with-celery` - Include Celery task queue support
- `--force` - Overwrite existing directory

Examples:

```bash
# Basic project with SQLAlchemy
fastscaff new myproject --orm sqlalchemy

# Full-featured project
fastscaff new myproject --orm sqlalchemy --with-celery --with-rbac

# Specify output directory
fastscaff new myproject --output /path/to/dir
```

### Generate Models from Database

Generate ORM models by introspecting existing MySQL database tables:

```bash
cd myproject
fastscaff models --db-url "mysql://user:pass@localhost:3306/mydb"
```

Options:
- `--db-url` - Database connection URL (required)
- `--orm` - Target ORM: `sqlalchemy` or `tortoise` (auto-detected from requirements.txt)
- `--tables` - Comma-separated table names (default: all tables)
- `--output` - Output directory (default: current directory)

Examples:

```bash
# In project directory - ORM is auto-detected
cd myproject
fastscaff models --db-url "mysql://root:password@localhost:3306/mydb"

# Generate models for specific tables
fastscaff models --db-url "mysql://..." --tables user,order,product

# Explicitly specify ORM
fastscaff models --db-url "mysql://..." --orm tortoise
```

Generated models include:
- Field type mapping
- Primary keys and auto-increment
- Indexes
- Foreign key relationships
- Table and column comments

## Project Structure

```
myproject/
├── app/
│   ├── main.py              # Application entry point
│   ├── core/
│   │   ├── config.py        # Settings (env-based)
│   │   ├── database.py      # Database connection
│   │   ├── redis.py         # Redis client
│   │   ├── security.py      # Password hashing, JWT
│   │   ├── logger.py        # Structured logging
│   │   └── lifespan.py      # Startup/shutdown events
│   ├── api/v1/
│   │   ├── router.py        # API router
│   │   └── endpoints/       # Route handlers
│   ├── models/              # ORM models
│   ├── schemas/             # Pydantic schemas
│   ├── repositories/        # Data access layer
│   ├── services/            # Business logic layer
│   ├── middleware/          # Request/response middleware
│   ├── exceptions/          # Custom exceptions
│   └── utils/               # Utility functions
├── deploy/                  # Test compose + prod K8s
├── tests/
├── .env.example
├── Makefile
└── requirements.txt
```

## Architecture

The generated project follows a layered architecture:

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| API | `api/` | HTTP handling, request validation, response formatting |
| Service | `services/` | Business logic, orchestration |
| Repository | `repositories/` | Data access, database queries |
| Model | `models/` | Database table definitions |
| Schema | `schemas/` | Request/response data structures |

Services are accessed via a singleton registry pattern:

```python
from app.services import registry

user = await registry.user_service.get_user_by_id(user_id)
```

## Built-in Features

### Middleware

- CORS handling
- Request logging with trace ID
- JWT authentication
- Security headers
- Request signing verification

### Utilities

- Snowflake ID generator
- Rate limiter (Redis-based)
- Cache decorator
- Password hashing

### Database

- SQLite by default (zero configuration)
- MySQL/PostgreSQL ready (just update `DATABASE_URL`)
- Async database operations
- Request-scoped sessions (SQLAlchemy)

## Running the Project

```bash
cd myproject
pip install -r requirements.txt
make dev
```

The project runs immediately with SQLite - no database setup required.

Available make commands:

```bash
make up            # Test deploy: build → recreate → wait ready
make down          # Stop test stack
make dev           # Local uvicorn
make test          # Run tests
make lint          # Run linter
```

Deployment: test uses Compose + `deploy/.env.test` placeholders (`source /etc/profile` for real values); production uses `deploy/deployment.yaml` with ConfigMap/Secret. See generated `deploy/README.md`.

If Celery is enabled:

```bash
make celery-worker  # Start Celery worker
make celery-beat    # Start Celery beat scheduler
```

## Configuration

Configuration is managed via environment variables. Copy `.env.example` to `.env`:

```bash
# Application
ENV=dev
DEBUG=true
PORT=8000

# Database
DATABASE_URL=sqlite+aiosqlite:///./app.db
# DATABASE_URL=mysql+aiomysql://user:pass@localhost:3306/mydb

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Celery (if enabled)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

## Development

```bash
# Clone the repository
git clone https://github.com/lee-hangzhou/fastscaff.git
cd fastscaff

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Code formatting
ruff check --fix .
ruff format .
```

## License

MIT
