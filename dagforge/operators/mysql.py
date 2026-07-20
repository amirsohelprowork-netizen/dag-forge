"""MySQL operator specification."""

from dagforge.operators._base import OperatorSpec, ParamSpec

OPERATOR_SPEC = OperatorSpec(
    key="mysql",
    class_path="airflow.providers.mysql.operators.mysql.MySqlOperator",
    description="Executes SQL on a MySQL database.",
    aliases=["MySqlOperator", "MysqlOperator"],
    task_specs_param="sql",
    params=[
        ParamSpec(name="sql", required=True, description="SQL statement(s) to execute", type="any"),
        ParamSpec(name="mysql_conn_id", description="MySQL connection ID", default="mysql_default"),
        ParamSpec(name="autocommit", description="Whether to auto-commit", type="bool", default=False),
        ParamSpec(name="parameters", description="Query parameters", type="any"),
        ParamSpec(name="database", description="Target database name"),
    ],
)
