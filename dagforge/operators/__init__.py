"""Operator specifications for DAG Forge.

This package contains one Python file per supported Airflow operator.
Each file defines an ``OPERATOR_SPEC`` constant of type
:class:`~dagforge.operators._base.OperatorSpec`.

To add a new operator, simply create a new ``.py`` file in this directory
with a module-level ``OPERATOR_SPEC``.  The registry will pick it up
automatically at import time.

Public API
----------
- ``operator_registry`` — the singleton :class:`OperatorRegistry` with all
  built-in operators already loaded.
- ``OperatorSpec``, ``ParamSpec`` — the models for defining operators.
"""

from dagforge.operators._base import OperatorSpec, ParamSpec
from dagforge.operators._registry import OperatorRegistry

# Global singleton — discovered once, used everywhere.
operator_registry = OperatorRegistry()
operator_registry.discover_builtin()

__all__ = [
    "operator_registry",
    "OperatorRegistry",
    "OperatorSpec",
    "ParamSpec",
]
