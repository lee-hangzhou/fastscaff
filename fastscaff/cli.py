from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from fastscaff import __version__
from fastscaff.generator import ProjectGenerator

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


@app.command()
def new(
    project_name: str = typer.Argument(..., help="Project name"),
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
        help="Output directory",
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


@app.command()
def version() -> None:
    console.print(f"FastScaff version: {__version__}")


if __name__ == "__main__":
    app()
