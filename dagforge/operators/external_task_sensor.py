"""External task sensor specification."""

from dagforge.operators._base import OperatorSpec, ParamSpec

OPERATOR_SPEC = OperatorSpec(
    key="external_task_sensor",
    class_path="airflow.sensors.external_task.ExternalTaskSensor",
    description="Waits for a task in another DAG to complete.",
    aliases=["ExternalTaskSensor", "sensor"],
    task_specs_param=None,
    params=[
        ParamSpec(name="external_dag_id", description="The DAG ID of the external task"),
        ParamSpec(name="external_task_id", description="The task ID to wait for"),
        ParamSpec(name="allowed_states", description="States that count as success", type="list"),
        ParamSpec(name="failed_states", description="States that count as failure", type="list"),
        ParamSpec(name="execution_delta", description="Time delta for execution date comparison"),
        ParamSpec(name="execution_date_fn", description="Function to compute execution date"),
    ],
)
