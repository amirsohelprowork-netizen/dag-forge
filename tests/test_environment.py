"""Tests for environment manager."""

import pytest
from dagforge.core.environment import EnvironmentManager
from dagforge.core.models import DagDefinition, ScheduleConfig, ScheduleType, TaskDefinition, OperatorType

def test_environment_manager():
    overlays = {
        "prod": {
            "tags": ["production"],
            "default_args": {"owner": "prod-team", "retries": 5},
            "task_overrides": {
                "*": {"pool": "default_pool"},
                "task1": {"pool": "high_priority"}
            }
        },
        "dev": {
            "tags": ["development"],
            "disable_schedule": True
        }
    }
    
    # Test prod overlay
    dag1 = DagDefinition(
        dag_id="test",
        tags=["etl"],
        default_args={"owner": "airflow"},
        tasks=[
            TaskDefinition(task_id="task1", operator=OperatorType.EMPTY),
            TaskDefinition(task_id="task2", operator=OperatorType.EMPTY)
        ]
    )
    
    prod_env = EnvironmentManager("prod", overlays)
    prod_env.apply(dag1)
    
    assert "production" in dag1.tags
    assert "etl" in dag1.tags
    assert dag1.default_args["owner"] == "prod-team"
    assert dag1.default_args["retries"] == 5
    
    tasks = {t.task_id: t for t in dag1.tasks}
    assert tasks["task1"].operator_params["pool"] == "high_priority"
    assert tasks["task2"].operator_params["pool"] == "default_pool"
    
    # Test dev overlay
    dag2 = DagDefinition(
        dag_id="test2",
        schedule=ScheduleConfig(type=ScheduleType.CRON, expression="0 0 * * *")
    )
    
    dev_env = EnvironmentManager("dev", overlays)
    dev_env.apply(dag2)
    
    assert "development" in dag2.tags
    assert dag2.schedule.type == ScheduleType.MANUAL
    assert dag2.schedule.expression is None
