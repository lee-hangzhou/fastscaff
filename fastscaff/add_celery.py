"""Add Celery support to an existing FastScaff project."""

import re
import shutil
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _detect_project_root(path: Path) -> Path:
    """Return project root (directory containing app/)."""
    if (path / "app" / "core" / "config.py").exists():
        return path
    if path.parent != path and path.parent.exists():
        return _detect_project_root(path.parent)
    return path


def _get_project_name_snake(project_root: Path) -> str:
    """Extract PROJECT_NAME from config.py and normalize to snake_case."""
    config_path = project_root / "app" / "core" / "config.py"
    if not config_path.exists():
        return project_root.name.replace("-", "_")
    text = config_path.read_text(encoding="utf-8")
    m = re.search(r'PROJECT_NAME:\s*str\s*=\s*["\']([^"\']+)["\']', text)
    if m:
        return m.group(1).replace("-", "_")
    return project_root.name.replace("-", "_")


def _is_tortoise(project_root: Path) -> bool:
    """Detect if project uses Tortoise ORM from requirements.txt."""
    req_path = project_root / "requirements.txt"
    if not req_path.exists():
        return True
    return "tortoise" in req_path.read_text(encoding="utf-8").lower()


def add_celery(project_root: Path) -> None:
    """Add Celery support to an existing FastScaff project at project_root."""
    project_root = project_root.resolve()
    if not (project_root / "app" / "core" / "config.py").exists():
        raise FileNotFoundError(
            f"Not a FastScaff project (missing app/core/config.py): {project_root}"
        )
    if (project_root / "app" / "tasks" / "__init__.py").exists():
        raise RuntimeError("Celery support already present (app/tasks exists).")

    project_name_snake = _get_project_name_snake(project_root)
    is_tortoise = _is_tortoise(project_root)

    # 1. Copy static files
    (project_root / "app" / "tasks" / "jobs").mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        TEMPLATES_DIR / "base" / "celery_worker.py",
        project_root / "celery_worker.py",
    )
    shutil.copy2(
        TEMPLATES_DIR / "app" / "tasks" / "__init__.py",
        project_root / "app" / "tasks" / "__init__.py",
    )
    shutil.copy2(
        TEMPLATES_DIR / "app" / "tasks" / "config.py",
        project_root / "app" / "tasks" / "config.py",
    )
    shutil.copy2(
        TEMPLATES_DIR / "app" / "tasks" / "jobs" / "__init__.py",
        project_root / "app" / "tasks" / "jobs" / "__init__.py",
    )
    shutil.copy2(
        TEMPLATES_DIR / "app" / "tasks" / "jobs" / "example.py",
        project_root / "app" / "tasks" / "jobs" / "example.py",
    )

    # 2. Patch requirements.txt
    req_path = project_root / "requirements.txt"
    if req_path.exists():
        req_text = req_path.read_text(encoding="utf-8")
        if "celery" not in req_text.lower():
            insert = "\ncelery[redis]>=5.3.0\n"
            if req_text.rstrip().endswith("\n"):
                req_path.write_text(req_text.rstrip() + insert, encoding="utf-8")
            else:
                req_path.write_text(req_text + insert, encoding="utf-8")

    # 3. Patch app/core/config.py: add CELERY_* before first @property
    config_path = project_root / "app" / "core" / "config.py"
    config_text = config_path.read_text(encoding="utf-8")
    if "CELERY_BROKER_URL" not in config_text:
        celery_block = """    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/1")
    CELERY_TIMEZONE: str = Field(default="UTC")

"""
        if "    @property" in config_text:
            config_text = config_text.replace(
                "    @property",
                celery_block + "    @property",
                1,
            )
        else:
            config_text = config_text.replace(
                'LOG_FORMAT: str = Field(default="json")',
                'LOG_FORMAT: str = Field(default="json")\n\n' + celery_block.strip(),
            )
        config_path.write_text(config_text, encoding="utf-8")

    # 4. Patch Makefile
    makefile_path = project_root / "Makefile"
    if makefile_path.exists():
        make_text = makefile_path.read_text(encoding="utf-8")
        if "celery-worker" not in make_text:
            make_text = make_text.replace(
                "docker-build docker-up docker-down",
                "docker-build docker-up docker-down celery-worker celery-beat",
                1,
            )
            make_text = make_text.replace(
                'make docker-down  Stop all services"',
                'make docker-down  Stop all services"\n\t@echo "  make celery-worker Start Celery worker"\n\t@echo "  make celery-beat   Start Celery beat scheduler"',
            )
            make_text = make_text.replace(
                "docker-compose logs -f app",
                "docker-compose logs -f app\n\ncelery-worker:\n\tcelery -A celery_worker worker --loglevel=info\n\ncelery-beat:\n\tcelery -A celery_worker beat --loglevel=info",
            )
            makefile_path.write_text(make_text, encoding="utf-8")

    # 5. Patch docker-compose.yml
    dc_path = project_root / "docker-compose.yml"
    if dc_path.exists():
        dc_text = dc_path.read_text(encoding="utf-8")
        if "celery-worker" not in dc_text:
            db_url = (
                "mysql://root:password@mysql:3306/" + project_name_snake
                if is_tortoise
                else "mysql+aiomysql://root:password@mysql:3306/" + project_name_snake
            )
            celery_services = f"""
  celery-worker:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: {project_name_snake}_celery_worker
    command: celery -A celery_worker worker --loglevel=info
    environment:
      - ENV=prod
      - DATABASE_URL={db_url}
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - {project_name_snake}_network

  celery-beat:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: {project_name_snake}_celery_beat
    command: celery -A celery_worker beat --loglevel=info
    environment:
      - ENV=prod
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - {project_name_snake}_network
"""
            dc_text = dc_text.replace("\nvolumes:", celery_services + "\nvolumes:")
            dc_path.write_text(dc_text, encoding="utf-8")

    # 6. Patch .env.example
    env_example = project_root / ".env.example"
    if env_example.exists():
        env_text = env_example.read_text(encoding="utf-8")
        if "CELERY_BROKER_URL" not in env_text:
            env_text = env_text.rstrip() + "\n\n# Celery\nCELERY_BROKER_URL=redis://localhost:6379/1\nCELERY_RESULT_BACKEND=redis://localhost:6379/1\nCELERY_TIMEZONE=UTC\n"
            env_example.write_text(env_text, encoding="utf-8")
