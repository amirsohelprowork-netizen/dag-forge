"""Branch Python operator specification."""

from dagforge.operators._base import OperatorSpec, ParamSpec

OPERATOR_SPEC = OperatorSpec(
    key="branch_python",
    class_path="airflow.operators.python.BranchPythonOperator",
    description="Branches workflow based on a Python callable's return value.",
    aliases=["BranchPythonOperator", "branch"],
    task_specs_param="python_callable",
    params=[
        ParamSpec(name="python_callable", required=True, description="Callable that returns the task_id(s) to follow"),
        ParamSpec(name="op_args", description="Positional arguments for the callable", type="list"),
        ParamSpec(name="op_kwargs", description="Keyword arguments for the callable", type="dict"),
    ],
)
