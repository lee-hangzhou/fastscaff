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
        base_files = [
            ("base/env.example.jinja2", ".env.example"),
            ("base/gitignore.jinja2", ".gitignore"),
            ("base/pre-commit-config.yaml.jinja2", ".pre-commit-config.yaml"),
            ("base/Dockerfile.jinja2", "Dockerfile"),
            ("base/docker-compose.yml.jinja2", "docker-compose.yml"),
            ("base/Makefile.jinja2", "Makefile"),
            ("base/pyproject.toml.jinja2", "pyproject.toml"),
            ("base/requirements.txt.jinja2", "requirements.txt"),
            ("base/README.md.jinja2", "README.md"),
        ]

        for template_path, output_name in base_files:
            self._render_template(template_path, output_name)

    def _generate_app_structure(self) -> None:
        app_dir = self.output_path / "app"
        app_dir.mkdir(exist_ok=True)

        self._render_template("app/__init__.py.jinja2", "app/__init__.py")
        self._render_template("app/main.py.jinja2", "app/main.py")

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

        core_files = [
            ("app/core/__init__.py.jinja2", "app/core/__init__.py"),
            ("app/core/config.py.jinja2", "app/core/config.py"),
            ("app/core/logger.py.jinja2", "app/core/logger.py"),
            ("app/core/lifespan.py.jinja2", "app/core/lifespan.py"),
            ("app/core/security.py.jinja2", "app/core/security.py"),
            ("app/core/singleton.py.jinja2", "app/core/singleton.py"),
            ("app/core/redis.py.jinja2", "app/core/redis.py"),
        ]

        for template_path, output_name in core_files:
            self._render_template(template_path, output_name)

        if self.orm == "tortoise":
            self._render_template("app/core/database_tortoise.py.jinja2", "app/core/database.py")
        else:
            self._render_template("app/core/database_sqlalchemy.py.jinja2", "app/core/database.py")

        if self.with_rbac:
            self._render_template("app/core/rbac.py.jinja2", "app/core/rbac.py")

    def _generate_api(self) -> None:
        api_v1_dir = self.output_path / "app" / "api" / "v1" / "endpoints"
        api_v1_dir.mkdir(parents=True, exist_ok=True)

        api_files = [
            ("app/api/__init__.py.jinja2", "app/api/__init__.py"),
            ("app/api/deps.py.jinja2", "app/api/deps.py"),
            ("app/api/v1/__init__.py.jinja2", "app/api/v1/__init__.py"),
            ("app/api/v1/router.py.jinja2", "app/api/v1/router.py"),
            ("app/api/v1/deps.py.jinja2", "app/api/v1/deps.py"),
            ("app/api/v1/endpoints/__init__.py.jinja2", "app/api/v1/endpoints/__init__.py"),
            ("app/api/v1/endpoints/health.py.jinja2", "app/api/v1/endpoints/health.py"),
            ("app/api/v1/endpoints/auth.py.jinja2", "app/api/v1/endpoints/auth.py"),
            ("app/api/v1/endpoints/users.py.jinja2", "app/api/v1/endpoints/users.py"),
        ]

        for template_path, output_name in api_files:
            self._render_template(template_path, output_name)

    def _generate_models(self) -> None:
        models_dir = self.output_path / "app" / "models"
        models_dir.mkdir(exist_ok=True)

        self._render_template("app/models/__init__.py.jinja2", "app/models/__init__.py")

        if self.orm == "tortoise":
            self._render_template("app/models/base_tortoise.py.jinja2", "app/models/base.py")
            self._render_template("app/models/user_tortoise.py.jinja2", "app/models/user.py")
        else:
            self._render_template("app/models/base_sqlalchemy.py.jinja2", "app/models/base.py")
            self._render_template("app/models/user_sqlalchemy.py.jinja2", "app/models/user.py")

    def _generate_schemas(self) -> None:
        schemas_dir = self.output_path / "app" / "schemas"
        schemas_dir.mkdir(exist_ok=True)

        schema_files = [
            ("app/schemas/__init__.py.jinja2", "app/schemas/__init__.py"),
            ("app/schemas/base.py.jinja2", "app/schemas/base.py"),
            ("app/schemas/auth.py.jinja2", "app/schemas/auth.py"),
            ("app/schemas/user.py.jinja2", "app/schemas/user.py"),
        ]

        for template_path, output_name in schema_files:
            self._render_template(template_path, output_name)

    def _generate_repositories(self) -> None:
        repo_dir = self.output_path / "app" / "repositories"
        repo_dir.mkdir(exist_ok=True)

        self._render_template("app/repositories/__init__.py.jinja2", "app/repositories/__init__.py")

        if self.orm == "tortoise":
            self._render_template("app/repositories/base_tortoise.py.jinja2", "app/repositories/base.py")
            self._render_template("app/repositories/user_tortoise.py.jinja2", "app/repositories/user.py")
        else:
            self._render_template("app/repositories/base_sqlalchemy.py.jinja2", "app/repositories/base.py")
            self._render_template("app/repositories/user_sqlalchemy.py.jinja2", "app/repositories/user.py")

    def _generate_services(self) -> None:
        services_dir = self.output_path / "app" / "services"
        services_dir.mkdir(exist_ok=True)

        service_files = [
            ("app/services/__init__.py.jinja2", "app/services/__init__.py"),
            ("app/services/base.py.jinja2", "app/services/base.py"),
            ("app/services/auth.py.jinja2", "app/services/auth.py"),
            ("app/services/user.py.jinja2", "app/services/user.py"),
        ]

        for template_path, output_name in service_files:
            self._render_template(template_path, output_name)

    def _generate_middleware(self) -> None:
        middleware_dir = self.output_path / "app" / "middleware"
        middleware_dir.mkdir(exist_ok=True)

        middleware_files = [
            ("app/middleware/__init__.py.jinja2", "app/middleware/__init__.py"),
            ("app/middleware/logging.py.jinja2", "app/middleware/logging.py"),
            ("app/middleware/cors.py.jinja2", "app/middleware/cors.py"),
            ("app/middleware/security.py.jinja2", "app/middleware/security.py"),
            ("app/middleware/jwt.py.jinja2", "app/middleware/jwt.py"),
            ("app/middleware/sign.py.jinja2", "app/middleware/sign.py"),
            ("app/middleware/tracing.py.jinja2", "app/middleware/tracing.py"),
        ]

        for template_path, output_name in middleware_files:
            self._render_template(template_path, output_name)

    def _generate_exceptions(self) -> None:
        exceptions_dir = self.output_path / "app" / "exceptions"
        exceptions_dir.mkdir(exist_ok=True)

        exception_files = [
            ("app/exceptions/__init__.py.jinja2", "app/exceptions/__init__.py"),
            ("app/exceptions/base.py.jinja2", "app/exceptions/base.py"),
            ("app/exceptions/handlers.py.jinja2", "app/exceptions/handlers.py"),
        ]

        for template_path, output_name in exception_files:
            self._render_template(template_path, output_name)

    def _generate_utils(self) -> None:
        utils_dir = self.output_path / "app" / "utils"
        utils_dir.mkdir(exist_ok=True)

        utils_files = [
            ("app/utils/__init__.py.jinja2", "app/utils/__init__.py"),
            ("app/utils/snowflake.py.jinja2", "app/utils/snowflake.py"),
            ("app/utils/sort_helper.py.jinja2", "app/utils/sort_helper.py"),
            ("app/utils/rate_limiter.py.jinja2", "app/utils/rate_limiter.py"),
            ("app/utils/auth.py.jinja2", "app/utils/auth.py"),
            ("app/utils/cache.py.jinja2", "app/utils/cache.py"),
        ]

        for template_path, output_name in utils_files:
            self._render_template(template_path, output_name)

    def _generate_tests(self) -> None:
        tests_dir = self.output_path / "tests"
        tests_dir.mkdir(exist_ok=True)

        api_tests_dir = tests_dir / "api"
        api_tests_dir.mkdir(exist_ok=True)

        test_files = [
            ("tests/__init__.py.jinja2", "tests/__init__.py"),
            ("tests/conftest.py.jinja2", "tests/conftest.py"),
            ("tests/api/__init__.py.jinja2", "tests/api/__init__.py"),
            ("tests/api/test_health.py.jinja2", "tests/api/test_health.py"),
        ]

        for template_path, output_name in test_files:
            self._render_template(template_path, output_name)

    def _render_template(self, template_path: str, output_name: str) -> None:
        template = self.env.get_template(template_path)
        content = template.render(**self.context)

        output_file = self.output_path / output_name
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(content, encoding="utf-8")
