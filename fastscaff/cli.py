from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel

from fastscaff import __version__
from fastscaff.generator import ProjectGenerator
from fastscaff.introspector import MySQLIntrospector
from fastscaff.model_generator import generate_models

app = typer.Typer(
    name="fastscaff",
    help="FastAPI project scaffolding tool",
    add_completion=False,
)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"FastScaff version: {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    _version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    pass


@app.command(
    help="Create a new FastAPI project. Example: fastscaff new myapp --orm tortoise",
)
def new(
    project_name: str = typer.Argument(
        ...,
        help="Project name (e.g. myapp, my_project)",
    ),
    orm: str = typer.Option(
        "tortoise",
        "--orm",
        "-o",
        help="ORM choice: tortoise or sqlalchemy",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-d",
        help="Output directory (default: current directory)",
    ),
    with_rbac: bool = typer.Option(
        False,
        "--with-rbac",
        help="Include Casbin RBAC support",
    ),
    with_celery: bool = typer.Option(
        False,
        "--with-celery",
        help="Include Celery task queue support",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing directory",
    ),
) -> None:
    """Create a new FastAPI project.

    Examples:
      fastscaff new myapp
      fastscaff new myapp --orm sqlalchemy
      fastscaff new myapp -d ./projects --with-rbac
    """
    if orm not in ("tortoise", "sqlalchemy"):
        console.print(f"[red]Error: ORM must be 'tortoise' or 'sqlalchemy', got '{orm}'[/red]")
        raise typer.Exit(1)

    if not project_name.replace("_", "").replace("-", "").isalnum():
        console.print(
            "[red]Error: Project name can only contain alphanumeric, underscores and hyphens[/red]"
        )
        raise typer.Exit(1)

    output_path = output or Path.cwd()
    project_path = output_path / project_name

    if project_path.exists() and not force:
        console.print(
            f"[red]Error: Directory '{project_path}' already exists. Use --force to overwrite[/red]"
        )
        raise typer.Exit(1)

    features = []
    if with_rbac:
        features.append("RBAC (Casbin)")
    if with_celery:
        features.append("Celery")

    console.print(Panel.fit(
        f"[bold green]Creating project[/bold green]\n\n"
        f"Name: [cyan]{project_name}[/cyan]\n"
        f"ORM: [cyan]{orm}[/cyan]\n"
        f"Features: [cyan]{', '.join(features) if features else 'None'}[/cyan]\n"
        f"Path: [cyan]{project_path}[/cyan]",
        title="FastScaff",
        border_style="blue",
    ))

    try:
        generator = ProjectGenerator(
            project_name=project_name,
            orm=orm,
            output_path=project_path,
            with_rbac=with_rbac,
            with_celery=with_celery,
        )
        generator.generate()

        console.print("\n[bold green]Project created successfully.[/bold green]\n")
        console.print(Panel.fit(
            f"cd {project_name}\n"
            f"pip install -r requirements.txt\n"
            f"make dev",
            title="Next steps",
            border_style="green",
        ))

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None


@app.command(help="Print FastScaff version.")
def version() -> None:
    console.print(f"FastScaff version: {__version__}")


def _detect_orm() -> Optional[str]:
    """Detect ORM from requirements.txt in current directory."""
    req_file = Path.cwd() / "requirements.txt"
    if not req_file.exists():
        return None

    content = req_file.read_text()
    if "sqlalchemy" in content.lower():
        return "sqlalchemy"
    if "tortoise" in content.lower():
        return "tortoise"
    return None


@app.command(
    help="Generate ORM models from MySQL (one file per table). Example: fastscaff models -d mysql://user:pass@host:3306/db",
)
def models(
    db_url: Optional[str] = typer.Option(
        None,
        "--db-url",
        "-d",
        help="MySQL URL (default: env DATABASE_URL)",
        envvar="DATABASE_URL",
    ),
    orm: Optional[str] = typer.Option(
        None,
        "--orm",
        "-o",
        help="ORM: tortoise or sqlalchemy (auto-detected from requirements.txt if omitted)",
    ),
    tables: Optional[str] = typer.Option(
        None,
        "--tables",
        "-t",
        help="Only these tables, comma-separated (default: all)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-O",
        help="Directory to write model files (default: current directory)",
    ),
) -> None:
    """Generate ORM model files from MySQL (one .py per table, filename = table name).

    Examples:
      fastscaff models -d mysql://user:pass@localhost:3306/mydb
      fastscaff models -d mysql://user:pass@localhost:3306/mydb -o tortoise -O app/models
      fastscaff models -d mysql://... --tables user,order,product
    """
    # Auto-detect ORM if not specified
    if orm is None:
        orm = _detect_orm()
        if orm:
            console.print(f"[green]Detected ORM: {orm}[/green]")
        else:
            orm = "tortoise"
            console.print(f"[yellow]Could not detect ORM, using default: {orm}[/yellow]")

    if orm not in ("tortoise", "sqlalchemy"):
        console.print(f"[red]Error: ORM must be 'tortoise' or 'sqlalchemy', got '{orm}'[/red]")
        raise typer.Exit(1)

    if not db_url:
        console.print(
            "[red]Error: Provide --db-url / -d or set DATABASE_URL in environment[/red]"
        )
        raise typer.Exit(1)

    table_list: Optional[List[str]] = None
    if tables:
        table_list = [t.strip() for t in tables.split(",")]

    output_path = output or Path.cwd()

    console.print(Panel.fit(
        f"[bold green]Generating models from database[/bold green]\n\n"
        f"Database: [cyan]{db_url.split('@')[-1] if '@' in db_url else db_url}[/cyan]\n"
        f"ORM: [cyan]{orm}[/cyan]\n"
        f"Tables: [cyan]{', '.join(table_list) if table_list else 'all'}[/cyan]\n"
        f"Output: [cyan]{output_path}[/cyan]",
        title="FastScaff",
        border_style="blue",
    ))

    try:
        introspector = MySQLIntrospector(db_url)
        introspector.connect()

        table_infos = introspector.get_tables(table_list)
        introspector.disconnect()

        if not table_infos:
            console.print("[yellow]No tables found.[/yellow]")
            raise typer.Exit(0)

        console.print(f"\n[green]Found {len(table_infos)} table(s):[/green]")
        for t in table_infos:
            console.print(f"  - {t.name} ({len(t.columns)} columns)")

        written = generate_models(table_infos, orm, output_path)
        files_str = ", ".join(f.name for f in written)
        console.print(f"\n[bold green]Models generated: {output_path}/ ({files_str})[/bold green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from None


if __name__ == "__main__":
    app()
