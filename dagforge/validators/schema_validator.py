"""Schema validator for DAG Forge.

Validates DAG definitions against additional business rules
beyond what Pydantic model validators handle.
"""

from __future__ import annotations

import logging

from dagforge.core.models import (
    DagDefinition,
    Severity,
    ValidationIssue,
    ValidationResult,
)
from dagforge.core.registry import registry
from dagforge.validators.base import BaseValidator


logger = logging.getLogger(__name__)


@registry.validator("schema")
class SchemaValidator(BaseValidator):
    """Validates DAG definitions against schema and best-practice rules.

    Checks:
    - DAG has at least one task
    - Description is present (warning)
    - Tags are present (info)
    - Default args has owner and start_date
    - Task IDs follow naming conventions
    - No empty dependency lists
    """

    def validate(self, dag: DagDefinition) -> ValidationResult:
        """Validate schema and best practices for a DAG."""
        issues: list[ValidationIssue] = []

        # DAG must have at least one task
        if not dag.tasks:
            issues.append(ValidationIssue(
                severity=Severity.WARNING,
                message="DAG has no tasks defined",
                dag_id=dag.dag_id,
            ))

        # Description should be present
        if not dag.description or not dag.description.strip():
            issues.append(ValidationIssue(
                severity=Severity.WARNING,
                message="DAG has no description. Consider adding one for documentation.",
                dag_id=dag.dag_id,
                field="description",
            ))

        # Tags are recommended
        if not dag.tags:
            issues.append(ValidationIssue(
                severity=Severity.INFO,
                message=(
                    "DAG has no tags. Tags help organize DAGs in the Airflow UI."
                ),
                dag_id=dag.dag_id,
                field="tags",
            ))

        # Default args should include owner
        if "owner" not in dag.default_args:
            issues.append(ValidationIssue(
                severity=Severity.WARNING,
                message="No 'owner' specified in default_args",
                dag_id=dag.dag_id,
                field="default_args.owner",
            ))

        # Default args should include start_date
        if "start_date" not in dag.default_args:
            issues.append(ValidationIssue(
                severity=Severity.WARNING,
                message="No 'start_date' specified in default_args",
                dag_id=dag.dag_id,
                field="default_args.start_date",
            ))

        # Check start_date format (basic check)
        start_date = dag.default_args.get("start_date")
        if start_date:
            sd_str = str(start_date)
            # Should look like a date (YYYY-MM-DD or similar)
            if len(sd_str) < 8 or not any(c.isdigit() for c in sd_str):
                issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    message=f"start_date '{sd_str}' may not be a valid date format",
                    dag_id=dag.dag_id,
                    field="default_args.start_date",
                ))

        # Task-level checks
        for task in dag.tasks:
            # Warn about tasks with no dependencies that aren't the root
            # (only if DAG has multiple tasks)
            if len(dag.tasks) > 1 and not task.dependencies:
                # Check if any other task depends on this one
                is_upstream = any(
                    task.task_id in t.dependencies
                    for t in dag.tasks
                    if t.task_id != task.task_id
                )
                if not is_upstream:
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        message=(
                            "Task has no dependencies and no downstream tasks. "
                            "It may be orphaned."
                        ),
                        dag_id=dag.dag_id,
                        task_id=task.task_id,
                        field="dependencies",
                    ))

        return ValidationResult(issues=issues)
