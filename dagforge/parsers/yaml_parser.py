"""YAML parser for DAG Forge.

Parses DAG definitions from clean YAML configuration files.
Supports both single-DAG and multi-DAG YAML files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from dagforge.core.exceptions import ParseError
from dagforge.core.models import (
    DagDefinition,
    OperatorType,
    ParseResult,
    ScheduleConfig,
    ScheduleType,
    TaskDefinition,
)
from dagforge.core.registry import registry
from dagforge.parsers.base import BaseParser


logger = logging.getLogger(__name__)

# Initialize ruamel.yaml with safe loading
_yaml = YAML(typ="safe")


def _parse_schedule(schedule_data: Any) -> ScheduleConfig:
    """Parse schedule configuration from YAML data.

    Supports multiple formats:
    - None / null -> manual
    - "@daily" -> preset
    - "0 0 * * *" -> cron
    - {"type": "cron", "expression": "..."} -> explicit
    """
    if schedule_data is None:
        return ScheduleConfig(type=ScheduleType.MANUAL, expression=None)

    if isinstance(schedule_data, dict):
        stype = schedule_data.get("type", "manual")
        expr = schedule_data.get("expression")
        return ScheduleConfig(type=ScheduleType(stype), expression=expr)

    # String schedule
    schedule_str = str(schedule_data).strip()

    if schedule_str.startswith("@"):
        preset = schedule_str.lstrip("@").lower()
        return ScheduleConfig(type=ScheduleType.PRESET, expression=preset)

    # Try as cron (5 space-separated fields)
    parts = schedule_str.split()
    if len(parts) == 5:
        return ScheduleConfig(type=ScheduleType.CRON, expression=schedule_str)

    # Fallback: treat as timetable reference
    return ScheduleConfig(type=ScheduleType.TIMETABLE, expression=schedule_str)


def _parse_operator(operator_data: Any) -> OperatorType:
    """Parse operator type from YAML data."""
    if operator_data is None:
        return OperatorType.EMPTY

    op_str = str(operator_data).strip().lower()

    # Try direct enum value
    try:
        return OperatorType(op_str)
    except ValueError:
        pass

    # Try matching by full class path
    for op_type in OperatorType:
        if op_type.full_class_path.lower() == op_str:
            return op_type
        # Also match just the class name
        class_name = op_type.full_class_path.split(".")[-1].lower()
        if op_str == class_name:
            return op_type

    logger.warning("Unknown operator '%s', defaulting to EmptyOperator", operator_data)
    return OperatorType.EMPTY


def _parse_dag_from_dict(dag_id: str, data: dict[str, Any]) -> DagDefinition:
    """Parse a single DAG definition from a YAML dictionary."""
    # Schedule
    schedule = _parse_schedule(data.get("schedule"))

    # Default args
    default_args: dict[str, Any] = {
        "owner": "airflow",
        "start_date": "2024-01-01",
    }
    if "default_args" in data and isinstance(data["default_args"], dict):
        default_args.update(data["default_args"])

    # Catchup
    catchup = bool(data.get("catchup", False))

    # Description
    description = str(data.get("description", data.get("Description", "")))

    # Tags
    tags_raw = data.get("tags", [])
    tags = list(tags_raw) if isinstance(tags_raw, list) else []

    # Tasks
    tasks: list[TaskDefinition] = []
    tasks_data = data.get("tasks", {})

    if isinstance(tasks_data, dict):
        for task_id, task_data in tasks_data.items():
            if not isinstance(task_data, dict):
                continue

            operator = _parse_operator(task_data.get("operator"))

            # Separate known meta-keys from operator params
            meta_keys = {"operator", "dependencies"}
            operator_params = {
                k: v for k, v in task_data.items() if k not in meta_keys
            }

            # Dependencies
            deps = task_data.get("dependencies", [])
            if isinstance(deps, str):
                deps = [d.strip() for d in deps.split(",") if d.strip()]

            tasks.append(TaskDefinition(
                task_id=str(task_id),
                operator=operator,
                operator_params=operator_params,
                dependencies=list(deps),
            ))

    elif isinstance(tasks_data, list):
        for task_data in tasks_data:
            if not isinstance(task_data, dict):
                continue
            task_id = str(task_data.get("task_id", task_data.get("id", "")))
            operator = _parse_operator(task_data.get("operator"))

            meta_keys = {"task_id", "id", "operator", "dependencies"}
            operator_params = {
                k: v for k, v in task_data.items() if k not in meta_keys
            }

            deps = task_data.get("dependencies", [])
            if isinstance(deps, str):
                deps = [d.strip() for d in deps.split(",") if d.strip()]

            tasks.append(TaskDefinition(
                task_id=task_id,
                operator=operator,
                operator_params=operator_params,
                dependencies=list(deps),
            ))

    return DagDefinition(
        dag_id=dag_id,
        description=description,
        schedule=schedule,
        default_args=default_args,
        catchup=catchup,
        tags=tags,
        tasks=tasks,
    )


@registry.parser("yaml")
class YamlParser(BaseParser):
    """Parser for YAML input files.

    Supports two YAML formats:

    1. dag-factory style (DAG ID as top-level key):
        ```yaml
        my_dag:
          schedule: "@daily"
          tasks:
            task_1:
              operator: bash
              bash_command: "echo hello"
        ```

    2. Explicit format (list of DAGs under 'dags' key):
        ```yaml
        dags:
          - dag_id: my_dag
            schedule: "@daily"
            tasks:
              - task_id: task_1
                operator: bash
                bash_command: "echo hello"
        ```
    """

    @property
    def supported_extensions(self) -> set[str]:
        return {".yaml", ".yml"}

    def parse(self, source: Path) -> ParseResult:
        """Parse a YAML file into DAG definitions."""
        if not source.exists():
            raise ParseError(f"File not found: {source}", source=str(source))

        logger.info("Parsing YAML file: %s", source)
        warnings: list[str] = []

        try:
            with open(source, encoding="utf-8") as f:
                raw_data = _yaml.load(f)
        except Exception as e:
            raise ParseError(
                f"Failed to parse YAML file: {e}", source=str(source)
            ) from e

        if not isinstance(raw_data, dict):
            raise ParseError(
                "YAML root must be a dictionary",
                source=str(source),
            )

        dags: list[DagDefinition] = []

        # Check for explicit 'dags' list format
        if "dags" in raw_data and isinstance(raw_data["dags"], list):
            for dag_data in raw_data["dags"]:
                if not isinstance(dag_data, dict):
                    continue
                dag_id = str(dag_data.get("dag_id", dag_data.get("id", "")))
                if not dag_id:
                    warnings.append("Skipping DAG with missing dag_id")
                    continue
                try:
                    dag = _parse_dag_from_dict(dag_id, dag_data)
                    dags.append(dag)
                except Exception as e:
                    warnings.append(f"DAG '{dag_id}': {e}")

        else:
            # dag-factory style: each top-level key is a DAG ID
            for key, value in raw_data.items():
                if not isinstance(value, dict):
                    continue
                # Skip metadata keys
                if key.startswith("_") or key in ("version", "metadata"):
                    continue
                try:
                    dag = _parse_dag_from_dict(str(key), value)
                    dags.append(dag)
                except Exception as e:
                    warnings.append(f"DAG '{key}': {e}")

        if not dags:
            warnings.append("No valid DAG definitions found in YAML file")

        return ParseResult(dags=dags, source=str(source), warnings=warnings)
