"""Python operator specification."""

from dagforge.operators._base import OperatorSpec, ParamSpec

OPERATOR_SPEC = OperatorSpec(
    key="python",
    class_path="airflow.operators.python.PythonOperator",
    description="Executes a Python callable.",
    aliases=["PythonOperator"],
    task_specs_param="python_callable",
    params=[
        ParamSpec(name="python_callable", required=True, description="The Python callable to execute"),
        ParamSpec(name="op_args", description="Positional arguments for the callable", type="list"),
        ParamSpec(name="op_kwargs", description="Keyword arguments for the callable", type="dict"),
        ParamSpec(name="templates_dict", description="Dictionary of templates", type="dict"),
        ParamSpec(name="templates_exts", description="List of template file extensions", type="list"),
    ],
)
