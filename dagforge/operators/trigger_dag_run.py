"""Trigger DAG run operator specification."""

from dagforge.operators._base import OperatorSpec, ParamSpec

OPERATOR_SPEC = OperatorSpec(
    key="trigger_dag_run",
    class_path="airflow.operators.trigger_dagrun.TriggerDagRunOperator",
    description="Triggers a run of another DAG.",
    aliases=["TriggerDagRunOperator", "trigger"],
    task_specs_param="trigger_dag_id",
    params=[
        ParamSpec(name="trigger_dag_id", required=True, description="The DAG ID to trigger"),
        ParamSpec(name="conf", description="Configuration dict passed to the triggered DAG", type="dict"),
        ParamSpec(name="execution_date", description="Execution date for the triggered run"),
        ParamSpec(name="reset_dag_run", description="Whether to reset the DAG run if it already exists", type="bool"),
        ParamSpec(name="wait_for_completion", description="Whether to wait for the triggered DAG to complete", type="bool"),
    ],
)
