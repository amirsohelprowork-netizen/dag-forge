"""Operator validator for DAG Forge.

Validates that tasks have the required parameters for their operator type
and warns about unknown or suspicious parameters.
"""

from __future__ import annotations

import logging

from dagforge.core.models import (
    OPERATOR_REQUIRED_PARAMS,
    DagDefinition,
    OperatorType,
    Severity,
    ValidationIssue,
    ValidationResult,
)
from dagforge.core.registry import registry
from dagforge.validators.base import BaseValidator


logger = logging.getLogger(__name__)

# Known optional parameters per operator type
OPERATOR_OPTIONAL_PARAMS: dict[OperatorType, set[str]] = {
    OperatorType.EMPTY: set(),
    OperatorType.BASH: {"env", "append_env", "output_encoding", "skip_on_exit_code", "cwd"},
    OperatorType.PYTHON: {"op_args", "op_kwargs", "templates_dict", "templates_exts"},
    OperatorType.BRANCH_PYTHON: {"op_args", "op_kwargs"},
    OperatorType.SHORT_CIRCUIT: {"op_args", "op_kwargs", "ignore_downstream_trigger_rules"},
    OperatorType.EXTERNAL_TASK_SENSOR: {
        "external_dag_id", "external_task_id", "allowed_states",
        "failed_states", "execution_delta", "execution_date_fn",
    },
    OperatorType.EMAIL: {"cc", "bcc", "mime_subtype", "mime_charset", "files"},
    OperatorType.TRIGGER_DAG_RUN: {
        "conf", "execution_date", "reset_dag_run", "wait_for_completion",
    },
    OperatorType.HTTP: {
        "method", "data", "headers", "response_check", "response_filter",
        "extra_options", "http_conn_id",
    },
    OperatorType.SQL_SENSOR: {
        "success", "failure", "fail_on_empty", "poke_interval", "timeout",
    },
    OperatorType.POSTGRES: {"postgres_conn_id", "autocommit", "parameters", "database"},
    OperatorType.MYSQL: {"mysql_conn_id", "autocommit", "parameters", "database"},
    OperatorType.S3_TO_GCS: {"dest_gcs", "replace", "gzip", "aws_conn_id", "gcp_conn_id"},
    OperatorType.GCS_TO_BIGQUERY: {"source_format", "create_disposition", "write_disposition", "autodetect", "gcp_conn_id"},
    OperatorType.BIGQUERY: {"gcp_conn_id", "location", "job_id"},
    OperatorType.SLACK: {"slack_conn_id", "username", "icon_url"},
    OperatorType.DOCKER: {"api_version", "container_name", "cpus", "docker_url", "environment", "force_pull", "mem_limit"},
    OperatorType.KUBERNETES_POD: {"cmds", "arguments", "ports", "volume_mounts", "volumes", "env_vars", "secrets", "in_cluster", "cluster_context"},
}

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
    """

    def validate(self, dag: DagDefinition) -> ValidationResult:
        """Validate operator parameters for all tasks in a DAG."""
        issues: list[ValidationIssue] = []

        for task in dag.tasks:
            # Check required params
            required = OPERATOR_REQUIRED_PARAMS.get(task.operator, set())
            for param in required:
                if param not in task.operator_params:
                    issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        message=(
                            f"Missing required parameter '{param}' "
                            f"for {task.operator.value} operator"
                        ),
                        dag_id=dag.dag_id,
                        task_id=task.task_id,
                        field=param,
                    ))

            # Check for unknown params (warning only)
            known_params = (
                required
                | OPERATOR_OPTIONAL_PARAMS.get(task.operator, set())
                | COMMON_TASK_PARAMS
            )
            for param in task.operator_params:
                if param not in known_params:
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        message=(
                            f"Unknown parameter '{param}' for "
                            f"{task.operator.value} operator. "
                            "This may be intentional or a typo."
                        ),
                        dag_id=dag.dag_id,
                        task_id=task.task_id,
                        field=param,
                    ))

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
