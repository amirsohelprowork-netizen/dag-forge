"""Operator registry with auto-discovery.

Scans the ``dagforge/operators/`` directory for Python modules that define
a module-level ``OPERATOR_SPEC`` variable of type :class:`OperatorSpec`.
Every discovered spec is indexed by its key, aliases, class path, and
class name so that look-ups from parsers, validators, and renderers are
fast and flexible.

Usage::

    from dagforge.operators import operator_registry

    spec = operator_registry.resolve("BashOperator")  # by alias
    spec = operator_registry.get("bash")               # by key
    class_path = operator_registry.class_path("bash")
    required   = operator_registry.required_params("bash")
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path
from typing import Iterator

from dagforge.operators._base import OperatorSpec

logger = logging.getLogger(__name__)


class OperatorRegistry:
    """Central registry for all known operator specifications."""

    def __init__(self) -> None:
        self._specs: dict[str, OperatorSpec] = {}          # key -> spec
        self._alias_index: dict[str, str] = {}             # normalized alias -> key
        self._class_path_index: dict[str, str] = {}        # lowered class path -> key
        self._class_name_index: dict[str, str] = {}        # lowered class name -> key

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, spec: OperatorSpec) -> None:
        """Register an :class:`OperatorSpec`.

        Raises ``ValueError`` if the key is already taken.
        """
        if spec.key in self._specs:
            raise ValueError(
                f"Operator key '{spec.key}' is already registered by "
                f"{self._specs[spec.key].class_path}"
            )

        self._specs[spec.key] = spec

        # Index aliases (normalized to lower, no separators)
        for alias in spec.aliases:
            norm = alias.lower().replace("_", "").replace("-", "").replace(" ", "")
            self._alias_index[norm] = spec.key

        # Index class path and class name
        self._class_path_index[spec.class_path.lower()] = spec.key
        class_name = spec.class_path.rsplit(".", 1)[-1].lower()
        self._class_name_index[class_name] = spec.key

        logger.debug("Registered operator: %s -> %s", spec.key, spec.class_path)

    # ------------------------------------------------------------------
    # Look-ups
    # ------------------------------------------------------------------

    def get(self, key: str) -> OperatorSpec:
        """Get an operator spec by its exact key.

        Raises ``KeyError`` if the key is not found.
        """
        if key not in self._specs:
            available = ", ".join(sorted(self._specs)) or "none"
            raise KeyError(
                f"No operator registered for key '{key}'. "
                f"Available: {available}"
            )
        return self._specs[key]

    def resolve(self, raw: str) -> OperatorSpec:
        """Resolve an operator from a raw string.

        The resolution order is:
        1. Exact key match
        2. Normalized alias match
        3. Full class-path match (case-insensitive)
        4. Class-name-only match (case-insensitive)
        5. Falls back to 'empty' operator (with a warning)
        """
        if not raw:
            return self.get("empty")

        trimmed = raw.strip()

        # 1. Exact key
        lower = trimmed.lower()
        if lower in self._specs:
            return self._specs[lower]

        # 2. Alias
        normalized = lower.replace("_", "").replace("-", "").replace(" ", "")
        if normalized in self._alias_index:
            return self._specs[self._alias_index[normalized]]

        # 3. Full class path
        if lower in self._class_path_index:
            return self._specs[self._class_path_index[lower]]

        # 4. Class name only
        if normalized in self._class_name_index:
            return self._specs[self._class_name_index[normalized]]

        # 5. Fallback
        logger.warning("Unknown operator '%s', defaulting to 'empty'", raw)
        return self.get("empty")

    def has(self, key: str) -> bool:
        """Return True if a key is registered."""
        return key in self._specs

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    def class_path(self, key: str) -> str:
        """Return the fully-qualified Airflow class path for an operator key."""
        return self.get(key).class_path

    def required_params(self, key: str) -> set[str]:
        """Return required parameter names for an operator key."""
        return self.get(key).required_params

    def optional_params(self, key: str) -> set[str]:
        """Return optional parameter names for an operator key."""
        return self.get(key).optional_params

    def task_specs_param(self, key: str) -> str | None:
        """Return the task_specs mapping parameter for an operator key."""
        return self.get(key).task_specs_param

    def all_specs(self) -> dict[str, OperatorSpec]:
        """Return a copy of all registered operator specs."""
        return dict(self._specs)

    @property
    def available_keys(self) -> list[str]:
        """Sorted list of all registered operator keys."""
        return sorted(self._specs)

    # ------------------------------------------------------------------
    # Auto-discovery
    # ------------------------------------------------------------------

    def discover_builtin(self) -> None:
        """Import all sibling modules in the ``operators`` package.

        Each module is expected to define a module-level ``OPERATOR_SPEC``
        of type :class:`OperatorSpec`.  Modules whose name starts with ``_``
        are skipped (they are internal infrastructure).
        """
        package_dir = Path(__file__).parent

        for module_info in pkgutil.iter_modules([str(package_dir)]):
            if module_info.name.startswith("_"):
                continue
            fqn = f"dagforge.operators.{module_info.name}"
            try:
                mod = importlib.import_module(fqn)
                spec = getattr(mod, "OPERATOR_SPEC", None)
                if isinstance(spec, OperatorSpec):
                    self.register(spec)
                else:
                    logger.debug(
                        "Module %s has no OPERATOR_SPEC, skipping", fqn
                    )
            except Exception:
                logger.exception("Failed to load operator module %s", fqn)

    def discover_directory(self, directory: Path) -> None:
        """Discover operator specs from an external directory.

        Works the same as :meth:`discover_builtin` but for user-provided
        directories, enabling extensibility without modifying the package.
        """
        if not directory.is_dir():
            logger.warning("Operator directory does not exist: %s", directory)
            return

        for py_file in sorted(directory.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            module_name = py_file.stem
            # Use importlib to load from arbitrary path
            import importlib.util

            spec_loader = importlib.util.spec_from_file_location(
                f"dagforge_custom_operators.{module_name}", py_file
            )
            if spec_loader is None or spec_loader.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec_loader)
            try:
                spec_loader.loader.exec_module(mod)  # type: ignore[union-attr]
                op_spec = getattr(mod, "OPERATOR_SPEC", None)
                if isinstance(op_spec, OperatorSpec):
                    self.register(op_spec)
            except Exception:
                logger.exception(
                    "Failed to load custom operator from %s", py_file
                )
