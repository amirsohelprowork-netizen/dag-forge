"""Bash operator specification."""

from dagforge.operators._base import OperatorSpec, ParamSpec

OPERATOR_SPEC = OperatorSpec(
    key="bash",
    class_path="airflow.operators.bash.BashOperator",
    description="Executes a bash command or script.",
    aliases=["BashOperator"],
    task_specs_param="bash_command",
    params=[
        ParamSpec(name="bash_command", required=True, description="The bash command to run"),
        ParamSpec(name="env", description="Environment variables dict", type="dict"),
        ParamSpec(name="append_env", description="Whether to append env vars instead of replacing", type="bool"),
        ParamSpec(name="output_encoding", description="Output encoding", default="utf-8"),
        ParamSpec(name="skip_on_exit_code", description="Exit codes that should be treated as skip", type="list"),
        ParamSpec(name="cwd", description="Working directory for the command"),
    ],
)
