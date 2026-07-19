"""CLI generate command for DAG Forge.

Parses input files, validates them, and generates dag-factory YAML output.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from dagforge.core.exceptions import DagForgeError, ParseError
from dagforge.core.models import ParseResult, ValidationResult
from dagforge.core.registry import registry
from dagforge.core.environment import EnvironmentManager
from dagforge.core.config import ForgeConfig
from dagforge.policies.engine import PolicyEngine


logger = logging.getLogger(__name__)
console = Console()


def _detect_parser_name(source: Path) -> str:
    """Auto-detect the appropriate parser based on file extension."""
    ext = source.suffix.lower()
    for name in registry.available_parsers:
        parser_cls = registry.get_parser(name)
        parser_instance = parser_cls()
        if parser_instance.can_handle(source):
            return name
    raise ParseError(
        f"No parser found for file extension '{ext}'. "
        f"Supported formats: {registry.available_parsers}",
        source=str(source),
    )


def _run_all_validators(dags: list) -> ValidationResult:
    """Run all registered validators against the parsed DAGs."""
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
    source = Path(input_path)
    output_dir = Path(output)
    verbose = ctx.obj.get("verbose", False)

    console.print()
    console.print(Panel.fit(
        "[bold cyan]DAG Forge[/bold cyan] — Generate",
        subtitle=f"Input: {source}",
    ))
    console.print()

    # Collect input files
    files: list[Path] = []
    if source.is_dir():
        for ext in (".xlsx", ".xls", ".yaml", ".yml", ".json"):
            files.extend(source.glob(f"*{ext}"))
        # Filter out Excel temp files
        files = [f for f in files if not f.name.startswith("~$")]
    else:
        files = [source]

    if not files:
        console.print("[yellow]No valid input files found.[/yellow]")
        sys.exit(0)

    console.print(f"  Found [bold]{len(files)}[/bold] input file(s)")
    console.print()

    # Parse all files
    all_dags = []
    all_warnings: list[str] = []

    for file_path in files:
        try:
            parser_name = _detect_parser_name(file_path)
            parser_cls = registry.get_parser(parser_name)
            parser = parser_cls()

            console.print(f"  [bold]>>[/bold] Parsing [cyan]{file_path.name}[/cyan] ({parser_name})...")
            result = parser.parse(file_path)

            all_dags.extend(result.dags)
            all_warnings.extend(result.warnings)

            console.print(f"     -> Found [bold]{len(result.dags)}[/bold] DAG(s)")
            if result.warnings:
                for w in result.warnings:
                    console.print(f"     [yellow]WARNING:[/yellow] {w}")

        except DagForgeError as e:
            console.print(f"  [red]ERROR: Error parsing {file_path.name}: {e.message}[/red]")
            if e.details:
                for detail in e.details:
                    console.print(f"       {detail}")
            continue

    if not all_dags:
        console.print()
        console.print("[red]No valid DAGs found across all input files.[/red]")
        sys.exit(2)

    # Apply Environment overlays if specified
    config = ForgeConfig.load()
    if env:
        env_manager = EnvironmentManager(env, config.environments)
        for dag in all_dags:
            env_manager.apply(dag)

    console.print()

    # Validate
    console.print("  [bold]>>[/bold] Running validators...\n")
    validation_result = _run_all_validators(all_dags)
    
    # Run Policies
    policy_engine = PolicyEngine(config.policies)
    policy_violations = policy_engine.evaluate(all_dags)
    
    # Convert policy violations to validation issues for reporting
    from dagforge.core.models import ValidationIssue
    for pv in policy_violations:
        validation_result.issues.append(
            ValidationIssue(
                severity=pv.severity,
                message=f"[POLICY {pv.rule_id}] {pv.message}",
                dag_id=pv.dag_id,
                task_id=pv.task_id
            )
        )

    # Show validation report
    if report_format == "text":
        report_cls = registry.get_renderer("report")
        report_renderer = report_cls()
        report_text = report_renderer.render_report(all_dags, validation_result)
        console.print()
        console.print(report_text)
        console.print()
    elif report_format == "json":
        report_cls = registry.get_renderer("report")
        report_renderer = report_cls()
        report_json = report_renderer.render_report_json(all_dags, validation_result)
        click.echo(report_json)

    # Check for errors
    if validation_result.has_errors:
        console.print("[bold red]Generation aborted due to validation errors.[/bold red]")
        sys.exit(1)

    if strict and validation_result.warnings:
        console.print(
            "[bold red]Generation aborted: warnings treated as errors (--strict).[/bold red]"
        )
        sys.exit(1)

    # Generate output
    console.print(f"  [bold]>>[/bold] Generating {output_format} YAML...")
    renderer_cls = registry.get_renderer(output_format)
    renderer = renderer_cls()
    output_paths = renderer.render_batch(all_dags, output_dir)

    # Summary table
    table = Table(title="Generated Files", show_header=True)
    table.add_column("DAG ID", style="cyan")
    table.add_column("Tasks", justify="right")
    table.add_column("Output File", style="green")

    for dag, path in zip(all_dags, output_paths):
        table.add_row(dag.dag_id, str(len(dag.tasks)), str(path))

    console.print()
    console.print(table)
    console.print()
    console.print(f"  [bold green]OK: Successfully generated {len(output_paths)} YAML file(s)[/bold green]")
    console.print()
