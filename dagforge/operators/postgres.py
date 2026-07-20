"""Postgres operator specification."""

from dagforge.operators._base import OperatorSpec, ParamSpec

OPERATOR_SPEC = OperatorSpec(
    key="postgres",
    class_path="airflow.providers.postgres.operators.postgres.PostgresOperator",
    description="Executes SQL on a Postgres database.",
    aliases=["PostgresOperator"],
    task_specs_param="sql",
    params=[
        ParamSpec(name="sql", required=True, description="SQL statement(s) to execute", type="any"),
        ParamSpec(name="postgres_conn_id", description="Postgres connection ID", default="postgres_default"),
        ParamSpec(name="autocommit", description="Whether to auto-commit", type="bool", default=False),
        ParamSpec(name="parameters", description="Query parameters", type="any"),
        ParamSpec(name="database", description="Target database name"),
    ],
)
