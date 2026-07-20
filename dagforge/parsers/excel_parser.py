"""Excel parser for DAG Forge.

Backwards-compatible with the original DAG Factory YAML Builder's
3-sheet Excel format (Dad_config, Task_details, Dependency_flow).
Also supports a cleaned-up format with standardized column names.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pandas as pd

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
from dagforge.operators import operator_registry
from dagforge.parsers.base import BaseParser


logger = logging.getLogger(__name__)

# Column name mappings: original (possibly typo'd) -> standardized
DAG_COLUMN_MAP: dict[str, str] = {
    "DAG_ID": "dag_id",
    "dag_id": "dag_id",
    "dad_ref": "dag_ref",
    "dag_ref": "dag_ref",
    "Schedule_type": "schedule_type",
    "schedule_type": "schedule_type",
    "schedule": "schedule",
    "Schedule": "schedule",
    "Default_arg": "default_args",
    "default_args": "default_args",
    "Dag_parameters": "dag_parameters",
    "dag_parameters": "dag_parameters",
    "description": "description",
    "Description": "description",
    "tags": "tags",
    "Tags": "tags",
}

TASK_COLUMN_MAP: dict[str, str] = {
    "Task_ID": "task_id",
    "task_id": "task_id",
    "dag_ref": "dag_ref",
    "Task_type": "task_type",
    "task_type": "task_type",
    "Task_specs": "task_specs",
    "task_specs": "task_specs",
    "Task_parameters": "task_parameters",
    "task_parameters": "task_parameters",
}

DEP_COLUMN_MAP: dict[str, str] = {
    "dag_ref": "dag_ref",
    "Task_id": "task_id",
    "task_id": "task_id",
    "Upstream_task": "upstream_task",
    "upstream_task": "upstream_task",
}

# Sheet name alternatives (supports original typo "Dad_config")
DAG_SHEET_NAMES = ["Dad_config", "Dag_config", "dag_config", "dags"]
TASK_SHEET_NAMES = ["Task_details", "task_details", "tasks"]
DEP_SHEET_NAMES = ["Dependency_flow", "dependency_flow", "dependencies"]


def _normalize_columns(df: pd.DataFrame, column_map: dict[str, str]) -> pd.DataFrame:
    """Rename DataFrame columns to standardized names."""
    rename_map = {}
    for col in df.columns:
        col_str = str(col).strip()
        if col_str in column_map:
            rename_map[col] = column_map[col_str]
    return df.rename(columns=rename_map)


def _find_sheet(
    excel_file: pd.ExcelFile, candidates: list[str], label: str
) -> str:
    """Find a matching sheet name from a list of candidates."""
    available = excel_file.sheet_names
    for candidate in candidates:
        if candidate in available:
            return candidate
    raise ParseError(
        f"Could not find {label} sheet. "
        f"Tried: {candidates}. Available sheets: {available}",
        source=str(excel_file),
    )


def _parse_key_value_string(kv_string: Any) -> dict[str, str]:
    """Parse 'key: value, key2: value2' format strings into a dictionary.

    This is backwards-compatible with the original project's format.
    Handles NaN, None, and empty strings gracefully.
    """
    if pd.isna(kv_string) or not kv_string:
        return {}

    parsed: dict[str, str] = {}
    raw = str(kv_string)

    for item in raw.split(","):
        item = item.strip()
        if ":" in item:
            key, value = item.split(":", 1)
            key = key.strip()
            value = value.strip().strip("'\"")
            if key:
                parsed[key] = value

    return parsed


def _resolve_schedule(schedule_type_raw: Any, schedule_raw: Any) -> ScheduleConfig:
    """Convert raw schedule fields into a ScheduleConfig."""
    sched_type_str = str(schedule_type_raw).strip().lower() if pd.notna(schedule_type_raw) else ""
    sched_expr = str(schedule_raw).strip() if pd.notna(schedule_raw) else ""

    # Normalize empty/nan values
    if sched_expr.lower() in ("nan", "none", "null", ""):
        sched_expr = ""

    if sched_type_str in ("manual", "") or not sched_type_str or sched_type_str == "nan":
        return ScheduleConfig(type=ScheduleType.MANUAL, expression=None)
    elif sched_type_str == "preset":
        return ScheduleConfig(type=ScheduleType.PRESET, expression=sched_expr)
    elif sched_type_str == "cron":
        return ScheduleConfig(type=ScheduleType.CRON, expression=sched_expr)
    elif sched_type_str == "timetable":
        return ScheduleConfig(type=ScheduleType.TIMETABLE, expression=sched_expr)
    else:
        raise ParseError(
            f"Unknown schedule type: '{schedule_type_raw}'. "
            "Must be one of: manual, preset, cron, timetable"
        )


def _resolve_operator(task_type_raw: Any) -> str:
    """Map a raw task type string to an operator key.

    Uses the operator registry to resolve by key, alias, class path,
    or class name.  Falls back to 'empty' if unrecognised.
    """
    if pd.isna(task_type_raw) or not task_type_raw:
        return OperatorType.EMPTY

    return operator_registry.resolve(str(task_type_raw)).key


@registry.parser("excel")
class ExcelParser(BaseParser):
    """Parser for Excel input files.

    Supports the original DAG Factory YAML Builder 3-sheet format:
    - Dad_config (or Dag_config): DAG-level configuration
    - Task_details: Task definitions
    - Dependency_flow: Task dependency relationships

    Column names are normalized to handle the original project's
    inconsistent naming (e.g., dad_ref vs dag_ref, Task_id vs Task_ID).
    """

    @property
    def supported_extensions(self) -> set[str]:
        return {".xlsx", ".xls"}

    def parse(self, source: Path) -> ParseResult:
        """Parse an Excel file into DAG definitions.

        Args:
            source: Path to the Excel file.

        Returns:
            ParseResult with parsed DAGs and any warnings.

        Raises:
            ParseError: If the file cannot be read or is missing required sheets.
        """
        if not source.exists():
            raise ParseError(f"File not found: {source}", source=str(source))

        # Skip Excel temp files
        if source.name.startswith("~$"):
            raise ParseError(
                f"Skipping temporary Excel file: {source.name}",
                source=str(source),
            )

        logger.info("Parsing Excel file: %s", source)
        warnings: list[str] = []

        try:
            excel_file = pd.ExcelFile(source, engine="openpyxl")
        except Exception as e:
            raise ParseError(
                f"Failed to open Excel file: {e}", source=str(source)
            ) from e

        # Find and read sheets
        try:
            dag_sheet = _find_sheet(excel_file, DAG_SHEET_NAMES, "DAG config")
            task_sheet = _find_sheet(excel_file, TASK_SHEET_NAMES, "Task details")
            dep_sheet = _find_sheet(excel_file, DEP_SHEET_NAMES, "Dependencies")
        except ParseError:
            raise

        dags_df = _normalize_columns(
            pd.read_excel(excel_file, sheet_name=dag_sheet), DAG_COLUMN_MAP
        )
        tasks_df = _normalize_columns(
            pd.read_excel(excel_file, sheet_name=task_sheet), TASK_COLUMN_MAP
        )
        deps_df = _normalize_columns(
            pd.read_excel(excel_file, sheet_name=dep_sheet), DEP_COLUMN_MAP
        )

        # Build DAG definitions
        dags: list[DagDefinition] = []

        for _, dag_row in dags_df.iterrows():
            dag_id = str(dag_row.get("dag_id", "")).strip()
            dag_ref = dag_row.get("dag_ref")

            if not dag_id or pd.isna(dag_id) or dag_id == "nan":
                warnings.append(f"Skipping row with missing DAG_ID (ref: {dag_ref})")
                continue

            # Resolve schedule
            try:
                schedule = _resolve_schedule(
                    dag_row.get("schedule_type"),
                    dag_row.get("schedule"),
                )
            except (ParseError, ValueError) as e:
                warnings.append(f"DAG '{dag_id}': {e}")
                schedule = ScheduleConfig(type=ScheduleType.MANUAL, expression=None)

            # Build default_args: base defaults + user overrides
            default_args: dict[str, Any] = {
                "owner": "airflow",
                "start_date": "2024-01-01",
            }
            user_defaults = _parse_key_value_string(dag_row.get("default_args"))
            default_args.update(user_defaults)

            # Parse DAG-level parameters for catchup
            dag_params = _parse_key_value_string(dag_row.get("dag_parameters"))
            catchup = False
            if "catchup" in dag_params:
                catchup = str(dag_params["catchup"]).lower() == "true"

            # Parse description
            description = ""
            desc_raw = dag_row.get("description")
            if pd.notna(desc_raw):
                description = str(desc_raw).strip()

            # Parse tags
            tags: list[str] = []
            tags_raw = dag_row.get("tags")
            if pd.notna(tags_raw) and tags_raw:
                tags = [t.strip() for t in str(tags_raw).split(",") if t.strip()]

            # Build tasks for this DAG
            dag_tasks_df = tasks_df[tasks_df["dag_ref"] == dag_ref]
            tasks: list[TaskDefinition] = []

            for _, task_row in dag_tasks_df.iterrows():
                task_id = str(task_row.get("task_id", "")).strip()
                if not task_id or pd.isna(task_id) or task_id == "nan":
                    warnings.append(f"DAG '{dag_id}': Skipping task with missing Task_ID")
                    continue

                operator = _resolve_operator(task_row.get("task_type"))

                # Build operator params
                operator_params: dict[str, Any] = {}

                # Add task_specs as the primary operator param
                task_specs = task_row.get("task_specs")
                if pd.notna(task_specs) and task_specs:
                    specs_str = str(task_specs).strip()
                    # Use registry to determine which param task_specs maps to
                    specs_param = operator_registry.task_specs_param(operator)
                    if specs_param:
                        operator_params[specs_param] = specs_str
                    elif specs_str:
                        # Fallback for operators without a task_specs mapping
                        operator_params["command"] = specs_str

                # Add extra parameters from Task_parameters column
                extra_params = _parse_key_value_string(task_row.get("task_parameters"))
                for k, v in extra_params.items():
                    # Try to convert numeric values
                    if v.isdigit():
                        operator_params[k] = int(v)
                    elif v.lower() in ("true", "false"):
                        operator_params[k] = v.lower() == "true"
                    else:
                        operator_params[k] = v

                # Resolve dependencies
                task_deps_df = deps_df[
                    (deps_df["dag_ref"] == dag_ref) & (deps_df["task_id"] == task_id)
                ]
                dependencies: list[str] = []
                for _, dep_row in task_deps_df.iterrows():
                    upstream = dep_row.get("upstream_task")
                    if pd.notna(upstream):
                        up_str = str(upstream).strip()
                        if up_str and up_str != "nan" and up_str != task_id:
                            dependencies.append(up_str)

                tasks.append(TaskDefinition(
                    task_id=task_id,
                    operator=operator,
                    operator_params=operator_params,
                    dependencies=dependencies,
                ))

            # Create DagDefinition
            try:
                dag = DagDefinition(
                    dag_id=dag_id,
                    description=description,
                    schedule=schedule,
                    default_args=default_args,
                    catchup=catchup,
                    tags=tags,
                    tasks=tasks,
                )
                dags.append(dag)
                logger.info("Parsed DAG: %s (%d tasks)", dag_id, len(tasks))
            except Exception as e:
                warnings.append(f"DAG '{dag_id}': Failed to create definition: {e}")

        return ParseResult(dags=dags, source=str(source), warnings=warnings)
