"""Pydantic v2 domain models for DAG Forge.

These models represent the canonical internal representation of DAG configurations.
All parsers produce these models; all validators and renderers consume them.
This is the single source of truth for the data schema.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ScheduleType(str, Enum):
    """Supported schedule types for DAGs."""

    MANUAL = "manual"
    PRESET = "preset"
    CRON = "cron"
    TIMETABLE = "timetable"


class OperatorType(str, Enum):
    """Supported Airflow operator types.

    The value is the short key used in input configs.
    The full_class_path property returns the importable Airflow path.
    """

    EMPTY = "empty"
    BASH = "bash"
    PYTHON = "python"
    BRANCH_PYTHON = "branch_python"
    SHORT_CIRCUIT = "short_circuit"
    EXTERNAL_TASK_SENSOR = "external_task_sensor"
    EMAIL = "email"
    TRIGGER_DAG_RUN = "trigger_dag_run"
    HTTP = "http"
    SQL_SENSOR = "sql_sensor"
    POSTGRES = "postgres"
    MYSQL = "mysql"
    S3_TO_GCS = "s3_to_gcs"
    GCS_TO_BIGQUERY = "gcs_to_bigquery"
    BIGQUERY = "bigquery"
    SLACK = "slack"
    DOCKER = "docker"
    KUBERNETES_POD = "kubernetes_pod"

    @property
    def full_class_path(self) -> str:
        """Return the fully qualified Airflow operator class path."""
        return OPERATOR_CLASS_MAP[self]


OPERATOR_CLASS_MAP: dict[OperatorType, str] = {
    OperatorType.EMPTY: "airflow.operators.empty.EmptyOperator",
    OperatorType.BASH: "airflow.operators.bash.BashOperator",
    OperatorType.PYTHON: "airflow.operators.python.PythonOperator",
    OperatorType.BRANCH_PYTHON: "airflow.operators.python.BranchPythonOperator",
    OperatorType.SHORT_CIRCUIT: "airflow.operators.python.ShortCircuitOperator",
    OperatorType.EXTERNAL_TASK_SENSOR: "airflow.sensors.external_task.ExternalTaskSensor",
    OperatorType.EMAIL: "airflow.operators.email.EmailOperator",
    OperatorType.TRIGGER_DAG_RUN: "airflow.operators.trigger_dagrun.TriggerDagRunOperator",
    OperatorType.HTTP: "airflow.providers.http.operators.http.SimpleHttpOperator",
    OperatorType.SQL_SENSOR: "airflow.sensors.sql.SqlSensor",
    OperatorType.POSTGRES: "airflow.providers.postgres.operators.postgres.PostgresOperator",
    OperatorType.MYSQL: "airflow.providers.mysql.operators.mysql.MySqlOperator",
    OperatorType.S3_TO_GCS: "airflow.providers.google.cloud.transfers.s3_to_gcs.S3ToGCSOperator",
    OperatorType.GCS_TO_BIGQUERY: "airflow.providers.google.cloud.transfers.gcs_to_bigquery.GCSToBigQueryOperator",
    OperatorType.BIGQUERY: "airflow.providers.google.cloud.operators.bigquery.BigQueryInsertJobOperator",
    OperatorType.SLACK: "airflow.providers.slack.operators.slack.SlackAPIPostOperator",
    OperatorType.DOCKER: "airflow.providers.docker.operators.docker.DockerOperator",
    OperatorType.KUBERNETES_POD: "airflow.providers.cncf.kubernetes.operators.pod.KubernetesPodOperator",
}

# Required parameters per operator type (validated by OperatorValidator)
OPERATOR_REQUIRED_PARAMS: dict[OperatorType, set[str]] = {
    OperatorType.EMPTY: set(),
    OperatorType.BASH: {"bash_command"},
    OperatorType.PYTHON: {"python_callable"},
    OperatorType.BRANCH_PYTHON: {"python_callable"},
    OperatorType.SHORT_CIRCUIT: {"python_callable"},
    OperatorType.EXTERNAL_TASK_SENSOR: set(),
    OperatorType.EMAIL: {"to", "subject", "html_content"},
    OperatorType.TRIGGER_DAG_RUN: {"trigger_dag_id"},
    OperatorType.HTTP: {"endpoint"},
    OperatorType.SQL_SENSOR: {"conn_id", "sql"},
    OperatorType.POSTGRES: {"sql"},
    OperatorType.MYSQL: {"sql"},
    OperatorType.S3_TO_GCS: {"source_bucket", "source_object", "destination_bucket"},
    OperatorType.GCS_TO_BIGQUERY: {"bucket", "source_objects", "destination_project_dataset_table"},
    OperatorType.BIGQUERY: {"configuration"},
    OperatorType.SLACK: {"channel", "text"},
    OperatorType.DOCKER: {"image"},
    OperatorType.KUBERNETES_POD: {"name", "namespace", "image"},
}

# Valid Airflow schedule presets
VALID_PRESETS: frozenset[str] = frozenset({
    "once", "hourly", "daily", "weekly", "monthly", "yearly", "annually",
})

# Identifier pattern: alphanumeric + underscores only
IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


# ---------------------------------------------------------------------------
# Validation result model
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    """Severity levels for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    """A single validation issue found during processing."""

    severity: Severity
    message: str
    dag_id: str | None = None
    task_id: str | None = None
    field: str | None = None

    def __str__(self) -> str:
        location_parts: list[str] = []
        if self.dag_id:
            location_parts.append(f"DAG '{self.dag_id}'")
        if self.task_id:
            location_parts.append(f"Task '{self.task_id}'")
        if self.field:
            location_parts.append(f"Field '{self.field}'")
        location = " -> ".join(location_parts) if location_parts else "Global"
        return f"[{self.severity.value.upper()}] {location}: {self.message}"


