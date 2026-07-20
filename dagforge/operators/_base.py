"""Base models for operator specifications.

Each operator in DAG Forge is described by an ``OperatorSpec`` instance that
captures everything the framework needs to know: the Airflow class path,
parameter definitions (including nested parameters), aliases for flexible
parsing, and the mapping from Excel's ``task_specs`` column.

To add a new operator, create a new ``.py`` file in the ``dagforge/operators/``
directory and define a module-level ``OPERATOR_SPEC`` variable of type
``OperatorSpec``.  The registry will auto-discover it at import time.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ParamSpec(BaseModel):
    """Specification for a single operator parameter.

    Supports nested parameters via the ``nested`` field, enabling
    rich descriptions for operators like BigQuery whose ``configuration``
    parameter contains structured sub-keys.
    """

    name: str = Field(..., description="Parameter name as passed to the operator constructor")
    description: str = Field(default="", description="Human-readable description")
    required: bool = Field(default=False, description="Whether this parameter is mandatory")
    type: str = Field(
        default="string",
        description="Expected value type: string, int, bool, float, list, dict, any",
    )
    default: Any = Field(default=None, description="Default value if not provided")
    nested: dict[str, ParamSpec] = Field(
        default_factory=dict,
        description="Nested parameter specifications (for dict-typed params)",
    )

    # Allow ParamSpec to reference itself in nested
    model_config = {"arbitrary_types_allowed": True}


class OperatorSpec(BaseModel):
    """Complete specification for one Airflow operator type.

    This is the single source of truth for an operator's metadata.
    Each built-in operator file defines exactly one ``OPERATOR_SPEC``
    constant of this type.
    """

    key: str = Field(
        ...,
        description="Short identifier used in configs, e.g. 'bash', 'python'",
    )
    class_path: str = Field(
        ...,
        description="Fully-qualified Airflow operator class, "
        "e.g. 'airflow.operators.bash.BashOperator'",
    )
    description: str = Field(
        default="",
        description="Human-readable description of the operator",
    )
    aliases: list[str] = Field(
        default_factory=list,
        description="Alternative names accepted during parsing "
        "(e.g. 'BashOperator', 'bash_operator')",
    )
    params: list[ParamSpec] = Field(
        default_factory=list,
        description="All parameters this operator accepts (required + optional)",
    )
    task_specs_param: str | None = Field(
        default=None,
        description="Which param the Excel 'task_specs' column maps to "
        "(None if task_specs is not applicable)",
    )

    # -- Derived helpers -----------------------------------------------------

    @property
    def required_params(self) -> set[str]:
        """Return the set of required parameter names."""
        return {p.name for p in self.params if p.required}

    @property
    def optional_params(self) -> set[str]:
        """Return the set of optional parameter names."""
        return {p.name for p in self.params if not p.required}

    @property
    def all_param_names(self) -> set[str]:
        """Return all known parameter names."""
        return {p.name for p in self.params}

    def get_param(self, name: str) -> ParamSpec | None:
        """Look up a parameter spec by name."""
        for p in self.params:
            if p.name == name:
                return p
        return None
