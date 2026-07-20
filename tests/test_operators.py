"""Tests for the dagforge.operators package.

Covers auto-discovery, registry look-ups, alias resolution,
nested ParamSpec, and the public API contract.
"""

from __future__ import annotations

import pytest

from dagforge.operators import operator_registry, OperatorSpec, ParamSpec
from dagforge.operators._registry import OperatorRegistry
from dagforge.core.models import OperatorType


# -----------------------------------------------------------------------
# Discovery tests
# -----------------------------------------------------------------------

class TestAutoDiscovery:
    """Verify that all 18 built-in operators are discovered."""

    EXPECTED_KEYS = {
        "empty", "bash", "python", "branch_python", "short_circuit",
        "external_task_sensor", "email", "trigger_dag_run", "http",
        "sql_sensor", "postgres", "mysql", "s3_to_gcs", "gcs_to_bigquery",
        "bigquery", "slack", "docker", "kubernetes_pod",
    }

    def test_all_builtin_operators_discovered(self):
        discovered = set(operator_registry.available_keys)
        assert discovered == self.EXPECTED_KEYS

    def test_count_matches(self):
        assert len(operator_registry.all_specs()) == 18


# -----------------------------------------------------------------------
# Lookup tests
# -----------------------------------------------------------------------

class TestRegistryLookup:
    """Verify get(), resolve(), and convenience accessors."""

    def test_get_by_key(self):
        spec = operator_registry.get("bash")
        assert spec.key == "bash"
        assert spec.class_path == "airflow.operators.bash.BashOperator"

    def test_get_unknown_raises(self):
        with pytest.raises(KeyError, match="No operator registered"):
            operator_registry.get("nonexistent_operator")

    def test_has_key(self):
        assert operator_registry.has("bash")
        assert not operator_registry.has("nonexistent")

    def test_class_path(self):
        assert operator_registry.class_path("empty") == "airflow.operators.empty.EmptyOperator"

    def test_required_params(self):
        assert operator_registry.required_params("bash") == {"bash_command"}
        assert operator_registry.required_params("empty") == set()
        assert operator_registry.required_params("kubernetes_pod") == {"name", "namespace", "image"}

    def test_optional_params(self):
        optional = operator_registry.optional_params("bash")
        assert "env" in optional
        assert "cwd" in optional
        assert "bash_command" not in optional  # required, not optional

    def test_task_specs_param(self):
        assert operator_registry.task_specs_param("bash") == "bash_command"
        assert operator_registry.task_specs_param("python") == "python_callable"
        assert operator_registry.task_specs_param("trigger_dag_run") == "trigger_dag_id"
        assert operator_registry.task_specs_param("empty") is None


# -----------------------------------------------------------------------
# Resolve tests (alias, class path, class name)
# -----------------------------------------------------------------------

class TestRegistryResolve:
    """Verify flexible operator resolution."""

    def test_resolve_by_key(self):
        assert operator_registry.resolve("bash").key == "bash"

    def test_resolve_by_key_case_insensitive(self):
        assert operator_registry.resolve("BASH").key == "bash"

    def test_resolve_by_alias(self):
        assert operator_registry.resolve("BashOperator").key == "bash"

    def test_resolve_by_class_path(self):
        assert operator_registry.resolve(
            "airflow.operators.bash.BashOperator"
        ).key == "bash"

    def test_resolve_by_class_name(self):
        assert operator_registry.resolve("BranchPythonOperator").key == "branch_python"

    def test_resolve_branch_alias(self):
        assert operator_registry.resolve("branch").key == "branch_python"

    def test_resolve_trigger_alias(self):
        assert operator_registry.resolve("trigger").key == "trigger_dag_run"

    def test_resolve_sensor_alias(self):
        assert operator_registry.resolve("sensor").key == "external_task_sensor"

    def test_resolve_unknown_falls_back_to_empty(self):
        spec = operator_registry.resolve("totally_unknown_operator")
        assert spec.key == "empty"

    def test_resolve_none_returns_empty(self):
        assert operator_registry.resolve("").key == "empty"

    def test_resolve_kubernetes_alias(self):
        assert operator_registry.resolve("K8sPodOperator").key == "kubernetes_pod"


