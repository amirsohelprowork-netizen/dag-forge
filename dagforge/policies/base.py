"""Base class for DAG policies."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from dagforge.core.models import DagDefinition, Severity


class PolicyViolation(BaseModel):
    """Represents a violation of an organizational policy."""
    
    rule_id: str
    severity: Severity
    message: str
    dag_id: str
    task_id: str | None = None
    field: str | None = None
    
    def __str__(self) -> str:
        loc = f"DAG '{self.dag_id}'"
        if self.task_id:
            loc += f", Task '{self.task_id}'"
        return f"[{self.severity.value.upper()}] Policy {self.rule_id} violated in {loc}: {self.message}"


class BasePolicy(ABC):
    """Abstract base class for all DAG policies."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize with optional configuration from dagforge.toml."""
        self.config = config or {}

    @abstractmethod
    def evaluate(self, dag: DagDefinition) -> list[PolicyViolation]:
        """Evaluate a DAG against this policy.
        
        Args:
            dag: The DAG to evaluate
            
        Returns:
            A list of PolicyViolations. Empty list means the DAG is compliant.
        """
        pass
