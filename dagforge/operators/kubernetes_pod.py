"""Kubernetes Pod operator specification."""

from dagforge.operators._base import OperatorSpec, ParamSpec

OPERATOR_SPEC = OperatorSpec(
    key="kubernetes_pod",
    class_path="airflow.providers.cncf.kubernetes.operators.pod.KubernetesPodOperator",
    description="Launches a Kubernetes Pod to run a container.",
    aliases=["KubernetesPodOperator", "K8sPodOperator"],
    task_specs_param="image",
    params=[
        ParamSpec(name="name", required=True, description="Name of the Pod"),
        ParamSpec(name="namespace", required=True, description="Kubernetes namespace"),
        ParamSpec(name="image", required=True, description="Container image to run"),
        ParamSpec(name="cmds", description="Entrypoint command list", type="list"),
        ParamSpec(name="arguments", description="Arguments to the entrypoint", type="list"),
        ParamSpec(name="ports", description="List of container ports", type="list"),
        ParamSpec(
            name="volume_mounts",
            description="Volume mount configurations",
            type="list",
        ),
        ParamSpec(
            name="volumes",
            description="Volume configurations",
            type="list",
        ),
        ParamSpec(name="env_vars", description="Environment variables", type="dict"),
        ParamSpec(
            name="secrets",
            description="Kubernetes secrets to mount",
            type="list",
        ),
        ParamSpec(name="in_cluster", description="Whether running inside a K8s cluster", type="bool"),
        ParamSpec(name="cluster_context", description="Kubernetes cluster context name"),
    ],
)
