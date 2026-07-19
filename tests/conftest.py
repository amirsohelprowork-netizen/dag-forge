"""Shared test fixtures for DAG Forge."""

from __future__ import annotations

from pathlib import Path

import pytest

from dagforge.core.models import (
    DagDefinition,
    OperatorType,
    ScheduleConfig,
    ScheduleType,
    TaskDefinition,
)


# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_EXCEL = Path(__file__).parent.parent.parent / "dag_factory_analysis" / "input_files" / "sample_sheet.xlsx"


@pytest.fixture
def simple_dag() -> DagDefinition:
    """A simple valid DAG with 3 tasks in a linear chain."""
    return DagDefinition(
        dag_id="test_simple_dag",
        description="A simple test DAG",
        schedule=ScheduleConfig(type=ScheduleType.MANUAL, expression=None),
        default_args={"owner": "test", "start_date": "2024-01-01"},
        catchup=False,
        tags=["test"],
        tasks=[
            TaskDefinition(
                task_id="start",
                operator=OperatorType.EMPTY,
                operator_params={},
                dependencies=[],
            ),
            TaskDefinition(
                task_id="process",
                operator=OperatorType.BASH,
                operator_params={"bash_command": "echo 'processing'"},
                dependencies=["start"],
            ),
            TaskDefinition(
                task_id="finish",
                operator=OperatorType.EMPTY,
                operator_params={},
                dependencies=["process"],
            ),
        ],
    )


@pytest.fixture
def complex_dag() -> DagDefinition:
    """A more complex DAG with multiple branches and operator types."""
    return DagDefinition(
        dag_id="test_complex_dag",
        description="A complex test DAG with branching",
        schedule=ScheduleConfig(type=ScheduleType.CRON, expression="0 6 * * *"),
        default_args={"owner": "data_team", "start_date": "2024-06-01"},
        catchup=False,
        tags=["test", "complex"],
        tasks=[
            TaskDefinition(
                task_id="start",
                operator=OperatorType.EMPTY,
                dependencies=[],
            ),
            TaskDefinition(
                task_id="extract_data",
                operator=OperatorType.BASH,
                operator_params={"bash_command": "python extract.py", "retries": 3},
                dependencies=["start"],
            ),
            TaskDefinition(
                task_id="transform_data",
                operator=OperatorType.BASH,
                operator_params={"bash_command": "python transform.py"},
                dependencies=["extract_data"],
            ),
            TaskDefinition(
                task_id="load_data",
                operator=OperatorType.BASH,
                operator_params={"bash_command": "python load.py"},
                dependencies=["transform_data"],
            ),
            TaskDefinition(
                task_id="send_notification",
                operator=OperatorType.BASH,
                operator_params={"bash_command": "echo 'done'"},
                dependencies=["load_data"],
            ),
            TaskDefinition(
                task_id="cleanup",
                operator=OperatorType.EMPTY,
                dependencies=["send_notification"],
            ),
        ],
    )


@pytest.fixture
def empty_dag() -> DagDefinition:
    """A DAG with no tasks."""
    return DagDefinition(
        dag_id="test_empty_dag",
        description="",
        schedule=ScheduleConfig(type=ScheduleType.MANUAL),
        tasks=[],
    )


@pytest.fixture
def daily_dag() -> DagDefinition:
    """A DAG with a daily preset schedule."""
    return DagDefinition(
        dag_id="test_daily_dag",
        description="Runs daily",
        schedule=ScheduleConfig(type=ScheduleType.PRESET, expression="daily"),
        tasks=[
            TaskDefinition(
                task_id="run_job",
                operator=OperatorType.BASH,
                operator_params={"bash_command": "echo 'daily job'"},
            ),
        ],
    )
