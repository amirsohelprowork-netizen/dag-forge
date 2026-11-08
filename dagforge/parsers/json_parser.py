"""JSON parser for DAG Forge.

Parses DAG definitions from JSON configuration files.
Supports both single-DAG and multi-DAG JSON files.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from dagforge.core.exceptions import ParseError
from dagforge.core.models import ParseResult
from dagforge.core.registry import registry
from dagforge.parsers.base import BaseParser
from dagforge.parsers.yaml_parser import _parse_document



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

        return _parse_document(raw_data, source)
