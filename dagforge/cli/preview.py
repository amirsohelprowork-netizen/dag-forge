"""CLI preview command for DAG Forge.

Parses input files and displays DAG graph structure in the terminal
using ASCII art or Mermaid diagram syntax.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from dagforge.core.exceptions import DagForgeError
from dagforge.core.registry import registry
from dagforge.graph.analyzer import GraphAnalyzer


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


@click.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option(
    "--format",
    "preview_format",
    type=click.Choice(["ascii", "mermaid", "yaml"]),
    default="ascii",
    help="Preview format: ascii (terminal), mermaid (diagram code), yaml (generated YAML)",
)
@click.option(
    "--dag",
    "dag_filter",
    default=None,
    help="Show only a specific DAG by ID",
)
@click.pass_context
def preview(
    ctx: click.Context,
    input_path: str,
    preview_format: str,
    dag_filter: str | None,
) -> None:
    """Preview DAG structure in the terminal.

    Shows the dependency graph, execution order, critical path,
    and key metadata for each DAG in the input file.
    """
    source = Path(input_path)
    verbose = ctx.obj.get("verbose", False)

    console.print()
    console.print(Panel.fit(
        "[bold cyan]DAG Forge[/bold cyan] — Preview",
        subtitle=f"Input: {source}",
    ))
    console.print()

    # Parse
    try:
        parser_name = _detect_parser_name(source)
        parser_cls = registry.get_parser(parser_name)
        parser = parser_cls()
        result = parser.parse(source)
    except DagForgeError as e:
        click.echo(f"ERROR: {e.message}", err=True)
        for detail in e.details:
            click.echo(detail, err=True)
        sys.exit(2)

    if not result.dags:
        console.print("[yellow]No DAGs found in input file.[/yellow]")
        sys.exit(0)

    # Filter if requested
    dags = result.dags
    if dag_filter:
        dags = [d for d in dags if d.dag_id == dag_filter]
        if not dags:
            console.print(f"[yellow]DAG '{dag_filter}' not found.[/yellow]")
            available = [d.dag_id for d in result.dags]
            console.print(f"  Available DAGs: {', '.join(available)}")
            sys.exit(0)

    # Display based on format
    for dag in dags:
        analyzer = GraphAnalyzer(dag)

        if preview_format == "ascii":
            ascii_graph = analyzer.to_ascii()
            console.print(Panel(
                ascii_graph,
                title=f"[bold]{dag.dag_id}[/bold]",
                border_style="cyan",
                padding=(1, 2),
            ))
            console.print()

        elif preview_format == "mermaid":
            mermaid = analyzer.to_mermaid()
            syntax = Syntax(mermaid, "text", theme="monokai", line_numbers=False)
            console.print(Panel(
                syntax,
                title=f"[bold]{dag.dag_id}[/bold] — Mermaid Diagram",
                border_style="cyan",
                padding=(1, 2),
            ))
            console.print()

        elif preview_format == "yaml":
            renderer_cls = registry.get_renderer("dagfactory")
            renderer = renderer_cls()
            yaml_str = renderer.render(dag)
            syntax = Syntax(yaml_str, "yaml", theme="monokai", line_numbers=True)
            console.print(Panel(
                syntax,
                title=f"[bold]{dag.dag_id}[/bold] — dag-factory YAML",
                border_style="cyan",
                padding=(1, 2),
            ))
            console.print()

    console.print(f"  Previewed [bold]{len(dags)}[/bold] DAG(s)")
    console.print()
