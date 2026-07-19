"""Tests for DAG Forge validators."""

from __future__ import annotations

import pytest

from dagforge.core.models import (
    DagDefinition,
    OperatorType,
    ScheduleConfig,
    ScheduleType,
    Severity,
    TaskDefinition,
    ValidationResult,
)

# Import to trigger registration
import dagforge.validators.graph_validator  # noqa: F401
import dagforge.validators.operator_validator  # noqa: F401
import dagforge.validators.schedule_validator  # noqa: F401
import dagforge.validators.schema_validator  # noqa: F401

from dagforge.validators.graph_validator import GraphValidator
from dagforge.validators.operator_validator import OperatorValidator
from dagforge.validators.schedule_validator import ScheduleValidator
from dagforge.validators.schema_validator import SchemaValidator


# -----------------------------------------------------------------------
# GraphValidator tests
# -----------------------------------------------------------------------

class TestGraphValidator:
    """Tests for the graph dependency validator."""

    def setup_method(self):
        self.validator = GraphValidator()

    def test_valid_linear_dag(self, simple_dag):
        result = self.validator.validate(simple_dag)
        assert not result.has_errors

    def test_valid_complex_dag(self, complex_dag):
        result = self.validator.validate(complex_dag)
        assert not result.has_errors

    def test_empty_dag_valid(self, empty_dag):
        result = self.validator.validate(empty_dag)
        assert not result.has_errors

    def test_detects_disconnected_tasks(self):
        dag = DagDefinition(
            dag_id="disconnected",
            tasks=[
                TaskDefinition(task_id="task_a"),
                TaskDefinition(task_id="task_b"),
                TaskDefinition(task_id="task_c", dependencies=["task_a"]),
            ],
        )
        result = self.validator.validate(dag)
        warnings = [i for i in result.issues if i.severity == Severity.WARNING]
        assert len(warnings) >= 1
        assert "disconnected" in warnings[0].message.lower()

    def test_detects_duplicate_dag_ids_in_batch(self):
        dag1 = DagDefinition(dag_id="same_id", tasks=[])
        dag2 = DagDefinition(dag_id="same_id", tasks=[])
        result = self.validator.validate_batch([dag1, dag2])
        errors = result.errors
        assert len(errors) >= 1
        assert "duplicate" in errors[0].message.lower()


# -----------------------------------------------------------------------
# OperatorValidator tests
# -----------------------------------------------------------------------

class TestOperatorValidator:
    """Tests for the operator parameter validator."""

    def setup_method(self):
        self.validator = OperatorValidator()

    def test_valid_bash_task(self, simple_dag):
        result = self.validator.validate(simple_dag)
        assert not result.has_errors

    def test_bash_missing_command(self):
        dag = DagDefinition(
            dag_id="test",
            tasks=[
                TaskDefinition(
                    task_id="bad_bash",
                    operator=OperatorType.BASH,
                    operator_params={},  # Missing bash_command!
                ),
            ],
        )
        result = self.validator.validate(dag)
        assert result.has_errors
        assert any("bash_command" in e.message for e in result.errors)

    def test_python_missing_callable(self):
        dag = DagDefinition(
            dag_id="test",
            tasks=[
                TaskDefinition(
                    task_id="bad_python",
                    operator=OperatorType.PYTHON,
                    operator_params={},
                ),
            ],
        )
        result = self.validator.validate(dag)
        assert result.has_errors
        assert any("python_callable" in e.message for e in result.errors)

    def test_empty_operator_no_errors(self):
        dag = DagDefinition(
            dag_id="test",
            tasks=[TaskDefinition(task_id="empty_task", operator=OperatorType.EMPTY)],
        )
        result = self.validator.validate(dag)
        assert not result.has_errors

    def test_unknown_params_warning(self):
        dag = DagDefinition(
            dag_id="test",
            tasks=[
                TaskDefinition(
                    task_id="task",
                    operator=OperatorType.BASH,
                    operator_params={
                        "bash_command": "echo test",
                        "totally_fake_param": "value",
                    },
                ),
            ],
        )
        result = self.validator.validate(dag)
        warnings = result.warnings
        assert len(warnings) >= 1
        assert any("totally_fake_param" in w.message for w in warnings)

    def test_negative_retries(self):
        dag = DagDefinition(
            dag_id="test",
            tasks=[
                TaskDefinition(
                    task_id="task",
                    operator=OperatorType.BASH,
                    operator_params={"bash_command": "echo", "retries": -1},
                ),
            ],
        )
        result = self.validator.validate(dag)
        assert result.has_errors

    def test_valid_retries(self):
        dag = DagDefinition(
            dag_id="test",
            tasks=[
                TaskDefinition(
                    task_id="task",
                    operator=OperatorType.BASH,
                    operator_params={"bash_command": "echo", "retries": 3},
                ),
            ],
        )
        result = self.validator.validate(dag)
        assert not result.has_errors


# -----------------------------------------------------------------------
# ScheduleValidator tests
# -----------------------------------------------------------------------

class TestScheduleValidator:
    """Tests for the schedule validator."""

    def setup_method(self):
        self.validator = ScheduleValidator()

    def test_valid_manual(self, simple_dag):
        result = self.validator.validate(simple_dag)
        # No errors for manual schedule
        assert not result.has_errors

    def test_valid_cron(self, complex_dag):
        result = self.validator.validate(complex_dag)
        assert not result.has_errors

    def test_valid_preset(self, daily_dag):
        result = self.validator.validate(daily_dag)
        assert not result.has_errors

    def test_catchup_with_manual_warning(self):
        dag = DagDefinition(
            dag_id="test",
            schedule=ScheduleConfig(type=ScheduleType.MANUAL),
            catchup=True,
            tasks=[],
        )
        result = self.validator.validate(dag)
        warnings = result.warnings
        assert len(warnings) >= 1
        assert any("catchup" in w.message.lower() for w in warnings)

    def test_every_minute_warning(self):
        dag = DagDefinition(
            dag_id="test",
            schedule=ScheduleConfig(type=ScheduleType.CRON, expression="* * * * *"),
            tasks=[],
        )
        result = self.validator.validate(dag)
        warnings = result.warnings
        assert len(warnings) >= 1
        assert any("every minute" in w.message.lower() for w in warnings)


# -----------------------------------------------------------------------
# SchemaValidator tests
# -----------------------------------------------------------------------

class TestSchemaValidator:
    """Tests for the schema/best-practices validator."""

    def setup_method(self):
        self.validator = SchemaValidator()

    def test_complete_dag_minimal_issues(self, simple_dag):
        result = self.validator.validate(simple_dag)
        # Should pass with no errors
        assert not result.has_errors

    def test_empty_dag_warning(self, empty_dag):
        result = self.validator.validate(empty_dag)
        warnings = result.warnings
        assert any("no tasks" in w.message.lower() for w in warnings)

    def test_missing_description_warning(self):
        dag = DagDefinition(
            dag_id="test",
            description="",
            tasks=[TaskDefinition(task_id="t")],
        )
        result = self.validator.validate(dag)
        warnings = result.warnings
        assert any("description" in w.message.lower() for w in warnings)

    def test_missing_tags_info(self):
        dag = DagDefinition(
            dag_id="test",
            description="Test DAG",
            tags=[],
            tasks=[TaskDefinition(task_id="t")],
        )
        result = self.validator.validate(dag)
        info_issues = [i for i in result.issues if i.severity == Severity.INFO]
        assert any("tags" in i.message.lower() for i in info_issues)
