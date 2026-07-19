"""dag-factory YAML renderer for DAG Forge.

Generates YAML output that is 100% compatible with the dag-factory library.
This is the primary output format, matching the original project's output.
"""

from __future__ import annotations

import logging
from io import StringIO
from typing import Any

from ruamel.yaml import YAML

from dagforge.core.models import DagDefinition, OperatorType
from dagforge.core.registry import registry
from dagforge.renderers.base import BaseRenderer


logger = logging.getLogger(__name__)


def _build_dagfactory_dict(dag: DagDefinition) -> dict[str, Any]:
    """Convert a DagDefinition into a dag-factory compatible dictionary.

    The output structure matches exactly what dag-factory expects:
    ```yaml
    dag_id:
      default_args:
        owner: airflow
        start_date: "2024-01-01"
      schedule: "@daily"
      Description: "My DAG description"
      catchup: false
      tasks:
        task_name:
          operator: airflow.operators.bash.BashOperator
          bash_command: "echo hello"
          dependencies:
            - upstream_task
    ```
    """
    # Build task dictionary
    tasks_dict: dict[str, Any] = {}

    for task in dag.tasks:
        task_entry: dict[str, Any] = {
            "operator": task.operator.full_class_path,
        }

        # Add operator-specific params
        for key, value in task.operator_params.items():
            task_entry[key] = value

        # Add dependencies
        if task.dependencies:
            task_entry["dependencies"] = list(task.dependencies)

        tasks_dict[task.task_id] = task_entry

    # Build the DAG dict
    dag_dict: dict[str, Any] = {
        "default_args": dict(dag.default_args),
        "schedule": dag.schedule.to_airflow_schedule(),
    }

    # Use 'Description' (capital D) for backwards compatibility with original output
    if dag.description:
        dag_dict["Description"] = dag.description

    dag_dict["catchup"] = dag.catchup

    # Add tags if present
    if dag.tags:
        dag_dict["tags"] = list(dag.tags)

    dag_dict["tasks"] = tasks_dict

    return {dag.dag_id: dag_dict}


@registry.renderer("dagfactory")
class DagFactoryRenderer(BaseRenderer):
    """Renders DagDefinitions as dag-factory compatible YAML files.

    Produces output identical to the original DAG Factory YAML Builder,
    ensuring full backwards compatibility with existing dag-factory setups.
    """

    def __init__(self) -> None:
        self._yaml = YAML()
        self._yaml.default_flow_style = False
        # Preserve insertion order (don't sort keys)
        self._yaml.allow_unicode = True

    @property
    def file_extension(self) -> str:
        return ".yaml"

    def render(self, dag: DagDefinition) -> str:
        """Render a single DAG to dag-factory YAML string."""
        data = _build_dagfactory_dict(dag)

        stream = StringIO()
        self._yaml.dump(data, stream)
        result = stream.getvalue()

        logger.debug("Rendered DAG '%s' (%d bytes)", dag.dag_id, len(result))
        return result

    def render_all(self, dags: list[DagDefinition]) -> str:
        """Render multiple DAGs into a single YAML document.

        Each DAG is a top-level key in the YAML, separated by blank lines.
        """
        combined: dict[str, Any] = {}
        for dag in dags:
            dag_dict = _build_dagfactory_dict(dag)
            combined.update(dag_dict)

        stream = StringIO()
        self._yaml.dump(combined, stream)
        return stream.getvalue()
