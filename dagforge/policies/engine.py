"""Policy engine runner."""

import logging
from typing import Any

from dagforge.core.models import DagDefinition
from dagforge.core.registry import registry
from dagforge.policies.base import PolicyViolation

logger = logging.getLogger(__name__)


class PolicyEngine:
    """Executes registered policies against DAGs."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        
        # Load enabled policies from config, or enable all built-ins by default
        enabled = self.config.get("enabled")
        if enabled is None:
            self.enabled_policies = [
                "require_tags", 
                "require_description", 
                "require_owner", 
                "max_tasks_per_dag"
            ]
        else:
            self.enabled_policies = list(enabled)

    def evaluate(self, dags: list[DagDefinition]) -> list[PolicyViolation]:
        """Evaluate a list of DAGs against enabled policies."""
        violations: list[PolicyViolation] = []
        
        for policy_name in self.enabled_policies:
            try:
                policy_cls = registry.get_policy(policy_name)
                policy_instance = policy_cls(self.config)
            except Exception as e:
                logger.error("Failed to load policy %s: %s", policy_name, e)
                continue
                
            for dag in dags:
                try:
                    result = policy_instance.evaluate(dag)
                    if result:
                        violations.extend(result)
                except Exception as e:
                    logger.error("Policy %s failed on DAG %s: %s", policy_name, dag.dag_id, e)
                    
        return violations
