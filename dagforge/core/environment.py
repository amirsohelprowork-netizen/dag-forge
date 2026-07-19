"""Environment manager for applying dev/staging/prod overlays."""

import logging
from typing import Any

from dagforge.core.models import DagDefinition

logger = logging.getLogger(__name__)


class EnvironmentManager:
    """Manages environment-specific overlays for DAG definitions.
    
    Overlays can modify:
    - default_args (e.g., owner, retries)
    - tags (e.g., adding 'prod' or 'dev' tags)
    - schedule (e.g., disabling schedules in dev)
    - connections/pool assignments (via default_args or operator_params)
    """

    def __init__(self, env_name: str | None, overlays: dict[str, Any] | None = None) -> None:
        self.env_name = env_name
        self.overlays = overlays or {}

    def apply(self, dag: DagDefinition) -> None:
        """Apply the environment overlay to a single DAG."""
        if not self.env_name or not self.overlays:
            return

        env_config = self.overlays.get(self.env_name)
        if not env_config:
            logger.warning("No overlay configuration found for environment: %s", self.env_name)
            return

        # 1. Add Environment Tags
        env_tags = env_config.get("tags", [])
        if env_tags:
            for tag in env_tags:
                if tag not in dag.tags:
                    dag.tags.append(tag)

        # 2. Update Default Args
        env_default_args = env_config.get("default_args", {})
        if env_default_args:
            dag.default_args.update(env_default_args)

        # 3. Apply Task Overlays (e.g., connection IDs)
        task_overlays = env_config.get("task_overrides", {})
        if task_overlays:
            for task in dag.tasks:
                # Apply global task overrides (like default pool)
                global_task_override = task_overlays.get("*", {})
                if global_task_override:
                    task.operator_params.update(global_task_override)
                
                # Apply specific task overrides by task_id
                specific_task_override = task_overlays.get(task.task_id, {})
                if specific_task_override:
                    task.operator_params.update(specific_task_override)
                    
        # 4. Schedule overrides
        if "disable_schedule" in env_config and env_config["disable_schedule"]:
            from dagforge.core.models import ScheduleConfig, ScheduleType
            dag.schedule = ScheduleConfig(type=ScheduleType.MANUAL, expression=None)
            
        logger.debug("Applied environment overlay '%s' to DAG '%s'", self.env_name, dag.dag_id)
