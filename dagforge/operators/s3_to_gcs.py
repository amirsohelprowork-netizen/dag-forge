"""S3 to GCS transfer operator specification."""

from dagforge.operators._base import OperatorSpec, ParamSpec

OPERATOR_SPEC = OperatorSpec(
    key="s3_to_gcs",
    class_path="airflow.providers.google.cloud.transfers.s3_to_gcs.S3ToGCSOperator",
    description="Transfers data from Amazon S3 to Google Cloud Storage.",
    aliases=["S3ToGCSOperator"],
    task_specs_param=None,
    params=[
        ParamSpec(name="source_bucket", required=True, description="Source S3 bucket name"),
        ParamSpec(name="source_object", required=True, description="Source S3 object key or prefix"),
        ParamSpec(name="destination_bucket", required=True, description="Destination GCS bucket name"),
        ParamSpec(name="dest_gcs", description="Destination GCS path prefix"),
        ParamSpec(name="replace", description="Whether to replace existing objects", type="bool"),
        ParamSpec(name="gzip", description="Whether to gzip the transferred data", type="bool"),
        ParamSpec(name="aws_conn_id", description="AWS connection ID", default="aws_default"),
        ParamSpec(name="gcp_conn_id", description="GCP connection ID", default="google_cloud_default"),
    ],
)
