"""Tests for the policy engine."""

import pytest

from dagforge.core.models import DagDefinition, ScheduleConfig, ScheduleType, TaskDefinition, OperatorType
from dagforge.policies.engine import PolicyEngine
from dagforge.policies.builtin_policies import RequireTagsPolicy, RequireDescriptionPolicy, RequireOwnerPolicy, MaxTasksPolicy, NoManualSchedulePolicy


def create_test_dag(
    tags=None, 
    description="desc", 
    owner="data-team", 
    schedule_type=ScheduleType.CRON,
    num_tasks=1
):
    tasks = [
        TaskDefinition(task_id=f"t{i}", operator=OperatorType.EMPTY)
        for i in range(num_tasks)
    ]
    return DagDefinition(
        dag_id="test_dag",
        description=description,
        schedule=ScheduleConfig(type=schedule_type, expression="0 0 * * *" if schedule_type != ScheduleType.MANUAL else None),
        default_args={"owner": owner, "start_date": "2024-01-01"},
        tags=["test"] if tags is None else tags,
        tasks=tasks
    )

def test_require_tags():
    policy = RequireTagsPolicy()
    
    # Valid
    dag1 = create_test_dag(tags=["prod"])
    assert not policy.evaluate(dag1)
    
    # Invalid
    dag2 = create_test_dag(tags=[])
    violations = policy.evaluate(dag2)
    assert len(violations) == 1
    assert violations[0].rule_id == "require_tags"

def test_require_description():
    policy = RequireDescriptionPolicy()
    
    dag1 = create_test_dag(description="Good dag")
    assert not policy.evaluate(dag1)
    
    dag2 = create_test_dag(description="")
    violations = policy.evaluate(dag2)
    assert len(violations) == 1

def test_require_owner():
    policy = RequireOwnerPolicy()
    
    dag1 = create_test_dag(owner="my-team")
    assert not policy.evaluate(dag1)
    
    dag2 = create_test_dag(owner="airflow")
    assert len(policy.evaluate(dag2)) == 1

def test_max_tasks():
    policy = MaxTasksPolicy({"max_tasks_per_dag": 5})
    
    dag1 = create_test_dag(num_tasks=5)
    assert not policy.evaluate(dag1)
    
    dag2 = create_test_dag(num_tasks=6)
    assert len(policy.evaluate(dag2)) == 1

def test_no_manual_schedule():
    policy = NoManualSchedulePolicy()
    
    dag1 = create_test_dag(schedule_type=ScheduleType.CRON)
    assert not policy.evaluate(dag1)
    
    dag2 = create_test_dag(schedule_type=ScheduleType.MANUAL)
    assert len(policy.evaluate(dag2)) == 1

def test_policy_engine():
    config = {
        "enabled": ["require_tags", "require_owner"]
    }
    engine = PolicyEngine(config)
    
    # Good dag
    dag1 = create_test_dag(tags=["t"], owner="t")
    assert not engine.evaluate([dag1])
    
    # Bad dag
    dag2 = create_test_dag(tags=[], owner="airflow")
    violations = engine.evaluate([dag2])
    assert len(violations) == 2
