"""CLI generate command for DAG Forge.

Parses input files, validates them, and generates dag-factory YAML output.
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from dagforge.cli.checks import check_inputs, print_report
from dagforge.core.registry import registry


console = Console()


@click.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option(
    "-o", "--output",
    type=click.Path(),
    default="output_yamls",
    help="Output directory for generated YAML files",
)
@click.option(
    "--env",
    help="Apply environment-specific configuration overlay (e.g. 'prod')",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["dagfactory"]),
    default="dagfactory",
    help="Output format",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Treat warnings as errors",
)
@click.option(
    "--report",
    "report_format",
    type=click.Choice(["text", "json", "none"]),
    default="text",
    help="Validation report format",
)
@click.pass_context
def generate(
    ctx: click.Context,
    input_path: str,
    output: str,
    env: str | None,
    output_format: str,
    strict: bool,
    report_format: str,
) -> None:
    """Generate dag-factory YAML from input files.

    INPUT_PATH can be a single file (.xlsx, .yaml, .json) or a directory
    containing multiple input files.
    """
    dags, result, parse_failed = check_inputs(Path(input_path), env)
    if not dags and not parse_failed and report_format != "json":
        click.echo("No valid input files found.")
        return

    print_report(dags, result, report_format, strict)
    if parse_failed or result.has_errors or (strict and result.warnings):
        if report_format == "none":
            for issue in result.errors + (result.warnings if strict else []):
                click.echo(str(issue), err=True)
        if report_format != "json":
            click.echo("Generation aborted. Fix the reported issues before generating.", err=True)
        ctx.exit(2 if parse_failed else 1)
    if not dags:
        return

    renderer = registry.get_renderer(output_format)()
    output_paths = renderer.render_batch(dags, Path(output))
    if report_format == "json":
        return

    # Summary table
    table = Table(title="Generated Files", show_header=True)
    table.add_column("DAG ID", style="cyan")
    table.add_column("Tasks", justify="right")
    table.add_column("Output File", style="green")

    for dag, path in zip(dags, output_paths):
        table.add_row(dag.dag_id, str(len(dag.tasks)), str(path))

    console.print()
    console.print(table)
    console.print()
    console.print(f"  [bold green]Generated {len(output_paths)} YAML file(s)[/bold green]")
    console.print()
