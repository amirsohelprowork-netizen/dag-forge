"""Docker operator specification."""

from dagforge.operators._base import OperatorSpec, ParamSpec

OPERATOR_SPEC = OperatorSpec(
    key="docker",
    class_path="airflow.providers.docker.operators.docker.DockerOperator",
    description="Runs a command inside a Docker container.",
    aliases=["DockerOperator"],
    task_specs_param="image",
    params=[
        ParamSpec(name="image", required=True, description="Docker image to run"),
        ParamSpec(name="api_version", description="Docker API version"),
        ParamSpec(name="container_name", description="Name of the container"),
        ParamSpec(name="cpus", description="Number of CPUs for the container", type="float"),
        ParamSpec(name="docker_url", description="Docker daemon URL", default="unix://var/run/docker.sock"),
        ParamSpec(name="environment", description="Environment variables dict", type="dict"),
        ParamSpec(name="force_pull", description="Whether to force-pull the image", type="bool"),
        ParamSpec(name="mem_limit", description="Memory limit for the container"),
    ],
)
