"""Built-in organizational policies for DAG Forge."""

from dagforge.core.models import DagDefinition, ScheduleType, Severity
from dagforge.core.registry import registry
from dagforge.policies.base import BasePolicy, PolicyViolation


@registry.policy("require_tags")
class RequireTagsPolicy(BasePolicy):
    def evaluate(self, dag: DagDefinition) -> list[PolicyViolation]:
        if not dag.tags or len(dag.tags) == 0:
            return [
                PolicyViolation(
                    rule_id="require_tags",
                    severity=Severity.ERROR,
                    message="DAG must have at least one tag.",
                    dag_id=dag.dag_id,
                )
            ]
        return []


@registry.policy("require_description")
class RequireDescriptionPolicy(BasePolicy):
    def evaluate(self, dag: DagDefinition) -> list[PolicyViolation]:
        if not dag.description:
            return [
                PolicyViolation(
                    rule_id="require_description",
                    severity=Severity.WARNING,
                    message="DAG should have a description.",
                    dag_id=dag.dag_id,
                )
            ]
        return []


@registry.policy("require_owner")
class RequireOwnerPolicy(BasePolicy):
    def evaluate(self, dag: DagDefinition) -> list[PolicyViolation]:
        owner = dag.default_args.get("owner")
        if not owner or owner == "airflow":
            return [
                PolicyViolation(
                    rule_id="require_owner",
                    severity=Severity.ERROR,
                    message="DAG must define an owner other than 'airflow' in default_args.",
                    dag_id=dag.dag_id,
                )
            ]
        return []


@registry.policy("max_tasks_per_dag")
class MaxTasksPolicy(BasePolicy):
    def evaluate(self, dag: DagDefinition) -> list[PolicyViolation]:
        max_tasks = int(self.config.get("max_tasks_per_dag", 50))
        if len(dag.tasks) > max_tasks:
            return [
                PolicyViolation(
                    rule_id="max_tasks_per_dag",
                    severity=Severity.WARNING,
                    message=f"DAG has {len(dag.tasks)} tasks, exceeding the recommended limit of {max_tasks}.",
                    dag_id=dag.dag_id,
                )
            ]
        return []


@registry.policy("no_manual_schedule")
class NoManualSchedulePolicy(BasePolicy):
    def evaluate(self, dag: DagDefinition) -> list[PolicyViolation]:
        if dag.schedule.type == ScheduleType.MANUAL:
            return [
                PolicyViolation(
                    rule_id="no_manual_schedule",
                    severity=Severity.WARNING,
                    message="DAG uses a manual schedule. Prod DAGs should usually be automated.",
                    dag_id=dag.dag_id,
                )
            ]
        return []
