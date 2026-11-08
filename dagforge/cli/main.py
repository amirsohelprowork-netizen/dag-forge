"""DAG Forge CLI — Main entry point.

Provides the `dagforge` command group with subcommands:
- generate: Parse, validate, and generate dag-factory YAML
- validate: Parse and validate without generating output
- preview: Preview DAG graph in terminal
"""

from __future__ import annotations

import logging
import sys

import click
from rich.console import Console
from rich.logging import RichHandler

from dagforge import __version__
from dagforge.cli.generate import generate
from dagforge.cli.validate import validate
from dagforge.cli.preview import preview
from dagforge.cli.init import init_cmd
from dagforge.cli.template import template_group

# Import parsers/validators/renderers to trigger plugin registration
import dagforge.parsers.excel_parser  # noqa: F401
import dagforge.parsers.yaml_parser  # noqa: F401
import dagforge.parsers.json_parser  # noqa: F401
import dagforge.validators.graph_validator  # noqa: F401
import dagforge.validators.operator_validator  # noqa: F401
import dagforge.validators.schedule_validator  # noqa: F401
import dagforge.validators.schema_validator  # noqa: F401
import dagforge.renderers.dagfactory_renderer  # noqa: F401
import dagforge.renderers.report_renderer  # noqa: F401
import dagforge.policies.builtin_policies  # noqa: F401
from dagforge.core.registry import registry

registry.discover_plugins()


console = Console()


def _setup_logging(verbose: bool) -> None:
    """Configure logging with Rich handler."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(
            console=Console(stderr=True),
            rich_tracebacks=True,
            show_path=verbose,
        )],
    )


@click.group()
@click.version_option(version=__version__, prog_name="dagforge")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """DAG Forge — The Ultimate DAG Factory Development Toolkit.

    Build, validate, and preview Airflow DAGs from Excel, YAML, or JSON.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    _setup_logging(verbose)


# Register subcommands
cli.add_command(validate)
cli.add_command(generate)
cli.add_command(preview)
cli.add_command(init_cmd)
cli.add_command(template_group)


def main() -> None:
    """Main entry point for the CLI."""
    try:
        cli()
    except Exception as e:
        console.print(f"[bold red]Fatal error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
