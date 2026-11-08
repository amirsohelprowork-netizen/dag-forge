"""Exercise the scaffolded Excel workflow through the public CLI."""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from openpyxl import load_workbook
from ruamel.yaml import YAML

from dagforge.cli.main import cli
from dagforge.operators import operator_registry


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["init"])
    assert result.exit_code == 0, result.output
    return runner


def _edit(sheet, updates):
    workbook_path = Path("input/starter.xlsx")
    workbook = load_workbook(workbook_path)
    for cell, value in updates.items():
        workbook[sheet][cell] = value
    workbook.save(workbook_path)
    workbook.close()


def _check_both(runner, path, exit_code, *options):
    validate = runner.invoke(cli, ["validate", path, "--format", "json", *options])
    generate = runner.invoke(cli, ["generate", path, "--report", "json", *options])
    assert validate.exit_code == generate.exit_code == exit_code, (
        validate.output, generate.output
    )
    report = json.loads(validate.stdout)
    assert report == json.loads(generate.stdout)
    assert report["summary"]["passed"] == (exit_code == 0)
    if exit_code:
        assert not Path("output_yamls").exists()
    return report


def test_init_workbook_can_be_edited_validated_and_generated(project):
    path = Path("input/starter.xlsx")
    workbook = load_workbook(path)
    assert workbook.sheetnames == ["Start here", "Dag_config", "Task_details", "Dependency_flow"]
    assert workbook["Dag_config"].data_validations.dataValidation[0].formula1.startswith('"manual,')
    operator_list = workbook["Task_details"].data_validations.dataValidation[0].formula1
    assert operator_list.strip('"').split(",") == operator_registry.available_keys
    workbook.close()
    assert project.invoke(cli, ["validate", "input", "--strict"]).exit_code == 0

    _edit("Task_details", {"D3": 'echo "Hi, team"', "E3": "retries: 2"})
    edited = path.read_bytes()
    assert project.invoke(cli, ["init"]).exit_code == 0
    assert path.read_bytes() == edited
    _check_both(project, "input/starter.xlsx", 0, "--strict")

    generated = YAML(typ="safe").load(Path("output_yamls/starter_pipeline.yaml"))
    dag = generated["starter_pipeline"]
    assert dag["schedule"] is None
    task = dag["tasks"]["say_hello"]
    assert task["bash_command"] == 'echo "Hi, team"'
    assert task["retries"] == 2
    assert task["dependencies"] == ["start"]


def test_legacy_excel_sheet_and_column_names_still_work(project):
    path = Path("input/starter.xlsx")
    workbook = load_workbook(path)
    workbook["Dag_config"].title = "Dad_config"
    for sheet, aliases in {
        "Dad_config": {"A1": "dad_ref", "B1": "DAG_ID", "G1": "Default_arg"},
        "Task_details": {"B1": "Task_ID", "C1": "Task_type", "D1": "Task_specs"},
        "Dependency_flow": {"B1": "Task_id", "C1": "Upstream_task"},
    }.items():
        for cell, value in aliases.items():
            workbook[sheet][cell] = value
    workbook.save(path)
    workbook.close()
    _check_both(project, str(path), 0, "--strict")


@pytest.mark.parametrize(
    ("sheet", "updates", "code", "cell", "message"),
    [
        ("Task_details", {"D3": None}, 1, "Task_details!D3", "Missing required parameter"),
        ("Task_details", {"E3": "retries: -1"}, 1, "Task_details!E3", "must be non-negative"),
        ("Task_details", {"C3": "basch"}, 2, "Task_details!C3", "Unknown operator"),
        ("Task_details", {"B3": "say hello"}, 2, "Task_details!B3", "is invalid"),
        ("Task_details", {"E3": "retries 2"}, 2, "Task_details!E3", "Expected 'key: value'"),
        ("Dependency_flow", {"B2": "no_task"}, 2, "Dependency_flow!B2", "Unknown task"),
        ("Dependency_flow", {"C2": "say_hello"}, 2, "Dependency_flow!C2", "depend on itself"),
        ("Dependency_flow", {"A4": "demo", "B4": "say_hello", "C4": "typo"}, 2,
         "Dependency_flow!C4", "Unknown upstream task"),
        ("Dag_config", {"C2": "cron", "D2": "99 0 * * *"}, 1, "Dag_config!D2",
         "Invalid minute field"),
    ],
)
def test_excel_diagnostics_locate_the_input(project, sheet, updates, code, cell, message):
    _edit(sheet, updates)
    report = _check_both(project, "input/starter.xlsx", code)
    issue = next(issue for issue in report["issues"] if message in issue["message"])
    assert cell in " ".join([issue["message"], *issue["locations"]])


def test_policy_and_overlay_are_shared(project):
    _edit("Dag_config", {"F2": None})
    report = _check_both(project, "input/starter.xlsx", 1)
    issue = next(issue for issue in report["issues"] if "[POLICY require_tags]" in issue["message"])
    assert issue["locations"] == ["input/starter.xlsx / Dag_config!F2"]

    config = Path("dagforge.toml")
    config.write_text(
        config.read_text() + '\n[dagforge.environments.prod]\ntags = ["prod"]\n',
        encoding="utf-8",
    )
    _check_both(project, "input/starter.xlsx", 0, "--env", "prod")


def test_strict_warnings_fail_the_report_and_block_output(project):
    _edit("Dag_config", {"E2": None})
    report = _check_both(project, "input/starter.xlsx", 1, "--strict")
    assert report["summary"]["errors"] == 0
    assert report["summary"]["warnings"] > 0


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("broken.xlsx", "not an Excel workbook"),
        ("broken.yaml", "bad: ["),
        ("broken.yaml", "valid: {}\nbad-id: {}\n"),
        ("broken.json", '{"dags": [{"dag_id": "valid"}, {}]}'),
    ],
)
def test_a_mixed_batch_fails_when_any_input_cannot_be_parsed(project, filename, content):
    (Path("input") / filename).write_text(content, encoding="utf-8")
    report = _check_both(project, "input", 2)
    assert report["summary"]["dags_analyzed"] == 2
    assert any(issue["locations"] == [f"input/{filename}"] for issue in report["issues"])
