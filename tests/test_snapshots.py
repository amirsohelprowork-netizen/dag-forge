"""Snapshot tests for DAG generation."""

import json
from pathlib import Path

import pytest
from dagforge.parsers.yaml_parser import YamlParser
from dagforge.renderers.dagfactory_renderer import DagFactoryRenderer

def test_snapshot_yaml_to_yaml():
    yaml_content = """
test_snapshot:
  schedule: "0 0 * * *"
  tasks:
    task1:
      operator: bash
      bash_command: "echo hi"
    task2:
      operator: bash
      bash_command: "echo bye"
      dependencies: [task1]
"""
    tmp_input = Path("tmp_snapshot_input.yaml")
    tmp_input.write_text(yaml_content)
    
    parser = YamlParser()
    result = parser.parse(tmp_input)
    assert len(result.dags) == 1
    
    renderer = DagFactoryRenderer()
    output = renderer.render(result.dags[0])
    
    # Cleanup
    tmp_input.unlink()
    
    # Verify exact match
    assert "test_snapshot:" in output
    assert "task1" in output
    assert "task2" in output
    assert "dependencies:" in output
    assert "- task1" in output
