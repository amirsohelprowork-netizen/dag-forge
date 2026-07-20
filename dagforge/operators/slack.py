"""Slack operator specification."""

from dagforge.operators._base import OperatorSpec, ParamSpec

OPERATOR_SPEC = OperatorSpec(
    key="slack",
    class_path="airflow.providers.slack.operators.slack.SlackAPIPostOperator",
    description="Sends a message to a Slack channel.",
    aliases=["SlackAPIPostOperator", "SlackOperator"],
    task_specs_param=None,
    params=[
        ParamSpec(name="channel", required=True, description="Slack channel to post to"),
        ParamSpec(name="text", required=True, description="Message text to send"),
        ParamSpec(name="slack_conn_id", description="Slack connection ID", default="slack_default"),
        ParamSpec(name="username", description="Username to post as"),
        ParamSpec(name="icon_url", description="URL of the icon to use"),
    ],
)
