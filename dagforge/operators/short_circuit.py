"""Short circuit operator specification."""

from dagforge.operators._base import OperatorSpec, ParamSpec

OPERATOR_SPEC = OperatorSpec(
    key="short_circuit",
    class_path="airflow.operators.python.ShortCircuitOperator",
    description="Skips downstream tasks when callable returns False.",
    aliases=["ShortCircuitOperator"],
    task_specs_param="python_callable",
    params=[
        ParamSpec(name="python_callable", required=True, description="Callable that returns True/False"),
        ParamSpec(name="op_args", description="Positional arguments for the callable", type="list"),
        ParamSpec(name="op_kwargs", description="Keyword arguments for the callable", type="dict"),
        ParamSpec(name="ignore_downstream_trigger_rules", description="Whether to ignore trigger rules of downstream tasks", type="bool"),
    ],
)
