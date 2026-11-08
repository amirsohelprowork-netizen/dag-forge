"""Validation report renderer for DAG Forge.

Generates structured validation reports in both text and JSON formats,
suitable for terminal display and CI/CD integration.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from dagforge.core.models import (
    DagDefinition,
    Severity,
    ValidationResult,
)
from dagforge.core.registry import registry
from dagforge.renderers.base import BaseRenderer


logger = logging.getLogger(__name__)


@registry.renderer("report")
class ReportRenderer(BaseRenderer):
    """Renders validation reports as structured text.

    Produces a clean, human-readable validation report showing
    errors, warnings, and info messages grouped by DAG.
    """

    @property
    def file_extension(self) -> str:
        return ".txt"

    def render(self, dag: DagDefinition) -> str:
        """Render a placeholder - use render_report() for actual reports."""
        return f"DAG: {dag.dag_id} ({len(dag.tasks)} tasks)"

    def render_report(
        self,
        dags: list[DagDefinition],
        validation_result: ValidationResult,
        *,
        strict: bool = False,
    ) -> str:
        """Render a full validation report.

        Args:
            dags: The DAG definitions that were validated.
            validation_result: The aggregated validation results.

        Returns:
            Formatted text report.
        """
        lines: list[str] = []
        lines.append("=" * 60)
        lines.append("  DAG Forge Validation Report")
        lines.append("=" * 60)
        lines.append("")

        # Summary
        error_count = len(validation_result.errors)
        warning_count = len(validation_result.warnings)
        info_count = len([
            i for i in validation_result.issues if i.severity == Severity.INFO
        ])

        lines.append(f"  DAGs analyzed: {len(dags)}")
        lines.append(f"  Total tasks:   {sum(len(d.tasks) for d in dags)}")
        lines.append(f"  Errors:        {error_count}")
        lines.append(f"  Warnings:      {warning_count}")
        lines.append(f"  Info:          {info_count}")
        lines.append("")

        if not validation_result.issues:
            lines.append("  [PASS] All validations passed!")
            lines.append("")
        else:
            # Group issues by DAG
            by_dag: dict[str, list[str]] = {}
            global_issues: list[str] = []

            for issue in validation_result.issues:
                icon = {
                    Severity.ERROR: "[ERROR]",
                    Severity.WARNING: "[WARN]",
                    Severity.INFO: "[INFO]",
                }[issue.severity]

                parts: list[str] = [icon]
                if issue.task_id:
                    parts.append(f"[{issue.task_id}]")
                if issue.field:
                    parts.append(f"({issue.field})")
                if issue.locations:
                    parts.append(" / ".join(issue.locations))
                parts.append(issue.message)
                formatted = " ".join(parts)

                if issue.dag_id:
                    by_dag.setdefault(issue.dag_id, []).append(formatted)
                else:
                    global_issues.append(formatted)

            # Print global issues
            if global_issues:
                lines.append("  Global Issues:")
                lines.append("  " + "-" * 40)
                for issue_str in global_issues:
                    lines.append(f"    {issue_str}")
                lines.append("")

            # Print per-DAG issues
            for dag_id, dag_issues in sorted(by_dag.items()):
                lines.append(f"  DAG: {dag_id}")
                lines.append("  " + "-" * 40)
                for issue_str in dag_issues:
                    lines.append(f"    {issue_str}")
                lines.append("")

        # Status line
        if validation_result.has_errors or (strict and validation_result.warnings):
            lines.append("  [FAIL] VALIDATION FAILED")
        else:
            lines.append("  [PASS] VALIDATION PASSED")

        lines.append("=" * 60)
        return "\n".join(lines)

    def render_report_json(
        self,
        dags: list[DagDefinition],
        validation_result: ValidationResult,
        *,
        strict: bool = False,
    ) -> str:
        """Render validation report as JSON for CI/CD integration.

        Args:
            dags: The DAG definitions that were validated.
            validation_result: The aggregated validation results.

        Returns:
            JSON string with structured report data.
        """
        report: dict[str, Any] = {
            "summary": {
                "dags_analyzed": len(dags),
                "total_tasks": sum(len(d.tasks) for d in dags),
                "errors": len(validation_result.errors),
                "warnings": len(validation_result.warnings),
                "passed": not (validation_result.has_errors or (strict and validation_result.warnings)),
            },
            "dags": [
                {
                    "dag_id": d.dag_id,
                    "task_count": len(d.tasks),
                    "schedule_type": d.schedule.type.value,
                }
                for d in dags
            ],
            "issues": [
                {
                    "severity": i.severity.value,
                    "message": i.message,
                    "dag_id": i.dag_id,
                    "task_id": i.task_id,
                    "field": i.field,
                    **({"locations": i.locations} if i.locations else {}),
                }
                for i in validation_result.issues
            ],
        }

        return json.dumps(report, indent=2)
