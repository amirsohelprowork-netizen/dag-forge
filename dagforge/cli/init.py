"""CLI command for scaffolding a new DAG Forge project."""

from importlib.resources import files
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

SAMPLE_YAML = """sample_dag:
  description: A minimal YAML example
  tags: [starter]
  default_args:
    owner: data-team
    start_date: "2024-01-01"
  schedule: "@daily"
  tasks:
    hello: {operator: empty}
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
        sample_path.write_text(SAMPLE_YAML, encoding="utf-8")
        console.print("  [green]+ Created sample input[/green] input/sample.yaml")

    workbook_path = base / "input" / "starter.xlsx"
    if not workbook_path.exists():
        workbook = files("dagforge").joinpath("starter", "starter.xlsx")
        workbook_path.write_bytes(workbook.read_bytes())
        console.print("  [green]+ Created starter workbook[/green] input/starter.xlsx")

    console.print("\n[bold green]DAG Forge project initialized successfully![/bold green]")
    console.print("Open [bold]input/starter.xlsx[/bold] and read the Start here tab.")
    console.print("From the project directory, run:")
    console.print("  [bold]dagforge validate input/starter.xlsx[/bold]")
    console.print("  [bold]dagforge generate input/starter.xlsx -o output[/bold]")
