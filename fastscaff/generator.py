import shutil
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()
TEMPLATES_DIR = Path(__file__).parent / "templates"


class ProjectGenerator:

    def __init__(
        self,
        project_name: str,
        orm: str,
        output_path: Path,
        with_rbac: bool = False,
    ) -> None:
        self.project_name = project_name
        self.orm = orm
        self.output_path = output_path
        self.with_rbac = with_rbac

        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            keep_trailing_newline=True,
        )

        self.context: dict[str, Any] = {
            "project_name": project_name,
            "project_name_snake": project_name.replace("-", "_"),
            "orm": orm,
            "is_tortoise": orm == "tortoise",
            "is_sqlalchemy": orm == "sqlalchemy",
            "with_rbac": with_rbac,
        }

    def generate(self) -> None:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating project...", total=None)

            self.output_path.mkdir(parents=True, exist_ok=True)

            progress.update(task, description="Generating base files...")
            self._generate_base_files()

            progress.update(task, description="Generating application code...")
            self._generate_app_structure()

            progress.update(task, description="Generating tests...")
            self._generate_tests()

            progress.update(task, description="Done")

    def _generate_base_files(self) -> None:
        # Templates (need rendering)
        templates = [
            ("base/env.example.jinja2", ".env.example"),
            ("base/docker-compose.yml.jinja2", "docker-compose.yml"),
            ("base/pyproject.toml.jinja2", "pyproject.toml"),
            ("base/requirements.txt.jinja2", "requirements.txt"),
            ("base/README.md.jinja2", "README.md"),
        ]
        for template_path, output_name in templates:
            self._render_template(template_path, output_name)

        # Static files (direct copy)
        static_files = [
            ("base/gitignore", ".gitignore"),
            ("base/pre-commit-config.yaml", ".pre-commit-config.yaml"),
            ("base/Dockerfile", "Dockerfile"),
            ("base/Makefile", "Makefile"),
        ]
        for src_path, output_name in static_files:
            self._copy_file(src_path, output_name)

    def _generate_app_structure(self) -> None:
        app_dir = self.output_path / "app"
        app_dir.mkdir(exist_ok=True)

        self._copy_file("app/__init__.py", "app/__init__.py")

        # ORM-specific main.py
        if self.orm == "tortoise":
            self._copy_file("app/main_tortoise.py", "app/main.py")
        else:
            self._copy_file("app/main_sqlalchemy.py", "app/main.py")

        self._generate_core()
        self._generate_api()
        self._generate_models()
        self._generate_schemas()
        self._generate_repositories()
        self._generate_services()
        self._generate_middleware()
        self._generate_exceptions()
        self._generate_utils()

    def _generate_core(self) -> None:
        core_dir = self.output_path / "app" / "core"
        core_dir.mkdir(exist_ok=True)

        # Templates (need rendering)
        templates = [
            ("app/core/config.py.jinja2", "app/core/config.py"),
            ("app/core/logger.py.jinja2", "app/core/logger.py"),
            ("app/core/lifespan.py.jinja2", "app/core/lifespan.py"),
        ]
        for template_path, output_name in templates:
            self._render_template(template_path, output_name)

        # Static files (direct copy)
        static_files = [
            ("app/core/__init__.py", "app/core/__init__.py"),
            ("app/core/security.py", "app/core/security.py"),
            ("app/core/singleton.py", "app/core/singleton.py"),
            ("app/core/redis.py", "app/core/redis.py"),
        ]
        for src_path, output_name in static_files:
            self._copy_file(src_path, output_name)

        # ORM-specific database file
        if self.orm == "tortoise":
            self._copy_file("app/core/database_tortoise.py", "app/core/database.py")
        else:
            self._copy_file("app/core/database_sqlalchemy.py", "app/core/database.py")

        # Optional RBAC
        if self.with_rbac:
            self._copy_file("app/core/rbac.py", "app/core/rbac.py")

    def _generate_api(self) -> None:
        api_v1_dir = self.output_path / "app" / "api" / "v1" / "endpoints"
        api_v1_dir.mkdir(parents=True, exist_ok=True)

        static_files = [
            ("app/api/__init__.py", "app/api/__init__.py"),
            ("app/api/v1/__init__.py", "app/api/v1/__init__.py"),
            ("app/api/v1/router.py", "app/api/v1/router.py"),
            ("app/api/v1/endpoints/__init__.py", "app/api/v1/endpoints/__init__.py"),
            ("app/api/v1/endpoints/health.py", "app/api/v1/endpoints/health.py"),
            ("app/api/v1/endpoints/auth.py", "app/api/v1/endpoints/auth.py"),
            ("app/api/v1/endpoints/users.py", "app/api/v1/endpoints/users.py"),
        ]
        for src_path, output_name in static_files:
            self._copy_file(src_path, output_name)

    def _generate_models(self) -> None:
        models_dir = self.output_path / "app" / "models"
        models_dir.mkdir(exist_ok=True)

        self._copy_file("app/models/__init__.py", "app/models/__init__.py")

        if self.orm == "tortoise":
            self._copy_file("app/models/base_tortoise.py", "app/models/base.py")
            self._copy_file("app/models/user_tortoise.py", "app/models/user.py")
        else:
            self._copy_file("app/models/base_sqlalchemy.py", "app/models/base.py")
            self._copy_file("app/models/user_sqlalchemy.py", "app/models/user.py")

    def _generate_schemas(self) -> None:
        schemas_dir = self.output_path / "app" / "schemas"
        schemas_dir.mkdir(exist_ok=True)

        static_files = [
            ("app/schemas/__init__.py", "app/schemas/__init__.py"),
            ("app/schemas/base.py", "app/schemas/base.py"),
            ("app/schemas/auth.py", "app/schemas/auth.py"),
            ("app/schemas/user.py", "app/schemas/user.py"),
        ]
        for src_path, output_name in static_files:
            self._copy_file(src_path, output_name)

    def _generate_repositories(self) -> None:
        repo_dir = self.output_path / "app" / "repositories"
        repo_dir.mkdir(exist_ok=True)

        self._copy_file("app/repositories/__init__.py", "app/repositories/__init__.py")

        if self.orm == "tortoise":
            self._copy_file("app/repositories/base_tortoise.py", "app/repositories/base.py")
            self._copy_file("app/repositories/user_tortoise.py", "app/repositories/user.py")
        else:
            self._copy_file("app/repositories/base_sqlalchemy.py", "app/repositories/base.py")
            self._copy_file("app/repositories/user_sqlalchemy.py", "app/repositories/user.py")

    def _generate_services(self) -> None:
        services_dir = self.output_path / "app" / "services"
        services_dir.mkdir(exist_ok=True)

        if self.orm == "tortoise":
            self._copy_file("app/services/__init___tortoise.py", "app/services/__init__.py")
            self._copy_file("app/services/auth_tortoise.py", "app/services/auth.py")
            self._copy_file("app/services/user_tortoise.py", "app/services/user.py")
        else:
            self._copy_file("app/services/__init___sqlalchemy.py", "app/services/__init__.py")
            self._copy_file("app/services/auth_sqlalchemy.py", "app/services/auth.py")
            self._copy_file("app/services/user_sqlalchemy.py", "app/services/user.py")

    def _generate_middleware(self) -> None:
        middleware_dir = self.output_path / "app" / "middleware"
        middleware_dir.mkdir(exist_ok=True)

        # ORM-specific __init__.py
        if self.orm == "tortoise":
            self._copy_file("app/middleware/__init___tortoise.py", "app/middleware/__init__.py")
        else:
            self._copy_file("app/middleware/__init___sqlalchemy.py", "app/middleware/__init__.py")
            self._copy_file("app/middleware/database.py", "app/middleware/database.py")

        static_files = [
            ("app/middleware/logging.py", "app/middleware/logging.py"),
            ("app/middleware/cors.py", "app/middleware/cors.py"),
            ("app/middleware/security.py", "app/middleware/security.py"),
            ("app/middleware/jwt.py", "app/middleware/jwt.py"),
            ("app/middleware/sign.py", "app/middleware/sign.py"),
            ("app/middleware/tracing.py", "app/middleware/tracing.py"),
        ]
        for src_path, output_name in static_files:
            self._copy_file(src_path, output_name)

    def _generate_exceptions(self) -> None:
        exceptions_dir = self.output_path / "app" / "exceptions"
        exceptions_dir.mkdir(exist_ok=True)

        static_files = [
            ("app/exceptions/__init__.py", "app/exceptions/__init__.py"),
            ("app/exceptions/base.py", "app/exceptions/base.py"),
            ("app/exceptions/handlers.py", "app/exceptions/handlers.py"),
        ]
        for src_path, output_name in static_files:
            self._copy_file(src_path, output_name)

    def _generate_utils(self) -> None:
        utils_dir = self.output_path / "app" / "utils"
        utils_dir.mkdir(exist_ok=True)

        # Template (need rendering)
        self._render_template("app/utils/sort_helper.py.jinja2", "app/utils/sort_helper.py")

        # Static files (direct copy)
        static_files = [
            ("app/utils/__init__.py", "app/utils/__init__.py"),
            ("app/utils/snowflake.py", "app/utils/snowflake.py"),
            ("app/utils/rate_limiter.py", "app/utils/rate_limiter.py"),
            ("app/utils/auth.py", "app/utils/auth.py"),
            ("app/utils/cache.py", "app/utils/cache.py"),
        ]
        for src_path, output_name in static_files:
            self._copy_file(src_path, output_name)

    def _generate_tests(self) -> None:
        tests_dir = self.output_path / "tests"
        tests_dir.mkdir(exist_ok=True)

        api_tests_dir = tests_dir / "api"
        api_tests_dir.mkdir(exist_ok=True)

        static_files = [
            ("tests/__init__.py", "tests/__init__.py"),
            ("tests/conftest.py", "tests/conftest.py"),
            ("tests/api/__init__.py", "tests/api/__init__.py"),
            ("tests/api/test_health.py", "tests/api/test_health.py"),
        ]
        for src_path, output_name in static_files:
            self._copy_file(src_path, output_name)

    def _render_template(self, template_path: str, output_name: str) -> None:
        """Render a Jinja2 template with context variables."""
        template = self.env.get_template(template_path)
        content = template.render(**self.context)

        output_file = self.output_path / output_name
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(content, encoding="utf-8")

    def _copy_file(self, src_path: str, output_name: str) -> None:
        """Copy a static file without rendering."""
        src_file = TEMPLATES_DIR / src_path
        output_file = self.output_path / output_name
        output_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, output_file)
