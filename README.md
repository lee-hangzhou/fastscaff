# FastScaff

FastAPI project scaffolding tool - quickly create standardized FastAPI project structures.

[中文文档](README_CN.md)

## Features

- One-click creation of standardized FastAPI project structure
- Multiple ORM support (Tortoise ORM / SQLAlchemy)
- Built-in JWT authentication
- Structured logging with structlog
- Unified exception handling
- Docker deployment support
- Testing framework integration
- SQLite by default (zero configuration)

## Installation

```bash
# Install from source
cd FastScaff
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

## Quick Start

### Create a New Project

```bash
# Using SQLAlchemy (with SQLite by default)
fastscaff new myproject --orm sqlalchemy

# Using Tortoise ORM
fastscaff new myproject --orm tortoise

# Specify output directory
fastscaff new myproject --output /path/to/dir
```

### Generated Project Structure

```
myproject/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── logger.py
│   │   ├── lifespan.py
│   │   ├── security.py
│   │   └── redis.py
│   ├── api/
│   │   └── v1/
│   │       ├── router.py
│   │       ├── deps.py
│   │       └── endpoints/
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   ├── middleware/
│   ├── exceptions/
│   └── utils/
├── tests/
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── requirements.txt
```

### Run the Generated Project

```bash
cd myproject
pip install -r requirements.txt
make dev
```

The project runs out of the box with SQLite - no configuration needed.

## CLI Reference

```bash
# Show help
fastscaff --help

# Create new project
fastscaff new <project_name>
  --orm         ORM choice: tortoise or sqlalchemy (default: tortoise)
  --output      Output directory (default: current directory)
  --force       Force overwrite existing directory
  --with-rbac   Enable RBAC with Casbin

# Show version
fastscaff version
```

## Project Layers

| Layer | Directory | Responsibility |
|-------|-----------|----------------|
| API | `api/` | HTTP request handling, parameter validation |
| Service | `services/` | Business logic, transaction management |
| Repository | `repositories/` | Data access, CRUD operations |
| Model | `models/` | Database table definitions |
| Schema | `schemas/` | Request/response data structures |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Code formatting
ruff check --fix .
ruff format .
```

## License

MIT
