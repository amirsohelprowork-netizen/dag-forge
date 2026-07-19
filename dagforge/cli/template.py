"""CLI commands for working with DAG Forge templates."""

from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from dagforge.templates.engine import TemplateEngine
from dagforge.renderers.dagfactory_renderer import DagFactoryRenderer

console = Console()

@click.group("template")
def template_group() -> None:
    """Manage and render Jinja2 DAG templates."""
    pass


@template_group.command("list")
def list_cmd() -> None:
    """List available built-in and custom templates."""
    engine = TemplateEngine()
    templates = engine.list_templates()
    
    table = Table(title="DAG Forge Templates")
    table.add_column("Template Name", style="cyan", no_wrap=True)
    table.add_column("Version", style="magenta")
    table.add_column("Description", style="green")
    
    for name, meta in templates.items():
        table.add_row(name, meta.version, meta.description)
        
    console.print(table)


@template_group.command("show")
@click.argument("template_name")
def show_cmd(template_name: str) -> None:
    """Show details and variables for a specific template."""
    engine = TemplateEngine()
    try:
        meta = engine.get_metadata(template_name)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
        
    console.print(f"\n[bold cyan]Template:[/bold cyan] {meta.name} (v{meta.version})")
    console.print(f"[bold]Description:[/bold] {meta.description}\n")
    
    table = Table(title="Template Variables")
    table.add_column("Variable", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Required", justify="center")
    table.add_column("Default")
    table.add_column("Description")
    
    for var_name, var_meta in meta.variables.items():
        req_str = "[red]*[/red]" if var_meta.required else ""
        def_str = str(var_meta.default) if var_meta.default is not None else ""
        table.add_row(var_name, var_meta.type, req_str, def_str, var_meta.description)
        
    console.print(table)
    
    if meta.example_values:
        console.print("\n[bold]Example rendering:[/bold]")
        console.print("dagforge template use {} {}".format(
            template_name,
            " ".join(f"--var {k}={v}" for k, v in meta.example_values.items())
        ))


@template_group.command("use")
@click.argument("template_name")
@click.option("-o", "--output", required=True, help="Output YAML file path")
@click.option("--var", "vars_list", multiple=True, help="Set variables (format: key=value)")
def use_cmd(template_name: str, output: str, vars_list: tuple[str, ...]) -> None:
    """Render a template to a DAG YAML file."""
    engine = TemplateEngine()
    
    try:
        meta = engine.get_metadata(template_name)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()
        
    # Parse CLI variables
    variables: dict[str, Any] = {}
    for v in vars_list:
        if "=" in v:
            key, val = v.split("=", 1)
            variables[key] = val
            
    # Interactive prompt for missing variables
    for var_name, var_meta in meta.variables.items():
        if var_name not in variables:
            if var_meta.required and var_meta.default is None:
                variables[var_name] = Prompt.ask(
                    f"[cyan]{var_name}[/cyan] ({var_meta.description})"
                )
            elif var_meta.default is not None:
                variables[var_name] = var_meta.default
                
    try:
        dag = engine.render(template_name, variables)
    except Exception as e:
        console.print(f"[red]Render Error:[/red] {e}")
        raise click.Abort()
        
    # Output to YAML
    out_path = Path(output)
    if not out_path.parent.exists():
        out_path.parent.mkdir(parents=True)
        
    renderer = DagFactoryRenderer()
    yaml_str = renderer.render(dag)
    
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(yaml_str)
        
    console.print(f"[green]Successfully rendered template to:[/green] {out_path}")
