"""Graph analyzer for DAG Forge.

Provides topological analysis of DAG dependency graphs:
- Cycle detection
- Topological sort (execution order)
- Critical path analysis
- Mermaid diagram generation
- ASCII graph rendering for CLI
"""

from __future__ import annotations

import logging

import networkx as nx

from dagforge.core.models import DagDefinition


logger = logging.getLogger(__name__)


class GraphAnalyzer:
    """Analyzes the dependency graph structure of a DAG.

    Uses networkx for all graph operations. Builds a directed graph
    where edges point from upstream tasks to downstream tasks.
    """

    def __init__(self, dag: DagDefinition) -> None:
        self.dag = dag
        self.graph = self._build_graph()

    def _build_graph(self) -> nx.DiGraph:
        """Build a networkx DiGraph from the DAG's task dependencies."""
        g = nx.DiGraph()

        for task in self.dag.tasks:
            g.add_node(task.task_id, operator=task.operator)

        for task in self.dag.tasks:
            for dep in task.dependencies:
                if dep in {t.task_id for t in self.dag.tasks}:
                    g.add_edge(dep, task.task_id)

        return g

    # -------------------------------------------------------------------
    # Analysis methods
    # -------------------------------------------------------------------

    def has_cycles(self) -> bool:
        """Return True if the dependency graph contains cycles."""
        return not nx.is_directed_acyclic_graph(self.graph)

    def detect_cycles(self) -> list[list[str]]:
        """Return all cycles found in the graph.

        Returns:
            List of cycles, where each cycle is a list of task IDs.
            Empty list if graph is acyclic (valid DAG).
        """
        try:
            return list(nx.simple_cycles(self.graph))
        except nx.NetworkXError:
            return []

    def topological_sort(self) -> list[str]:
        """Return tasks in topological order (execution order).

        Returns:
            List of task IDs in execution order.

        Raises:
            ValueError: If the graph contains cycles.
        """
        if self.has_cycles():
            cycles = self.detect_cycles()
            cycle_strs = [" -> ".join(c + [c[0]]) for c in cycles]
            raise ValueError(
                f"Cannot compute execution order: graph has cycles: "
                + "; ".join(cycle_strs)
            )
        return list(nx.topological_sort(self.graph))

    def root_tasks(self) -> list[str]:
        """Return tasks with no upstream dependencies (entry points)."""
        return [n for n in self.graph.nodes() if self.graph.in_degree(n) == 0]

    def leaf_tasks(self) -> list[str]:
        """Return tasks with no downstream dependents (exit points)."""
        return [n for n in self.graph.nodes() if self.graph.out_degree(n) == 0]

    def critical_path(self) -> list[str]:
        """Return the longest dependency chain in the DAG.

        This represents the minimum possible execution time path,
        assuming each task takes 1 unit of time.

        Returns:
            List of task IDs on the critical path.
        """
        if self.has_cycles() or not self.graph.nodes():
            return []

        return nx.dag_longest_path(self.graph)

    def depth(self) -> int:
        """Return the depth (length of critical path) of the DAG."""
        path = self.critical_path()
        return len(path) if path else 0

    # -------------------------------------------------------------------
    # Visualization methods
    # -------------------------------------------------------------------

    def to_mermaid(self) -> str:
        """Generate a Mermaid diagram string for the DAG.

        Returns:
            Mermaid graph definition suitable for rendering.
        """
        lines: list[str] = [f"graph TD"]
        lines.append(f"    %% DAG: {self.dag.dag_id}")

        # Define nodes with operator info
        for task in self.dag.tasks:
            label = f"{task.task_id}\\n({task.operator})"
            lines.append(f'    {task.task_id}["{label}"]')

        # Define edges
        for task in self.dag.tasks:
            for dep in task.dependencies:
                if dep in {t.task_id for t in self.dag.tasks}:
                    lines.append(f"    {dep} --> {task.task_id}")

        # Style root nodes (green) and leaf nodes (blue)
        roots = self.root_tasks()
        leaves = self.leaf_tasks()

        if roots:
            for root in roots:
                lines.append(f"    style {root} fill:#2d6a4f,color:#fff")
        if leaves:
            for leaf in leaves:
                if leaf not in roots:  # Don't double-style
                    lines.append(f"    style {leaf} fill:#1d3557,color:#fff")

        return "\n".join(lines)

    def to_ascii(self) -> str:
        """Generate an ASCII representation of the DAG graph.

        Returns:
            ASCII art string showing the DAG structure.
        """
        if not self.dag.tasks:
            return f"  DAG '{self.dag.dag_id}': (empty)\n"

        lines: list[str] = []
        lines.append(f"  DAG: {self.dag.dag_id}")
        lines.append(f"  Schedule: {self.dag.schedule.to_airflow_schedule() or 'Manual'}")
        lines.append(f"  Tasks: {len(self.dag.tasks)}")
        lines.append("")

        if self.has_cycles():
            lines.append("  WARNING: Graph contains cycles! Cannot show execution order.")
            cycles = self.detect_cycles()
            for cycle in cycles:
                lines.append(f"    Cycle: {' -> '.join(cycle + [cycle[0]])}")
            return "\n".join(lines)

        # Show in topological order with indentation based on depth
        try:
            order = self.topological_sort()
        except ValueError:
            lines.append("  WARNING: Cannot determine execution order")
            return "\n".join(lines)

        # Calculate depth for each node
        depths: dict[str, int] = {}
        for node in order:
            predecessors = list(self.graph.predecessors(node))
            if not predecessors:
                depths[node] = 0
            else:
                depths[node] = max(depths.get(p, 0) for p in predecessors) + 1

        # Render with depth-based indentation
        for node in order:
            depth = depths[node]
            task = self.dag.get_task(node)
            operator_str = task.operator if task else "?"

            indent = "    " * depth
            prefix = "|-- " if depth > 0 else "* "
            deps_str = ""
            if task and task.dependencies:
                deps_str = f"  <- [{', '.join(task.dependencies)}]"

            lines.append(f"  {indent}{prefix}{node} ({operator_str}){deps_str}")

        # Summary
        lines.append("")
        lines.append(f"  Roots: {', '.join(self.root_tasks())}")
        lines.append(f"  Leaves: {', '.join(self.leaf_tasks())}")
        lines.append(f"  Critical path: {' -> '.join(self.critical_path())}")
        lines.append(f"  Depth: {self.depth()}")

        return "\n".join(lines)
