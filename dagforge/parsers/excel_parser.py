"""Excel parser for DAG Forge.

Backwards-compatible with the original DAG Factory YAML Builder's
3-sheet Excel format (Dad_config, Task_details, Dependency_flow).
Also supports a cleaned-up format with standardized column names.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl.utils.cell import get_column_letter
from pydantic import ValidationError

from dagforge.core.exceptions import ParseError
from dagforge.core.models import (
    DagDefinition,
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


@dataclass
class _Sheet:
    name: str
    frame: pd.DataFrame

    def rows(self) -> Iterator[tuple[int, pd.Series]]:
        # Preserve the original index so gaps in the workbook count toward row numbers.
        return self.frame.dropna(how="all").iterrows()

    def cell(self, index: int, field: str) -> str:
        row = index + 2  # The header occupies Excel row 1.
        if field not in self.frame.columns:
            return f"{self.name} row {row} ({field} column)"
        column = get_column_letter(self.frame.columns.get_loc(field) + 1)
        return f"{self.name}!{column}{row}"

    def require_columns(self, *fields: str) -> None:
        missing = [field for field in fields if field not in self.frame.columns]
        if missing:
            raise ParseError(f"{self.name} row 1 is missing columns: {', '.join(missing)}")


def _read_sheet(
    excel: pd.ExcelFile, candidates: list[str], columns: dict[str, str]
) -> _Sheet:
    for name in candidates:
        if name in excel.sheet_names:
            frame = excel.parse(name)
            frame = frame.rename(columns=lambda col: columns.get(str(col).strip(), col))
            if not frame.columns.is_unique:
                raise ParseError(f"{name} row 1 contains duplicate column names")
            return _Sheet(name, frame)
    raise ParseError(
        f"Missing sheet '{candidates[0]}'. Available sheets: {', '.join(excel.sheet_names)}"
    )


def _text(value: Any) -> str:
    return str(value).strip() if pd.notna(value) else ""


def _dag_ref(value: Any) -> Any:
    # Keep numeric references comparable across sheets with and without blank rows.
    return value if pd.notna(value) and not isinstance(value, str) else _text(value)


def _parse_key_value_string(value: Any, cell: str) -> dict[str, str]:
    """Parse the legacy comma-separated key/value format."""
    parsed: dict[str, str] = {}
    for item in _text(value).split(","):
        if not item.strip():
            continue
        key, separator, raw_value = item.partition(":")
        if not separator or not key.strip():
            raise ParseError(f"{cell}: Expected 'key: value', found '{item.strip()}'")
        parsed[key.strip()] = raw_value.strip().strip("'\"")
    return parsed


def _resolve_schedule(kind: ScheduleType, expression: str) -> ScheduleConfig:
    if kind == ScheduleType.MANUAL:
        return ScheduleConfig(type=kind)
    if expression.lower() in ("", "nan", "none", "null"):
        return ScheduleConfig(type=kind)
    return ScheduleConfig(type=kind, expression=expression)


def _model_error(error: ValidationError) -> str:
    return error.errors()[0]["msg"].removeprefix("Value error, ")


def _task_param_value(value: str) -> Any:
    if value.isdecimal():
        return int(value)
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    return value


@registry.parser("excel")
class ExcelParser(BaseParser):
    """Parse the DAG, task, and dependency sheets in a DAG Forge workbook."""

    @property
    def supported_extensions(self) -> set[str]:
        return {".xlsx", ".xls"}

    def parse(self, source: Path) -> ParseResult:
        if source.name.startswith("~$"):
            raise ParseError(f"Skipping temporary Excel file: {source.name}", source=str(source))

        logger.info("Parsing Excel file: %s", source)
        try:
            with pd.ExcelFile(source, engine="openpyxl") as excel:
                dag_sheet = _read_sheet(excel, DAG_SHEET_NAMES, DAG_COLUMN_MAP)
                task_sheet = _read_sheet(excel, TASK_SHEET_NAMES, TASK_COLUMN_MAP)
                dep_sheet = _read_sheet(excel, DEP_SHEET_NAMES, DEP_COLUMN_MAP)
        except ParseError:
            raise
        except Exception as error:
            raise ParseError(f"Could not read Excel workbook: {error}", source=str(source)) from error

        dag_sheet.require_columns("dag_id")
        if not task_sheet.frame.empty:
            task_sheet.require_columns("dag_ref", "task_id")
        if not dep_sheet.frame.empty:
            dep_sheet.require_columns("dag_ref", "task_id")

        dag_rows = list(dag_sheet.rows())
        refs = {_dag_ref(row.get("dag_ref")) for _, row in dag_rows}
        tasks: dict[Any, dict[str, TaskDefinition]] = defaultdict(dict)
        task_cells: dict[tuple[Any, str], dict[str | None, list[str]]] = {}
        for index, row in task_sheet.rows():
            ref = _dag_ref(row.get("dag_ref"))
            if not _text(row.get("dag_ref")) or ref not in refs:
                cell = task_sheet.cell(index, "dag_ref")
                raise ParseError(f"{cell}: Use a dag_ref from {dag_sheet.name}, got '{ref}'")

            task_id = _text(row.get("task_id"))
            id_cell = task_sheet.cell(index, "task_id")
            if not task_id:
                raise ParseError(f"{id_cell}: Enter a task ID")
            if task_id in tasks[ref]:
                first = task_cells[ref, task_id][None][0]
                raise ParseError(f"{id_cell}: Duplicate task ID '{task_id}' (first used in {first})")

            task_type = _text(row.get("task_type"))
            type_cell = task_sheet.cell(index, "task_type")
            try:
                operator = operator_registry.resolve(task_type, strict=True)
            except KeyError as error:
                raise ParseError(f"{type_cell}: {error.args[0]}") from error

            specs_cell = task_sheet.cell(index, "task_specs")
            params_cell = task_sheet.cell(index, "task_parameters")
            specs = _text(row.get("task_specs"))
            params = {operator.task_specs_param or "command": specs} if specs else {}
            extra_params = _parse_key_value_string(row.get("task_parameters"), params_cell)
            params.update({key: _task_param_value(value) for key, value in extra_params.items()})
            try:
                tasks[ref][task_id] = TaskDefinition(
                    task_id=task_id, operator=operator.key, operator_params=params
                )
            except ValidationError as error:
                raise ParseError(f"{id_cell}: {_model_error(error)}") from error

            cells = {param: [params_cell] for param in operator.all_param_names}
            if operator.task_specs_param:
                cells[operator.task_specs_param] = [specs_cell]
            elif specs:
                cells["command"] = [specs_cell]
            cells.update({param: [params_cell] for param in extra_params})
            task_cells[ref, task_id] = {**cells, None: [id_cell], "operator": [type_cell]}

        for index, row in dep_sheet.rows():
            ref = _dag_ref(row.get("dag_ref"))
            if not _text(row.get("dag_ref")) or ref not in refs:
                cell = dep_sheet.cell(index, "dag_ref")
                raise ParseError(f"{cell}: Use a dag_ref from {dag_sheet.name}, got '{ref}'")

            task_id = _text(row.get("task_id"))
            if task_id not in tasks[ref]:
                cell = dep_sheet.cell(index, "task_id")
                raise ParseError(f"{cell}: Unknown task '{task_id}' for dag_ref '{ref}'")

            upstream = _text(row.get("upstream_task"))
            if not upstream:
                continue
            upstream_cell = dep_sheet.cell(index, "upstream_task")
            if upstream not in tasks[ref]:
                raise ParseError(f"{upstream_cell}: Unknown upstream task '{upstream}'")
            if upstream == task_id:
                raise ParseError(f"{upstream_cell}: Task '{task_id}' cannot depend on itself")
            tasks[ref][task_id].dependencies.append(upstream)
            task_cells[ref, task_id].setdefault("dependencies", []).append(upstream_cell)

        result = ParseResult(source=str(source))
        for index, row in dag_rows:
            dag_id = _text(row.get("dag_id"))
            dag_id_cell = dag_sheet.cell(index, "dag_id")
            if not dag_id:
                raise ParseError(f"{dag_id_cell}: Enter a DAG ID")
            ref = _dag_ref(row.get("dag_ref"))
            schedule_type = _text(row.get("schedule_type"))
            try:
                kind = ScheduleType(schedule_type.lower() or "manual")
            except ValueError as error:
                cell = dag_sheet.cell(index, "schedule_type")
                options = ", ".join(kind.value for kind in ScheduleType)
                raise ParseError(
                    f"{cell}: Unknown schedule type '{schedule_type}'. Use {options}"
                ) from error
            try:
                schedule = _resolve_schedule(kind, _text(row.get("schedule")))
            except ValidationError as error:
                cell = dag_sheet.cell(index, "schedule")
                raise ParseError(f"{cell}: {_model_error(error)}") from error

            defaults = {"owner": "airflow", "start_date": "2024-01-01"}
            defaults_cell = dag_sheet.cell(index, "default_args")
            defaults.update(_parse_key_value_string(row.get("default_args"), defaults_cell))
            dag_params_cell = dag_sheet.cell(index, "dag_parameters")
            dag_params = _parse_key_value_string(row.get("dag_parameters"), dag_params_cell)
            try:
                dag = DagDefinition(
                    dag_id=dag_id,
                    description=_text(row.get("description")),
                    schedule=schedule,
                    default_args=defaults,
                    catchup=dag_params.get("catchup", "").lower() == "true",
                    tags=[tag.strip() for tag in _text(row.get("tags")).split(",") if tag.strip()],
                    tasks=[task.model_copy(deep=True) for task in tasks[ref].values()],
                )
            except ValidationError as error:
                raise ParseError(f"{dag_id_cell}: {_model_error(error)}") from error
            result.dags.append(dag)

            schedule_cell = dag_sheet.cell(index, "schedule")
            dag_cells: dict[str | None, list[str]] = {
                None: [dag_id_cell],
                "description": [dag_sheet.cell(index, "description")],
                "tags": [dag_sheet.cell(index, "tags")],
                "schedule": [dag_sheet.cell(index, "schedule_type")],
                "schedule.expression": [schedule_cell],
                "catchup": [dag_params_cell],
                "default_args.owner": [defaults_cell],
                "default_args.start_date": [defaults_cell],
                "dependencies": [dep_sheet.name],
            }
            for field, cells in dag_cells.items():
                result.locations.setdefault((dag_id, None, field), []).extend(
                    f"{source} / {cell}" for cell in cells
                )
            for task_id in tasks[ref]:
                for field, cells in task_cells[ref, task_id].items():
                    result.locations.setdefault((dag_id, task_id, field), []).extend(
                        f"{source} / {cell}" for cell in cells
                    )
        return result
