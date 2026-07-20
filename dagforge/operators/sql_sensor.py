"""SQL sensor specification."""

from dagforge.operators._base import OperatorSpec, ParamSpec

OPERATOR_SPEC = OperatorSpec(
    key="sql_sensor",
    class_path="airflow.sensors.sql.SqlSensor",
    description="Waits for a SQL query to return a truthy value.",
    aliases=["SqlSensor"],
    task_specs_param=None,
    params=[
        ParamSpec(name="conn_id", required=True, description="Database connection ID"),
        ParamSpec(name="sql", required=True, description="SQL query to execute"),
        ParamSpec(name="success", description="Callable to evaluate success"),
        ParamSpec(name="failure", description="Callable to evaluate failure"),
        ParamSpec(name="fail_on_empty", description="Whether to fail if query returns no rows", type="bool"),
        ParamSpec(name="poke_interval", description="Seconds between pokes", type="int", default=60),
        ParamSpec(name="timeout", description="Seconds before the sensor times out", type="int", default=3600),
    ],
)