class ValidationResult(BaseModel):
    """Aggregated validation result across all validators."""

    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Return True if any issues are errors."""
        return any(i.severity == Severity.ERROR for i in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        """Return only error-severity issues."""
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Return only warning-severity issues."""
        return [i for i in self.issues if i.severity == Severity.WARNING]

    def merge(self, other: ValidationResult) -> ValidationResult:
        """Merge another result into this one, returning a new result."""
        return ValidationResult(issues=self.issues + other.issues)


# ---------------------------------------------------------------------------
# Schedule configuration
# ---------------------------------------------------------------------------

class ScheduleConfig(BaseModel):
    """Schedule configuration for a DAG.

    Supports manual (no schedule), preset (@daily, @hourly, etc.),
    cron expressions, and timetable references.
    """

    type: ScheduleType
    expression: str | None = None

    @model_validator(mode="after")
    def validate_schedule_consistency(self) -> ScheduleConfig:
        """Ensure expression is consistent with schedule type."""
        if self.type == ScheduleType.MANUAL:
            if self.expression is not None:
                raise ValueError(
                    f"Manual schedule must not have an expression, got '{self.expression}'"
                )

        elif self.type == ScheduleType.PRESET:
            if self.expression is None:
                raise ValueError("Preset schedule requires an expression")
            normalized = self.expression.lower().lstrip("@")
            if normalized not in VALID_PRESETS:
                raise ValueError(
                    f"Invalid preset '{self.expression}'. "
                    f"Valid options: {', '.join(sorted(VALID_PRESETS))}"
                )
            # Normalize to lowercase without @
            self.expression = normalized

        elif self.type == ScheduleType.CRON:
            if self.expression is None:
                raise ValueError("Cron schedule requires an expression")
            parts = self.expression.strip().split()
            if len(parts) != 5:
                raise ValueError(
                    f"Cron expression must have exactly 5 fields, "
                    f"got {len(parts)}: '{self.expression}'"
                )

        elif self.type == ScheduleType.TIMETABLE:
            if self.expression is None:
                raise ValueError("Timetable schedule requires a class path expression")

        return self

    def to_airflow_schedule(self) -> str | None:
        """Convert to the value used in dag-factory YAML."""
        if self.type == ScheduleType.MANUAL:
            return None
        elif self.type == ScheduleType.PRESET:
            return f"@{self.expression}"
        elif self.type == ScheduleType.CRON:
            return self.expression
        elif self.type == ScheduleType.TIMETABLE:
            return self.expression
        return None


