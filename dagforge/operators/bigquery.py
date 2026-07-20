"""BigQuery operator specification."""

from dagforge.operators._base import OperatorSpec, ParamSpec

OPERATOR_SPEC = OperatorSpec(
    key="bigquery",
    class_path="airflow.providers.google.cloud.operators.bigquery.BigQueryInsertJobOperator",
    description="Executes a BigQuery job (query, load, copy, or extract).",
    aliases=["BigQueryInsertJobOperator", "BigQueryOperator"],
    task_specs_param=None,
    params=[
        ParamSpec(
            name="configuration",
            required=True,
            type="dict",
            description="BigQuery job configuration (query, load, copy, or extract)",
            nested={
                "query": ParamSpec(
                    name="query",
                    type="dict",
                    description="Query job configuration",
                    nested={
                        "query": ParamSpec(name="query", description="The SQL query string"),
                        "useLegacySql": ParamSpec(name="useLegacySql", type="bool", description="Use legacy SQL"),
                        "destinationTable": ParamSpec(name="destinationTable", type="dict", description="Destination table reference"),
                    },
                ),
                "load": ParamSpec(
                    name="load",
                    type="dict",
                    description="Load job configuration",
                    nested={
                        "sourceUris": ParamSpec(name="sourceUris", type="list", description="Source URIs"),
                        "destinationTable": ParamSpec(name="destinationTable", type="dict", description="Destination table reference"),
                        "sourceFormat": ParamSpec(name="sourceFormat", description="Source file format"),
                    },
                ),
                "copy": ParamSpec(name="copy", type="dict", description="Copy job configuration"),
                "extract": ParamSpec(name="extract", type="dict", description="Extract job configuration"),
            },
        ),
        ParamSpec(name="gcp_conn_id", description="GCP connection ID", default="google_cloud_default"),
        ParamSpec(name="location", description="BigQuery location / region"),
        ParamSpec(name="job_id", description="Custom job ID"),
    ],
)
