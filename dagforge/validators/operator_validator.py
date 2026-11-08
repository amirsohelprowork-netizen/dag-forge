"""Operator validator for DAG Forge.

Validates that tasks have the required parameters for their operator type
and warns about unknown or suspicious parameters.  All operator metadata
is fetched from the ``dagforge.operators`` registry.
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
from dagforge.operators import operator_registry
from dagforge.validators.base import BaseValidator


logger = logging.getLogger(__name__)

# Common Airflow task-level parameters (apply to any operator)
COMMON_TASK_PARAMS: set[str] = {
    "retries", "retry_delay", "retry_exponential_backoff", "max_retry_delay",
    "pool", "pool_slots", "priority_weight", "weight_rule",
    "queue", "executor_config", "run_as_user",
    "timeout", "execution_timeout", "sla",
    "trigger_rule", "depends_on_past", "wait_for_downstream",
    "email", "email_on_failure", "email_on_retry",
    "on_failure_callback", "on_success_callback", "on_retry_callback",
    "task_concurrency", "max_active_tis_per_dag",
    "doc", "doc_md", "doc_json", "doc_yaml", "doc_rst",
    "outlets", "inlets",
}


@registry.validator("operator")
class OperatorValidator(BaseValidator):
    """Validates operator-specific parameters for each task.

    Checks:
    - Required parameters are present for the operator type
    - Warns about unknown parameters that might be typos
    - Validates parameter value types where possible
    - Validates nested parameter structure when specs define nested params
    """

    def validate(self, dag: DagDefinition) -> ValidationResult:
        """Validate operator parameters for all tasks in a DAG."""
        issues: list[ValidationIssue] = []

        for task in dag.tasks:
            # Resolve the operator spec from the registry
            try:
                op_spec = operator_registry.get(task.operator)
            except KeyError:
                issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    message=(
                        f"Unknown operator '{task.operator}'. "
                        "Cannot validate parameters."
                    ),
                    dag_id=dag.dag_id,
                    task_id=task.task_id,
                ))
                continue

            # Check required params
            for param in op_spec.required_params:
                if task.operator_params.get(param) in (None, ""):
                    issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        message=(
                            f"Missing required parameter '{param}' "
                            f"for {task.operator} operator"
                        ),
                        dag_id=dag.dag_id,
                        task_id=task.task_id,
                        field=param,
                    ))

            # Check for unknown params (warning only)
            known_params = op_spec.all_param_names | COMMON_TASK_PARAMS
            for param in task.operator_params:
                if param not in known_params:
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        message=(
                            f"Unknown parameter '{param}' for "
                            f"{task.operator} operator. "
                            "This may be intentional or a typo."
                        ),
                        dag_id=dag.dag_id,
                        task_id=task.task_id,
                        field=param,
                    ))

            # Validate nested parameter structure
            for param_name, param_value in task.operator_params.items():
                param_spec = op_spec.get_param(param_name)
                if (
                    param_spec
                    and param_spec.nested
                    and isinstance(param_value, dict)
                ):
                    self._validate_nested(
                        param_value,
                        param_spec.nested,
                        dag.dag_id,
                        task.task_id,
                        param_name,
                        issues,
                    )

            # Validate retries is a positive integer
            retries = task.operator_params.get("retries")
            if retries is not None:
                try:
                    retries_int = int(retries)
                    if retries_int < 0:
                        issues.append(ValidationIssue(
                            severity=Severity.ERROR,
                            message=f"'retries' must be non-negative, got {retries_int}",
                            dag_id=dag.dag_id,
                            task_id=task.task_id,
                            field="retries",
                        ))
                except (ValueError, TypeError):
                    issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        message=f"'retries' must be an integer, got '{retries}'",
                        dag_id=dag.dag_id,
                        task_id=task.task_id,
                        field="retries",
                    ))

            # Validate trigger_rule values
            trigger_rule = task.operator_params.get("trigger_rule")
            if trigger_rule is not None:
                valid_rules = {
                    "all_success", "all_failed", "all_done",
                    "one_success", "one_failed", "one_done",
                    "none_failed", "none_failed_min_one_success",
                    "none_skipped", "always", "dummy",
                }
                if str(trigger_rule).lower() not in valid_rules:
                    issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        message=(
                            f"Invalid trigger_rule '{trigger_rule}'. "
                            f"Valid options: {', '.join(sorted(valid_rules))}"
                        ),
                        dag_id=dag.dag_id,
                        task_id=task.task_id,
                        field="trigger_rule",
                    ))

        return ValidationResult(issues=issues)

    @staticmethod
    def _validate_nested(
        value: dict,
        nested_specs: dict,
        dag_id: str,
        task_id: str,
        parent_path: str,
        issues: list[ValidationIssue],
    ) -> None:
        """Recursively validate nested parameter structure."""
        for key, sub_value in value.items():
            if key in nested_specs:
                sub_spec = nested_specs[key]
                if sub_spec.nested and isinstance(sub_value, dict):
                    OperatorValidator._validate_nested(
                        sub_value,
                        sub_spec.nested,
                        dag_id,
                        task_id,
                        f"{parent_path}.{key}",
                        issues,
                    )
