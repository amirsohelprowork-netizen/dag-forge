"""Check DAG Forge inputs without generating output."""

from pathlib import Path

import click

from dagforge.cli.checks import check_inputs, print_report


@click.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--env", help="Apply an environment overlay (e.g. 'prod')")
@click.option("--strict", is_flag=True, help="Treat warnings as errors (exit code 1)")
@click.option(
    "--format",
    "report_format",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Report output format",
)
@click.pass_context
def validate(
    ctx: click.Context, input_path: str, env: str | None, strict: bool, report_format: str
) -> None:
    """Check input files with the same validators and policies as generate.

    Exit code 0 = pass, 1 = validation errors, 2 = parse errors.
    """
    dags, result, parse_failed = check_inputs(Path(input_path), env)
    if not dags and not parse_failed and report_format == "text":
        click.echo("No valid input files found.")
        return

    print_report(dags, result, report_format, strict)
    if parse_failed:
        ctx.exit(2)
    if result.has_errors or (strict and result.warnings):
        ctx.exit(1)
