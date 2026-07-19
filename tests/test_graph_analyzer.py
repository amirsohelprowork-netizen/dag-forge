"""Tests for DAG Forge graph analyzer."""

from __future__ import annotations

import pytest

from dagforge.core.models import (
    DagDefinition,
    OperatorType,
    ScheduleConfig,
    ScheduleType,
    TaskDefinition,
)
from dagforge.graph.analyzer import GraphAnalyzer


class TestGraphAnalyzer:
    """Tests for the GraphAnalyzer."""

    def test_linear_dag_no_cycles(self, simple_dag):
        analyzer = GraphAnalyzer(simple_dag)
        assert not analyzer.has_cycles()
        assert analyzer.detect_cycles() == []

    def test_topological_sort_linear(self, simple_dag):
        analyzer = GraphAnalyzer(simple_dag)
        order = analyzer.topological_sort()
        assert order == ["start", "process", "finish"]

    def test_root_tasks(self, simple_dag):
        analyzer = GraphAnalyzer(simple_dag)
        roots = analyzer.root_tasks()
        assert roots == ["start"]

    def test_leaf_tasks(self, simple_dag):
        analyzer = GraphAnalyzer(simple_dag)
        leaves = analyzer.leaf_tasks()
        assert leaves == ["finish"]

    def test_critical_path(self, simple_dag):
        analyzer = GraphAnalyzer(simple_dag)
        path = analyzer.critical_path()
        assert path == ["start", "process", "finish"]

    def test_depth(self, simple_dag):
        analyzer = GraphAnalyzer(simple_dag)
        assert analyzer.depth() == 3

    def test_complex_dag_execution_order(self, complex_dag):
        analyzer = GraphAnalyzer(complex_dag)
        order = analyzer.topological_sort()
        # start must come before extract_data
        assert order.index("start") < order.index("extract_data")
        # extract must come before transform
        assert order.index("extract_data") < order.index("transform_data")
        # transform must come before load
        assert order.index("transform_data") < order.index("load_data")

    def test_empty_dag(self, empty_dag):
        analyzer = GraphAnalyzer(empty_dag)
        assert not analyzer.has_cycles()
        assert analyzer.topological_sort() == []
        assert analyzer.root_tasks() == []
        assert analyzer.leaf_tasks() == []
        assert analyzer.depth() == 0

    def test_mermaid_output(self, simple_dag):
        analyzer = GraphAnalyzer(simple_dag)
        mermaid = analyzer.to_mermaid()
        assert "graph TD" in mermaid
        assert "start" in mermaid
        assert "process" in mermaid
        assert "-->" in mermaid

    def test_ascii_output(self, simple_dag):
        analyzer = GraphAnalyzer(simple_dag)
        ascii_graph = analyzer.to_ascii()
        assert "test_simple_dag" in ascii_graph
        assert "start" in ascii_graph
        assert "process" in ascii_graph
        assert "Critical path" in ascii_graph

    def test_single_task_dag(self):
        dag = DagDefinition(
            dag_id="single",
            tasks=[TaskDefinition(task_id="only_task")],
        )
        analyzer = GraphAnalyzer(dag)
        assert not analyzer.has_cycles()
        assert analyzer.topological_sort() == ["only_task"]
        assert analyzer.root_tasks() == ["only_task"]
        assert analyzer.leaf_tasks() == ["only_task"]
        assert analyzer.depth() == 1

    def test_parallel_tasks(self):
        dag = DagDefinition(
            dag_id="parallel",
            tasks=[
                TaskDefinition(task_id="start"),
                TaskDefinition(task_id="branch_a", dependencies=["start"]),
                TaskDefinition(task_id="branch_b", dependencies=["start"]),
                TaskDefinition(
                    task_id="merge",
                    dependencies=["branch_a", "branch_b"],
                ),
            ],
        )
        analyzer = GraphAnalyzer(dag)
        assert not analyzer.has_cycles()
        order = analyzer.topological_sort()
        assert order[0] == "start"
        assert order[-1] == "merge"
        assert analyzer.depth() == 3
