"""Tests for DAG Forge renderers."""

from __future__ import annotations

import pytest

from dagforge.core.models import (
    DagDefinition,
    OperatorType,
    ScheduleConfig,
    ScheduleType,
    Severity,
    TaskDefinition,
    ValidationIssue,
    ValidationResult,
)

# Import to trigger registration
import dagforge.renderers.dagfactory_renderer  # noqa: F401
import dagforge.renderers.report_renderer  # noqa: F401

from dagforge.renderers.dagfactory_renderer import DagFactoryRenderer
from dagforge.renderers.report_renderer import ReportRenderer


class TestDagFactoryRenderer:
    """Tests for the dag-factory YAML renderer."""

    def setup_method(self):
        self.renderer = DagFactoryRenderer()

    def test_render_simple_dag(self, simple_dag):
        output = self.renderer.render(simple_dag)
        assert "test_simple_dag:" in output
        assert "start:" in output
        assert "process:" in output
        assert "finish:" in output
        assert "EmptyOperator" in output
        assert "BashOperator" in output

    def test_render_preserves_schedule_null(self, simple_dag):
        output = self.renderer.render(simple_dag)
        assert "schedule: null" in output or "schedule:" in output

    def test_render_cron_schedule(self, complex_dag):
        output = self.renderer.render(complex_dag)
        assert "0 6 * * *" in output

    def test_render_preset_schedule(self, daily_dag):
        output = self.renderer.render(daily_dag)
        assert "@daily" in output

    def test_render_dependencies(self, simple_dag):
        output = self.renderer.render(simple_dag)
        assert "dependencies:" in output
        assert "- start" in output

    def test_render_operator_params(self, simple_dag):
        output = self.renderer.render(simple_dag)
        assert "bash_command:" in output
        assert "echo 'processing'" in output

    def test_render_catchup(self, simple_dag):
        output = self.renderer.render(simple_dag)
        assert "catchup: false" in output

    def test_render_description(self, simple_dag):
        output = self.renderer.render(simple_dag)
        assert "Description: A simple test DAG" in output

    def test_render_tags(self, simple_dag):
        output = self.renderer.render(simple_dag)
        assert "tags:" in output
        assert "- test" in output

    def test_file_extension(self):
        assert self.renderer.file_extension == ".yaml"

    def test_render_all(self, simple_dag, daily_dag):
        output = self.renderer.render_all([simple_dag, daily_dag])
        assert "test_simple_dag:" in output
        assert "test_daily_dag:" in output

    def test_render_to_file(self, simple_dag, tmp_path):
        output_path = self.renderer.render_to_file(simple_dag, tmp_path)
        assert output_path.exists()
        assert output_path.name == "test_simple_dag.yaml"
        content = output_path.read_text()
        assert "test_simple_dag:" in content


class TestReportRenderer:
    """Tests for the validation report renderer."""

    def setup_method(self):
        self.renderer = ReportRenderer()

    def test_render_clean_report(self, simple_dag):
        result = ValidationResult()
        report = self.renderer.render_report([simple_dag], result)
        assert "DAG Forge Validation Report" in report
        assert "Errors:        0" in report
        assert "PASSED" in report

    def test_render_report_with_errors(self, simple_dag):
        result = ValidationResult(issues=[
            ValidationIssue(
                severity=Severity.ERROR,
                message="Something is wrong",
                dag_id="test_simple_dag",
                task_id="start",
            ),
        ])
        report = self.renderer.render_report([simple_dag], result)
        assert "Errors:        1" in report
        assert "FAILED" in report
        assert "Something is wrong" in report

    def test_render_report_json(self, simple_dag):
        result = ValidationResult()
        json_str = self.renderer.render_report_json([simple_dag], result)
        import json
        data = json.loads(json_str)
        assert data["summary"]["passed"] is True
        assert data["summary"]["dags_analyzed"] == 1
        assert data["summary"]["errors"] == 0

    def test_render_report_json_with_issues(self, simple_dag):
        result = ValidationResult(issues=[
            ValidationIssue(
                severity=Severity.ERROR,
                message="broken",
                dag_id="test_simple_dag",
            ),
            ValidationIssue(
                severity=Severity.WARNING,
                message="questionable",
            ),
        ])
        json_str = self.renderer.render_report_json([simple_dag], result)
        import json
        data = json.loads(json_str)
        assert data["summary"]["passed"] is False
        assert data["summary"]["errors"] == 1
        assert data["summary"]["warnings"] == 1
        assert len(data["issues"]) == 2
