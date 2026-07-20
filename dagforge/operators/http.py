"""HTTP operator specification."""

from dagforge.operators._base import OperatorSpec, ParamSpec

OPERATOR_SPEC = OperatorSpec(
    key="http",
    class_path="airflow.providers.http.operators.http.SimpleHttpOperator",
    description="Executes an HTTP request.",
    aliases=["SimpleHttpOperator", "HttpOperator"],
    task_specs_param="endpoint",
    params=[
        ParamSpec(name="endpoint", required=True, description="The relative URL endpoint to call"),
        ParamSpec(name="method", description="HTTP method (GET, POST, etc.)", default="POST"),
        ParamSpec(name="data", description="Request body data", type="any"),
        ParamSpec(name="headers", description="HTTP headers dict", type="dict"),
        ParamSpec(name="response_check", description="Callable to validate the response"),
        ParamSpec(name="response_filter", description="Callable to filter the response"),
        ParamSpec(name="extra_options", description="Extra options dict for the request", type="dict"),
        ParamSpec(name="http_conn_id", description="Airflow connection ID for HTTP", default="http_default"),
    ],
)