# -----------------------------------------------------------------------
# OperatorSpec & ParamSpec model tests
# -----------------------------------------------------------------------

class TestOperatorSpec:
    """Verify OperatorSpec model properties."""

    def test_required_params_property(self):
        spec = OperatorSpec(
            key="test_op",
            class_path="test.TestOperator",
            params=[
                ParamSpec(name="a", required=True),
                ParamSpec(name="b", required=False),
                ParamSpec(name="c", required=True),
            ],
        )
        assert spec.required_params == {"a", "c"}

    def test_optional_params_property(self):
        spec = OperatorSpec(
            key="test_op",
            class_path="test.TestOperator",
            params=[
                ParamSpec(name="a", required=True),
                ParamSpec(name="b", required=False),
            ],
        )
        assert spec.optional_params == {"b"}

    def test_get_param(self):
        spec = OperatorSpec(
            key="test_op",
            class_path="test.TestOperator",
            params=[
                ParamSpec(name="alpha", description="first"),
                ParamSpec(name="beta", description="second"),
            ],
        )
        assert spec.get_param("alpha") is not None
        assert spec.get_param("alpha").description == "first"
        assert spec.get_param("missing") is None


class TestParamSpecNested:
    """Verify nested parameter support."""

    def test_nested_param_spec(self):
        """BigQuery configuration has nested query/load sub-params."""
        bq_spec = operator_registry.get("bigquery")
        config_param = bq_spec.get_param("configuration")
        assert config_param is not None
        assert config_param.required is True
        assert config_param.type == "dict"
        assert "query" in config_param.nested
        assert "load" in config_param.nested

    def test_deeply_nested_params(self):
        """BigQuery query config has further nested params."""
        bq_spec = operator_registry.get("bigquery")
        config_param = bq_spec.get_param("configuration")
        query_spec = config_param.nested["query"]
        assert "query" in query_spec.nested  # SQL query string
        assert "useLegacySql" in query_spec.nested

    def test_custom_nested_param(self):
        """Verify a custom ParamSpec with nesting works."""
        param = ParamSpec(
            name="config",
            type="dict",
            nested={
                "database": ParamSpec(
                    name="database",
                    type="dict",
                    nested={
                        "host": ParamSpec(name="host", required=True),
                        "port": ParamSpec(name="port", type="int", default=5432),
                    },
                ),
            },
        )
        assert "database" in param.nested
        assert "host" in param.nested["database"].nested
        assert param.nested["database"].nested["port"].default == 5432


# -----------------------------------------------------------------------
# OperatorType string-constants backward compatibility
# -----------------------------------------------------------------------

class TestOperatorTypeCompat:
    """Verify that the OperatorType string-constants class works like it used to."""

    def test_constants_are_strings(self):
        assert OperatorType.BASH == "bash"
        assert OperatorType.EMPTY == "empty"
        assert isinstance(OperatorType.BASH, str)

    def test_values_returns_all_keys(self):
        vals = OperatorType.values()
        assert "bash" in vals
        assert "python" in vals
        assert len(vals) == 18

    def test_class_getitem(self):
        assert OperatorType["bash"] == "bash"


# -----------------------------------------------------------------------
# Registry isolation test
# -----------------------------------------------------------------------

class TestRegistryIsolation:
    """Verify that creating a new registry doesn't pollute the global one."""

    def test_fresh_registry_is_empty(self):
        reg = OperatorRegistry()
        assert reg.available_keys == []

    def test_register_custom_spec(self):
        reg = OperatorRegistry()
        reg.register(OperatorSpec(
            key="custom_op",
            class_path="my_package.operators.CustomOperator",
            aliases=["CustomOp"],
            params=[
                ParamSpec(name="param1", required=True),
            ],
        ))
        assert reg.has("custom_op")
        assert reg.resolve("CustomOp").key == "custom_op"
        assert reg.required_params("custom_op") == {"param1"}

    def test_duplicate_key_raises(self):
        reg = OperatorRegistry()
        spec = OperatorSpec(key="dup", class_path="a.B")
        reg.register(spec)
        with pytest.raises(ValueError, match="already registered"):
            reg.register(spec)
