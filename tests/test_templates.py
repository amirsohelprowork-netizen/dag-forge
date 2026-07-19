"""Tests for the template engine."""

import pytest
from dagforge.templates.engine import TemplateEngine

def test_template_engine_list():
    engine = TemplateEngine()
    templates = engine.list_templates()
    
    assert "etl_pipeline" in templates
    assert "sensor_process_notify" in templates
    assert "data_quality_check" in templates

def test_template_metadata():
    engine = TemplateEngine()
    meta = engine.get_metadata("etl_pipeline")
    
    assert meta.name == "etl_pipeline"
    assert "dag_id" in meta.variables
    assert meta.variables["dag_id"].required is True
    assert meta.variables["schedule"].default == "@daily"

def test_template_render():
    engine = TemplateEngine()
    
    variables = {
        "dag_id": "test_etl",
        "extract_command": "echo 'extract'",
        "transform_callable": "test.run",
        "load_command": "echo 'load'",
        "alert_email": "test@test.com",
    }
    
    dag = engine.render("etl_pipeline", variables)
    
    assert dag.dag_id == "test_etl"
    assert len(dag.tasks) == 4
    
    tasks = {t.task_id: t for t in dag.tasks}
    assert "extract" in tasks
    assert "transform" in tasks
    assert "load" in tasks
    assert "notify" in tasks
    
    assert tasks["extract"].operator_params["bash_command"] == "echo 'extract'"
    assert tasks["notify"].operator_params["to"] == "test@test.com"
