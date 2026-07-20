"""GCS to BigQuery operator specification."""

from dagforge.operators._base import OperatorSpec, ParamSpec

OPERATOR_SPEC = OperatorSpec(
    key="gcs_to_bigquery",
    class_path="airflow.providers.google.cloud.transfers.gcs_to_bigquery.GCSToBigQueryOperator",
    description="Loads data from Google Cloud Storage into BigQuery.",
    aliases=["GCSToBigQueryOperator"],
    task_specs_param=None,
    params=[
        ParamSpec(name="bucket", required=True, description="GCS bucket name"),
        ParamSpec(name="source_objects", required=True, description="List of GCS object paths", type="list"),
        ParamSpec(
            name="destination_project_dataset_table",
            required=True,
            description="Target BigQuery table in 'project.dataset.table' format",
        ),
        ParamSpec(name="source_format", description="Source file format (CSV, JSON, AVRO, etc.)"),
        ParamSpec(name="create_disposition", description="BigQuery create disposition"),
        ParamSpec(name="write_disposition", description="BigQuery write disposition"),
        ParamSpec(name="autodetect", description="Whether to auto-detect schema", type="bool"),
        ParamSpec(name="gcp_conn_id", description="GCP connection ID", default="google_cloud_default"),
    ],
)
