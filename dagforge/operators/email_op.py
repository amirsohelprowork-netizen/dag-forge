"""Email operator specification."""

from dagforge.operators._base import OperatorSpec, ParamSpec

OPERATOR_SPEC = OperatorSpec(
    key="email",
    class_path="airflow.operators.email.EmailOperator",
    description="Sends an email.",
    aliases=["EmailOperator"],
    task_specs_param=None,
    params=[
        ParamSpec(name="to", required=True, description="Recipient email address(es)", type="any"),
        ParamSpec(name="subject", required=True, description="Email subject line"),
        ParamSpec(name="html_content", required=True, description="HTML body of the email"),
        ParamSpec(name="cc", description="CC recipients", type="any"),
        ParamSpec(name="bcc", description="BCC recipients", type="any"),
        ParamSpec(name="mime_subtype", description="MIME subtype", default="mixed"),
        ParamSpec(name="mime_charset", description="MIME charset", default="utf-8"),
        ParamSpec(name="files", description="List of file paths to attach", type="list"),
    ],
)
