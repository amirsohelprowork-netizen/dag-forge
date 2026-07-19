"""JSON parser for DAG Forge.

Parses DAG definitions from JSON configuration files.
Supports both single-DAG and multi-DAG JSON files.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

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
from dagforge.parsers.yaml_parser import _parse_dag_from_dict


logger = logging.getLogger(__name__)


@registry.parser("json")
class JsonParser(BaseParser):
    """Parser for JSON input files.

    Supports two JSON formats:

    1. Object format (DAG ID as key):
        ```json
        {
          "my_dag": {
            "schedule": "@daily",
            "tasks": { ... }
          }
        }
        ```

    2. Array format (under 'dags' key):
        ```json
        {
          "dags": [
            {
              "dag_id": "my_dag",
              "schedule": "@daily",
              "tasks": [ ... ]
            }
          ]
        }
        ```
    """

    @property
    def supported_extensions(self) -> set[str]:
        return {".json"}

    def parse(self, source: Path) -> ParseResult:
        """Parse a JSON file into DAG definitions."""
        if not source.exists():
            raise ParseError(f"File not found: {source}", source=str(source))

        logger.info("Parsing JSON file: %s", source)
        warnings: list[str] = []

        try:
            with open(source, encoding="utf-8") as f:
                raw_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ParseError(
                f"Invalid JSON syntax: {e}", source=str(source)
            ) from e
        except Exception as e:
            raise ParseError(
                f"Failed to read JSON file: {e}", source=str(source)
            ) from e

        if not isinstance(raw_data, dict):
            raise ParseError(
                "JSON root must be an object (dict)",
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
            # Object format: each top-level key is a DAG ID
            for key, value in raw_data.items():
                if not isinstance(value, dict):
                    continue
                if key.startswith("_") or key in ("version", "metadata", "$schema"):
                    continue
                try:
                    dag = _parse_dag_from_dict(str(key), value)
                    dags.append(dag)
                except Exception as e:
                    warnings.append(f"DAG '{key}': {e}")

        if not dags:
            warnings.append("No valid DAG definitions found in JSON file")

        return ParseResult(dags=dags, source=str(source), warnings=warnings)
