"""CLI validate command for DAG Forge.

Parses input files and runs all validators without generating output.
Useful for CI/CD pipelines and pre-commit hooks.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from dagforge.core.exceptions import DagForgeError
from dagforge.core.models import ValidationResult
from dagforge.core.registry import registry


logger = logging.getLogger(__name__)
console = Console()


def _detect_parser_name(source: Path) -> str:
    """Auto-detect the appropriate parser based on file extension."""
    for name in registry.available_parsers:
        parser_cls = registry.get_parser(name)
        parser_instance = parser_cls()
        if parser_instance.can_handle(source):
            return name
    raise DagForgeError(
        f"No parser found for file extension '{source.suffix}'. "
        f"Supported formats: {registry.available_parsers}"
    )


def _run_all_validators(dags: list) -> ValidationResult:
    """Run all registered validators."""
    combined = ValidationResult()
    for name in registry.available_validators:
        validator_cls = registry.get_validator(name)
        validator = validator_cls()
        result = validator.validate_batch(dags)
        combined = combined.merge(result)
    return combined


@click.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option(
    "--strict",
    is_flag=True,
    help="Treat warnings as errors (exit code 1)",
)
@click.option(
    "--format",
    "report_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Report output format",
)
@click.pass_context
def validate(
    ctx: click.Context,
    input_path: str,
    strict: bool,
    report_format: str,
) -> None:
    """Validate input files without generating output.

    Runs all parsers and validators, then reports issues.
    Exit code 0 = pass, 1 = validation errors, 2 = parse errors.
    """
    source = Path(input_path)
    verbose = ctx.obj.get("verbose", False)

    console.print()
    console.print(Panel.fit(
        "[bold cyan]DAG Forge[/bold cyan] — Validate",
        subtitle=f"Input: {source}",
    ))
    console.print()

    # Collect files
    files: list[Path] = []
    if source.is_dir():
        for ext in (".xlsx", ".xls", ".yaml", ".yml", ".json"):
            files.extend(source.glob(f"*{ext}"))
        files = [f for f in files if not f.name.startswith("~$")]
    else:
        files = [source]

    if not files:
        console.print("[yellow]No valid input files found.[/yellow]")
        sys.exit(0)

    # Parse
    all_dags = []
    parse_errors = 0

    for file_path in files:
        try:
            parser_name = _detect_parser_name(file_path)
            parser_cls = registry.get_parser(parser_name)
            parser = parser_cls()

            console.print(f"  [bold]>>[/bold] Parsing [cyan]{file_path.name}[/cyan]...")
            result = parser.parse(file_path)
            all_dags.extend(result.dags)

            if result.warnings:
                for w in result.warnings:
                    console.print(f"     [yellow]WARNING:[/yellow] {w}")

        except DagForgeError as e:
            console.print(f"  [red]ERROR: Parse error: {e.message}[/red]")
            parse_errors += 1

    if not all_dags and parse_errors > 0:
        console.print()
        console.print("[red]All files failed to parse.[/red]")
        sys.exit(2)

    # Validate
    console.print()
    console.print("  [bold]>>[/bold] Running validators...")
    validation_result = _run_all_validators(all_dags)

    # Report
    report_cls = registry.get_renderer("report")
    report_renderer = report_cls()

    if report_format == "json":
        report_json = report_renderer.render_report_json(all_dags, validation_result)
        click.echo(report_json)
    else:
        report_text = report_renderer.render_report(all_dags, validation_result)
        console.print()
        console.print(report_text)

    # Exit code
    if validation_result.has_errors:
        sys.exit(1)
    elif strict and validation_result.warnings:
        sys.exit(1)
    else:
        sys.exit(0)
