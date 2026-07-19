"""Jinja2 template engine for DAG Forge."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from pydantic import BaseModel, Field

from dagforge.core.exceptions import ParseError
from dagforge.core.models import DagDefinition
from dagforge.parsers.yaml_parser import _parse_dag_from_dict, _yaml

logger = logging.getLogger(__name__)


class TemplateVariable(BaseModel):
    """Metadata for a single template variable."""
    description: str = ""
    type: str = "string"
    required: bool = True
    default: Any = None


class TemplateMetadata(BaseModel):
    """Metadata sidecar for a Jinja template."""
    name: str
    description: str = ""
    version: str = "1.0"
    variables: dict[str, TemplateVariable] = Field(default_factory=dict)
    example_values: dict[str, Any] = Field(default_factory=dict)


class TemplateEngine:
    """Discovers and renders Jinja2 templates into DagDefinitions."""

    def __init__(self, custom_dirs: list[Path] | None = None) -> None:
        self.builtin_dir = Path(__file__).parent / "builtins"
        
        self.search_dirs = [self.builtin_dir]
        if custom_dirs:
            self.search_dirs.extend(custom_dirs)
            
        self.env = Environment(
            loader=FileSystemLoader([str(d) for d in self.search_dirs]),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def list_templates(self) -> dict[str, TemplateMetadata]:
        """List all available templates by name."""
        templates: dict[str, TemplateMetadata] = {}
        
        for search_dir in reversed(self.search_dirs):
            if not search_dir.exists():
                continue
                
            for meta_file in search_dir.glob("*.meta.yaml"):
                template_name = meta_file.name.replace(".meta.yaml", "")
                
                try:
                    with open(meta_file, encoding="utf-8") as f:
                        meta_data = _yaml.load(f)
                        if meta_data:
                            templates[template_name] = TemplateMetadata(**meta_data)
                except Exception as e:
                    logger.warning("Failed to load metadata %s: %s", meta_file, e)
                    
        return templates

    def get_metadata(self, template_name: str) -> TemplateMetadata:
        """Get metadata for a specific template."""
        templates = self.list_templates()
        if template_name not in templates:
            raise ParseError(f"Template not found: {template_name}")
        return templates[template_name]

    def render(self, template_name: str, variables: dict[str, Any]) -> DagDefinition:
        """Render a template into a DagDefinition."""
        meta = self.get_metadata(template_name)
        
        # Validate variables
        missing = []
        for var_name, var_meta in meta.variables.items():
            if var_name not in variables:
                if var_meta.required and var_meta.default is None:
                    missing.append(var_name)
                else:
                    variables[var_name] = var_meta.default
                    
        if missing:
            raise ParseError(f"Missing required variables for template {template_name}: {missing}")

        template_file = f"{template_name}.yaml.j2"
        try:
            template = self.env.get_template(template_file)
            rendered_yaml = template.render(**variables)
        except TemplateNotFound as e:
            raise ParseError(f"Template file not found: {template_file}") from e
        except Exception as e:
            raise ParseError(f"Failed to render template {template_name}: {e}") from e
            
        try:
            raw_data = _yaml.load(rendered_yaml)
            if not raw_data or not isinstance(raw_data, dict):
                raise ValueError("Template rendered to empty or invalid YAML")
                
            # Usually the root is a single DAG ID mapping to the config
            if len(raw_data) == 1:
                dag_id = list(raw_data.keys())[0]
                dag_data = raw_data[dag_id]
                return _parse_dag_from_dict(dag_id, dag_data)
            else:
                # If there are multiple keys, maybe it's the dags list format
                if "dags" in raw_data and isinstance(raw_data["dags"], list) and raw_data["dags"]:
                    dag_data = raw_data["dags"][0]
                    dag_id = str(dag_data.get("dag_id", dag_data.get("id", "")))
                    return _parse_dag_from_dict(dag_id, dag_data)
                else:
                    raise ValueError("Template must render exactly one DAG definition")
                    
        except Exception as e:
            raise ParseError(f"Failed to parse rendered template {template_name}: {e}") from e
