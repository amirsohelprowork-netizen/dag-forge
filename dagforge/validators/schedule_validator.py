"""Schedule validator for DAG Forge.

Validates schedule configurations including cron expressions,
preset names, and schedule/catchup consistency.
"""

from __future__ import annotations

import logging
import re

from dagforge.core.models import (
    VALID_PRESETS,
    DagDefinition,
    ScheduleType,
    Severity,
    ValidationIssue,
    ValidationResult,
)
from dagforge.core.registry import registry
from dagforge.validators.base import BaseValidator


logger = logging.getLogger(__name__)

# Regex patterns for basic cron field validation
CRON_FIELD_PATTERNS = [
    re.compile(r"^(\*|([0-9]|[1-5][0-9])([-/][0-9]+)*)(,(\*|([0-9]|[1-5][0-9])([-/][0-9]+)*))*$"),  # minute (0-59)
    re.compile(r"^(\*|([0-9]|1[0-9]|2[0-3])([-/][0-9]+)*)(,(\*|([0-9]|1[0-9]|2[0-3])([-/][0-9]+)*))*$"),  # hour (0-23)
    re.compile(r"^(\*|([1-9]|[12][0-9]|3[01])([-/][0-9]+)*)(,(\*|([1-9]|[12][0-9]|3[01])([-/][0-9]+)*))*$"),  # day (1-31)
    re.compile(r"^(\*|([1-9]|1[0-2])([-/][0-9]+)*)(,(\*|([1-9]|1[0-2])([-/][0-9]+)*))*$"),  # month (1-12)
    re.compile(r"^(\*|[0-6]([-/][0-6])*)(,(\*|[0-6]([-/][0-6])*))*$"),  # dow (0-6)
]


def _validate_cron_expression(expr: str) -> list[str]:
    """Validate a cron expression and return any errors found."""
    errors: list[str] = []
    parts = expr.strip().split()

    if len(parts) != 5:
        errors.append(f"Cron expression must have exactly 5 fields, got {len(parts)}")
        return errors

    field_names = ["minute", "hour", "day-of-month", "month", "day-of-week"]

    for i, (part, pattern, name) in enumerate(
        zip(parts, CRON_FIELD_PATTERNS, field_names)
    ):
        # Allow wildcards with step values like */5
        if part == "*" or re.match(r"^\*/[0-9]+$", part):
            continue
        if not pattern.match(part):
            errors.append(f"Invalid {name} field: '{part}'")

    return errors


@registry.validator("schedule")
class ScheduleValidator(BaseValidator):
    """Validates schedule configurations for DAGs.

    Checks:
    - Cron expression syntax validity
    - Preset name validity
    - Schedule type consistency
    - Catchup + manual schedule warning
    """

    def validate(self, dag: DagDefinition) -> ValidationResult:
        """Validate the schedule configuration of a DAG."""
        issues: list[ValidationIssue] = []
        schedule = dag.schedule

        # Manual schedule checks
        if schedule.type == ScheduleType.MANUAL:
            if dag.catchup:
                issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    message=(
                        "catchup=True has no effect on a manually triggered DAG"
                    ),
                    dag_id=dag.dag_id,
                    field="catchup",
                ))

        # Preset validation
        elif schedule.type == ScheduleType.PRESET:
            if schedule.expression is None:
                issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    message="Preset schedule requires an expression",
                    dag_id=dag.dag_id,
                    field="schedule.expression",
                ))
            else:
                normalized = schedule.expression.lower().lstrip("@")
                if normalized not in VALID_PRESETS:
                    issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        message=(
                            f"Invalid preset '{schedule.expression}'. "
                            f"Valid options: {', '.join(sorted(VALID_PRESETS))}"
                        ),
                        dag_id=dag.dag_id,
                        field="schedule.expression",
                    ))

        # Cron validation
        elif schedule.type == ScheduleType.CRON:
            if schedule.expression is None:
                issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    message="Cron schedule requires an expression",
                    dag_id=dag.dag_id,
                    field="schedule.expression",
                ))
            else:
                cron_errors = _validate_cron_expression(schedule.expression)
                for err in cron_errors:
                    issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        message=err,
                        dag_id=dag.dag_id,
                        field="schedule.expression",
                    ))

                # Warn about very frequent schedules
                parts = schedule.expression.strip().split()
                if len(parts) == 5 and parts[0] == "*" and parts[1] == "*":
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        message=(
                            "Schedule runs every minute. "
                            "This is unusual for production DAGs."
                        ),
                        dag_id=dag.dag_id,
                        field="schedule.expression",
                    ))

        # Timetable validation
        elif schedule.type == ScheduleType.TIMETABLE:
            if schedule.expression is None:
                issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    message="Timetable schedule requires a class path expression",
                    dag_id=dag.dag_id,
                    field="schedule.expression",
                ))

        return ValidationResult(issues=issues)
