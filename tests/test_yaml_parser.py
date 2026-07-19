"""Tests for DAG Forge YAML parser."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

# Import to trigger registration
import dagforge.parsers.yaml_parser  # noqa: F401

from dagforge.core.exceptions import ParseError
from dagforge.core.models import OperatorType, ScheduleType
from dagforge.parsers.yaml_parser import YamlParser


class TestYamlParser:
    """Tests for the YAML input parser."""

    def setup_method(self):
        self.parser = YamlParser()

    def test_supported_extensions(self):
        assert ".yaml" in self.parser.supported_extensions
        assert ".yml" in self.parser.supported_extensions

    def test_can_handle_yaml(self, tmp_path):
        f = tmp_path / "test.yaml"
        f.touch()
        assert self.parser.can_handle(f)

    def test_cannot_handle_xlsx(self, tmp_path):
        f = tmp_path / "test.xlsx"
        f.touch()
        assert not self.parser.can_handle(f)

    def test_parse_dagfactory_format(self, tmp_path):
        content = dedent("""\
            my_test_dag:
              default_args:
                owner: test_user
                start_date: "2024-01-01"
              schedule: "@daily"
              Description: A test DAG
              catchup: false
              tasks:
                start_task:
                  operator: airflow.operators.empty.EmptyOperator
                process_task:
                  operator: airflow.operators.bash.BashOperator
                  bash_command: "echo hello"
                  dependencies:
                    - start_task
        """)
        f = tmp_path / "test.yaml"
        f.write_text(content)

        result = self.parser.parse(f)
        assert len(result.dags) == 1

        dag = result.dags[0]
        assert dag.dag_id == "my_test_dag"
        assert dag.schedule.type == ScheduleType.PRESET
        assert dag.schedule.expression == "daily"
        assert len(dag.tasks) == 2
        assert dag.tasks[1].dependencies == ["start_task"]

    def test_parse_cron_schedule(self, tmp_path):
        content = dedent("""\
            cron_dag:
              schedule: "0 6 * * *"
              tasks:
                task_1:
                  operator: bash
                  bash_command: "echo test"
        """)
        f = tmp_path / "test.yaml"
        f.write_text(content)

        result = self.parser.parse(f)
        dag = result.dags[0]
        assert dag.schedule.type == ScheduleType.CRON
        assert dag.schedule.expression == "0 6 * * *"

    def test_parse_null_schedule(self, tmp_path):
        content = dedent("""\
            manual_dag:
              schedule: null
              tasks:
                task_1:
                  operator: empty
        """)
        f = tmp_path / "test.yaml"
        f.write_text(content)

        result = self.parser.parse(f)
        dag = result.dags[0]
        assert dag.schedule.type == ScheduleType.MANUAL

    def test_parse_multiple_dags(self, tmp_path):
        content = dedent("""\
            dag_one:
              schedule: "@daily"
              tasks:
                t1:
                  operator: empty
            dag_two:
              schedule: null
              tasks:
                t1:
                  operator: bash
                  bash_command: "echo two"
        """)
        f = tmp_path / "test.yaml"
        f.write_text(content)

        result = self.parser.parse(f)
        assert len(result.dags) == 2
        dag_ids = {d.dag_id for d in result.dags}
        assert dag_ids == {"dag_one", "dag_two"}

    def test_parse_file_not_found(self):
        with pytest.raises(ParseError):
            self.parser.parse(Path("/nonexistent/file.yaml"))

    def test_parse_invalid_yaml(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("{{{{invalid yaml")
        with pytest.raises(ParseError):
            self.parser.parse(f)

    def test_parse_empty_file(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("")
        with pytest.raises(ParseError):
            self.parser.parse(f)
