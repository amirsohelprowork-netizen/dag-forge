"""Empty operator specification."""

from dagforge.operators._base import OperatorSpec

OPERATOR_SPEC = OperatorSpec(
    key="empty",
    class_path="airflow.operators.empty.EmptyOperator",
    description="A no-op operator used as a placeholder or junction point in DAGs.",
    aliases=["EmptyOperator", "dummy", "DummyOperator"],
    task_specs_param=None,
    params=[],
)
