"""CLI command for scaffolding a new DAG Forge project."""

import os
from pathlib import Path

import click
from rich.console import Console

console = Console()

DEFAULT_TOML = """[dagforge]
input_dir = "input"
output_dir = "output"
default_owner = "data-team"
default_start_date = "2024-01-01"

[dagforge.policies]
enabled = [
    "require_tags",
    "require_description",
    "require_owner",
]
max_tasks_per_dag = 50
"""


@click.command("init")
@click.option("--dir", "project_dir", default=".", help="Directory to initialize")
def init_cmd(project_dir: str) -> None:
    """Initialize a new DAG Forge project with standard directories and config."""
    base = Path(project_dir).resolve()
    
    console.print(f"Initializing DAG Forge project in [bold blue]{base}[/bold blue]...")
    
    dirs_to_create = ["input", "output", "templates"]
    for d in dirs_to_create:
        dir_path = base / d
        if not dir_path.exists():
            dir_path.mkdir(parents=True)
            console.print(f"  [green]+ Created directory:[/green] {d}/")
        else:
            console.print(f"  [yellow]~ Directory exists:[/yellow] {d}/")
            
    config_path = base / "dagforge.toml"
    if not config_path.exists():
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(DEFAULT_TOML)
        console.print(f"  [green]+ Created config:[/green] dagforge.toml")
    else:
        console.print("  [yellow]~ Config exists:[/yellow] dagforge.toml")
        
    sample_path = base / "input" / "sample.yaml"
    if not sample_path.exists():
        with open(sample_path, "w", encoding="utf-8") as f:
            f.write("sample_dag:\n  schedule: '@daily'\n  tasks:\n    hello: {operator: empty}\n")
        console.print(f"  [green]+ Created sample input:[/green] input/sample.yaml")
        
    console.print("\n[bold green]DAG Forge project initialized successfully![/bold green]")
    console.print("Try running: [bold]dagforge generate input -o output[/bold]")