# ---------------------------------------------------------------------------
# Task definition
# ---------------------------------------------------------------------------

class TaskDefinition(BaseModel):
    """A single task within a DAG.

    Represents one Airflow task with its operator type, parameters,
    and upstream dependencies.
    """

    task_id: str = Field(
        ...,
        description="Unique identifier for the task within its DAG",
    )
    operator: OperatorType = Field(
        default=OperatorType.EMPTY,
        description="Airflow operator type",
    )
    operator_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters passed to the operator constructor",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of upstream task_ids this task depends on",
    )

    @model_validator(mode="after")
    def validate_task_id_format(self) -> TaskDefinition:
        """Ensure task_id follows Airflow naming conventions."""
        if not IDENTIFIER_PATTERN.match(self.task_id):
            raise ValueError(
                f"Task ID '{self.task_id}' is invalid. "
                "Must contain only alphanumeric characters and underscores, "
                "and start with a letter or underscore."
            )
        return self


# ---------------------------------------------------------------------------
# DAG definition
# ---------------------------------------------------------------------------

class DagDefinition(BaseModel):
    """Complete definition of a single Airflow DAG.

    This is the primary unit of work in DAG Forge. Each DagDefinition
    maps to one dag-factory YAML output file.
    """

    dag_id: str = Field(
        ...,
        description="Unique identifier for the DAG in Airflow",
    )
    description: str = Field(
        default="",
        description="Human-readable description of the DAG",
    )
    schedule: ScheduleConfig = Field(
        default_factory=lambda: ScheduleConfig(type=ScheduleType.MANUAL),
        description="Schedule configuration",
    )
    default_args: dict[str, Any] = Field(
        default_factory=lambda: {"owner": "airflow", "start_date": "2024-01-01"},
        description="Default arguments passed to all tasks in this DAG",
    )
    catchup: bool = Field(
        default=False,
        description="Whether to backfill missed DAG runs",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for organizing DAGs in the Airflow UI",
    )
    tasks: list[TaskDefinition] = Field(
        default_factory=list,
        description="List of tasks in this DAG",
    )

    @model_validator(mode="after")
    def validate_dag_id_format(self) -> DagDefinition:
        """Ensure dag_id follows Airflow naming conventions."""
        if not IDENTIFIER_PATTERN.match(self.dag_id):
            raise ValueError(
                f"DAG ID '{self.dag_id}' is invalid. "
                "Must contain only alphanumeric characters and underscores, "
                "and start with a letter or underscore."
            )
        return self

    @model_validator(mode="after")
    def validate_unique_task_ids(self) -> DagDefinition:
        """Ensure no duplicate task IDs within this DAG."""
        seen: set[str] = set()
        duplicates: list[str] = []
        for task in self.tasks:
            if task.task_id in seen:
                duplicates.append(task.task_id)
            seen.add(task.task_id)
        if duplicates:
            raise ValueError(
                f"Duplicate task IDs in DAG '{self.dag_id}': {duplicates}"
            )
        return self

    @model_validator(mode="after")
    def validate_dependency_references(self) -> DagDefinition:
        """Ensure all dependency references point to existing tasks."""
        task_ids = {t.task_id for t in self.tasks}
        for task in self.tasks:
            for dep in task.dependencies:
                if dep not in task_ids:
                    raise ValueError(
                        f"Task '{task.task_id}' in DAG '{self.dag_id}' "
                        f"depends on unknown task '{dep}'"
                    )
                if dep == task.task_id:
                    raise ValueError(
                        f"Task '{task.task_id}' in DAG '{self.dag_id}' "
                        f"depends on itself"
                    )
        return self

    def get_task(self, task_id: str) -> TaskDefinition | None:
        """Get a task by its ID, or None if not found."""
        for task in self.tasks:
            if task.task_id == task_id:
                return task
        return None


# ---------------------------------------------------------------------------
# Batch processing result
# ---------------------------------------------------------------------------

class ParseResult(BaseModel):
    """Result of parsing one or more input files."""

    dags: list[DagDefinition] = Field(default_factory=list)
    source: str = Field(default="", description="Source file or description")
    warnings: list[str] = Field(default_factory=list)
