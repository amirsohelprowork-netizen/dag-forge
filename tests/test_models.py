"""Tests for DAG Forge domain models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from dagforge.core.models import (
    DagDefinition,
    OperatorType,
    ScheduleConfig,
    ScheduleType,
    Severity,
    TaskDefinition,
    ValidationIssue,
    ValidationResult,
)


# -----------------------------------------------------------------------
# ScheduleConfig tests
# -----------------------------------------------------------------------

class TestScheduleConfig:
    """Tests for ScheduleConfig model."""

    def test_manual_schedule(self):
        config = ScheduleConfig(type=ScheduleType.MANUAL)
        assert config.expression is None
        assert config.to_airflow_schedule() is None

    def test_manual_with_expression_fails(self):
        with pytest.raises(ValidationError):
            ScheduleConfig(type=ScheduleType.MANUAL, expression="@daily")

    def test_preset_daily(self):
        config = ScheduleConfig(type=ScheduleType.PRESET, expression="daily")
        assert config.to_airflow_schedule() == "@daily"

    def test_preset_with_at_sign(self):
        config = ScheduleConfig(type=ScheduleType.PRESET, expression="@hourly")
        assert config.expression == "hourly"
        assert config.to_airflow_schedule() == "@hourly"

    def test_preset_invalid(self):
        with pytest.raises(ValidationError):
            ScheduleConfig(type=ScheduleType.PRESET, expression="every_5_minutes")

    def test_preset_missing_expression(self):
        with pytest.raises(ValidationError):
            ScheduleConfig(type=ScheduleType.PRESET, expression=None)

    def test_cron_valid(self):
        config = ScheduleConfig(type=ScheduleType.CRON, expression="0 6 * * *")
        assert config.to_airflow_schedule() == "0 6 * * *"

    def test_cron_invalid_fields(self):
        with pytest.raises(ValidationError):
            ScheduleConfig(type=ScheduleType.CRON, expression="0 6 *")

    def test_cron_missing_expression(self):
        with pytest.raises(ValidationError):
            ScheduleConfig(type=ScheduleType.CRON, expression=None)

    def test_all_valid_presets(self):
        for preset in ["once", "hourly", "daily", "weekly", "monthly", "yearly", "annually"]:
            config = ScheduleConfig(type=ScheduleType.PRESET, expression=preset)
            assert config.to_airflow_schedule() == f"@{preset}"


# -----------------------------------------------------------------------
# TaskDefinition tests
# -----------------------------------------------------------------------

class TestTaskDefinition:
    """Tests for TaskDefinition model."""

    def test_valid_task(self):
        task = TaskDefinition(
            task_id="my_task",
            operator=OperatorType.BASH,
            operator_params={"bash_command": "echo hello"},
        )
        assert task.task_id == "my_task"
        assert task.operator == OperatorType.BASH

    def test_task_with_underscores(self):
        task = TaskDefinition(task_id="my_task_123")
        assert task.task_id == "my_task_123"

    def test_task_invalid_characters(self):
        with pytest.raises(ValidationError):
            TaskDefinition(task_id="my task")  # spaces not allowed

    def test_task_special_characters(self):
        with pytest.raises(ValidationError):
            TaskDefinition(task_id="my-task")  # hyphens not allowed

    def test_task_default_operator(self):
        task = TaskDefinition(task_id="test")
        assert task.operator == OperatorType.EMPTY

    def test_task_empty_dependencies(self):
        task = TaskDefinition(task_id="test")
        assert task.dependencies == []


# -----------------------------------------------------------------------
# DagDefinition tests
# -----------------------------------------------------------------------

class TestDagDefinition:
    """Tests for DagDefinition model."""

    def test_valid_dag(self, simple_dag):
        assert simple_dag.dag_id == "test_simple_dag"
        assert len(simple_dag.tasks) == 3

    def test_dag_invalid_id(self):
        with pytest.raises(ValidationError):
            DagDefinition(dag_id="my dag", tasks=[])

    def test_dag_duplicate_task_ids(self):
        with pytest.raises(ValidationError):
            DagDefinition(
                dag_id="test",
                tasks=[
                    TaskDefinition(task_id="task_a"),
                    TaskDefinition(task_id="task_a"),
                ],
            )

    def test_dag_invalid_dependency_ref(self):
        with pytest.raises(ValidationError):
            DagDefinition(
                dag_id="test",
                tasks=[
                    TaskDefinition(
                        task_id="task_a",
                        dependencies=["nonexistent"],
                    ),
                ],
            )

    def test_dag_self_dependency(self):
        with pytest.raises(ValidationError):
            DagDefinition(
                dag_id="test",
                tasks=[
                    TaskDefinition(
                        task_id="task_a",
                        dependencies=["task_a"],
                    ),
                ],
            )

    def test_dag_get_task(self, simple_dag):
        task = simple_dag.get_task("process")
        assert task is not None
        assert task.operator == OperatorType.BASH

    def test_dag_get_task_not_found(self, simple_dag):
        assert simple_dag.get_task("nonexistent") is None

    def test_dag_default_args(self):
        dag = DagDefinition(dag_id="test", tasks=[])
        assert dag.default_args["owner"] == "airflow"

    def test_dag_default_schedule(self):
        dag = DagDefinition(dag_id="test", tasks=[])
        assert dag.schedule.type == ScheduleType.MANUAL


# -----------------------------------------------------------------------
# OperatorType tests
# -----------------------------------------------------------------------

class TestOperatorType:
    """Tests for OperatorType enum."""

    def test_full_class_paths(self):
        assert OperatorType.EMPTY.full_class_path == "airflow.operators.empty.EmptyOperator"
        assert OperatorType.BASH.full_class_path == "airflow.operators.bash.BashOperator"
        assert OperatorType.PYTHON.full_class_path == "airflow.operators.python.PythonOperator"

    def test_all_operators_have_class_paths(self):
        for op in OperatorType:
            assert op.full_class_path, f"Missing class path for {op}"


# -----------------------------------------------------------------------
# ValidationResult tests
# -----------------------------------------------------------------------

class TestValidationResult:
    """Tests for ValidationResult model."""

    def test_empty_result(self):
        result = ValidationResult()
        assert not result.has_errors
        assert result.errors == []
        assert result.warnings == []

    def test_result_with_errors(self):
        result = ValidationResult(issues=[
            ValidationIssue(severity=Severity.ERROR, message="bad"),
            ValidationIssue(severity=Severity.WARNING, message="meh"),
        ])
        assert result.has_errors
        assert len(result.errors) == 1
        assert len(result.warnings) == 1

    def test_merge_results(self):
        r1 = ValidationResult(issues=[
            ValidationIssue(severity=Severity.ERROR, message="err1"),
        ])
        r2 = ValidationResult(issues=[
            ValidationIssue(severity=Severity.WARNING, message="warn1"),
        ])
        merged = r1.merge(r2)
        assert len(merged.issues) == 2
        assert merged.has_errors

    def test_issue_string_formatting(self):
        issue = ValidationIssue(
            severity=Severity.ERROR,
            message="something broke",
            dag_id="my_dag",
            task_id="my_task",
        )
        formatted = str(issue)
        assert "ERROR" in formatted
        assert "my_dag" in formatted
        assert "my_task" in formatted
