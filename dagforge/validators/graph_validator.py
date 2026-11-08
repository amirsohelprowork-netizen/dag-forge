"""Graph validator for DAG Forge.

Detects dependency cycles, orphan tasks, and structural issues
in DAG task dependency graphs using networkx.
"""

from __future__ import annotations

import logging

import networkx as nx

from dagforge.core.models import (
    DagDefinition,
    Severity,
    ValidationIssue,
    ValidationResult,
)
from dagforge.core.registry import registry
from dagforge.validators.base import BaseValidator


logger = logging.getLogger(__name__)


@registry.validator("graph")
class GraphValidator(BaseValidator):
    """Validates the structural integrity of DAG dependency graphs.

    Checks for:
    - Circular dependencies (cycles)
    - Self-dependencies
    - Orphan task references in dependencies
    - Disconnected subgraphs (warning only)
    """

    def validate(self, dag: DagDefinition) -> ValidationResult:
        """Validate the dependency graph of a single DAG."""
        issues: list[ValidationIssue] = []

        if not dag.tasks:
            return ValidationResult(issues=issues)

        # Build directed graph
        graph = nx.DiGraph()
        task_ids = {t.task_id for t in dag.tasks}

        for task in dag.tasks:
            graph.add_node(task.task_id)

        for task in dag.tasks:
            for dep in task.dependencies:
                # Self-dependency check
                if dep == task.task_id:
                    issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        message=f"Task depends on itself",
                        dag_id=dag.dag_id,
                        task_id=task.task_id,
                        field="dependencies",
                    ))
                    continue

                # Orphan reference check
                if dep not in task_ids:
                    issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        message=f"Depends on unknown task '{dep}'",
                        dag_id=dag.dag_id,
                        task_id=task.task_id,
                        field="dependencies",
                    ))
                    continue

                # Add edge: dependency -> task (upstream -> downstream)
                graph.add_edge(dep, task.task_id)

        # Cycle detection
        try:
            cycles = list(nx.simple_cycles(graph))
            for cycle in cycles:
                cycle_str = " -> ".join(cycle + [cycle[0]])
                issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    message=f"Circular dependency detected: {cycle_str}",
                    dag_id=dag.dag_id,
                    field="dependencies",
                ))
        except nx.NetworkXError:
            pass  # Graph is empty or has no edges

        # Disconnected subgraph warning
        if len(dag.tasks) > 1:
            undirected = graph.to_undirected()
            components = list(nx.connected_components(undirected))
            if len(components) > 1:
                component_strs = [
                    "{" + ", ".join(sorted(c)) + "}" for c in components
                ]
                issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    message=(
                        f"DAG has {len(components)} disconnected task groups: "
                        + ", ".join(component_strs)
                    ),
                    dag_id=dag.dag_id,
                ))

        return ValidationResult(issues=issues)

    def validate_batch(self, dags: list[DagDefinition]) -> ValidationResult:
        """Validate multiple DAGs, including cross-DAG checks."""
        result = ValidationResult()

        # Per-DAG validation
        for dag in dags:
            result = result.merge(self.validate(dag))

        # Cross-DAG: duplicate DAG IDs
        dag_ids: dict[str, int] = {}
        for dag in dags:
            dag_ids[dag.dag_id] = dag_ids.get(dag.dag_id, 0) + 1

        for dag_id, count in dag_ids.items():
            if count > 1:
                result.issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    message=f"Duplicate DAG ID '{dag_id}' found {count} times",
                    dag_id=dag_id,
                ))

        return result
