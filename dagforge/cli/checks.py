"""Shared input and validation workflow for validate and generate."""

from collections import defaultdict
from pathlib import Path

import click
from rich.console import Console

from dagforge.core.config import ForgeConfig
from dagforge.core.environment import EnvironmentManager
from dagforge.core.exceptions import DagForgeError, ParseError
from dagforge.core.models import (
    DagDefinition,
    ParseResult,
    Severity,
    ValidationIssue,
    ValidationResult,
)
from dagforge.core.registry import registry
from dagforge.policies.engine import PolicyEngine


def _parse_file(source: Path) -> ParseResult:
    for name in registry.available_parsers:
        parser = registry.get_parser(name)()
        if parser.can_handle(source):
            result = parser.parse(source)
            if not result.dags:
                raise ParseError("No DAG definitions found", details=result.warnings)
            return result
    raise ParseError(f"No parser found for file extension '{source.suffix}'")


def check_inputs(
    source: Path, env: str | None
) -> tuple[list[DagDefinition], ValidationResult, bool]:
    """Parse inputs, apply an overlay, and run validators and configured policies."""
    files = [source]
    if source.is_dir():
        files = sorted(
            path for path in source.iterdir()
            if path.is_file()
            and path.suffix.lower() in {".xlsx", ".xls", ".yaml", ".yml", ".json"}
            and not path.name.startswith("~$")
        )

    dags: list[DagDefinition] = []
    result = ValidationResult()
    locations: dict[tuple[str, str | None, str | None], list[str]] = defaultdict(list)
    parse_failed = False
    for path in files:
        try:
            parsed = _parse_file(path)
        except DagForgeError as exc:
            parse_failed = True
            result.issues.extend(
                ValidationIssue(
                    severity=Severity.ERROR,
                    message=f"Parse error: {message}",
                    locations=[str(path)],
                )
                for message in (exc.details or [exc.message])
            )
            continue

        dags.extend(parsed.dags)
        for key, cells in parsed.locations.items():
            locations[key].extend(cells)
        for dag in parsed.dags:
            key = (dag.dag_id, None, None)
            if key not in parsed.locations:
                locations[key].append(str(path))
        result.issues.extend(
            ValidationIssue(severity=Severity.WARNING, message=warning, locations=[str(path)])
            for warning in parsed.warnings
        )

    if not dags:
        return dags, result, parse_failed

    config = ForgeConfig.load()
    if env:
        manager = EnvironmentManager(env, config.environments)
        for dag in dags:
            manager.apply(dag)

    checks = ValidationResult()
    for name in registry.available_validators:
        validator = registry.get_validator(name)()
        checks = checks.merge(validator.validate_batch(dags))

    for violation in PolicyEngine(config.policies).evaluate(dags):
        checks.issues.append(ValidationIssue(
            severity=violation.severity,
            message=f"[POLICY {violation.rule_id}] {violation.message}",
            dag_id=violation.dag_id,
            task_id=violation.task_id,
            field=violation.field,
        ))

    for issue in checks.issues:
        if issue.dag_id is not None:
            origins = locations.get((issue.dag_id, None, None), [])
            if len(origins) > 1:
                # Duplicate IDs make field locations ambiguous across definitions.
                issue.locations = origins
            else:
                issue.locations = (
                    locations.get((issue.dag_id, issue.task_id, issue.field))
                    or locations.get((issue.dag_id, issue.task_id, None))
                    or origins
                )
    return dags, result.merge(checks), parse_failed


def print_report(
    dags: list[DagDefinition], result: ValidationResult, report_format: str, strict: bool
) -> None:
    if report_format == "none":
        return
    renderer = registry.get_renderer("report")()
    if report_format == "json":
        click.echo(renderer.render_report_json(dags, result, strict=strict))
    else:
        Console().print(renderer.render_report(dags, result, strict=strict), markup=False)
