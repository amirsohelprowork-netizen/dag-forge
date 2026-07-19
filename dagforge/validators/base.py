"""Abstract base class for validators.

Validators examine DagDefinitions for semantic correctness beyond
what Pydantic schema validation catches.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from dagforge.core.models import DagDefinition, ValidationResult


logger = logging.getLogger(__name__)


class BaseValidator(ABC):
    """Abstract base class for all validators.

    Subclasses must implement:
        - validate(dag): Check a single DagDefinition and return issues

    Validators should NOT raise exceptions for validation failures.
    Instead, they return ValidationResult with appropriate severity levels.
    Only raise exceptions for internal validator errors.

    Example:
        @registry.validator("custom_policy")
        class CustomPolicyValidator(BaseValidator):
            def validate(self, dag: DagDefinition) -> ValidationResult:
                ...
    """

    @abstractmethod
    def validate(self, dag: DagDefinition) -> ValidationResult:
        """Validate a single DAG definition.

        Args:
            dag: The DagDefinition to validate.

        Returns:
            ValidationResult containing any issues found.
        """
        ...

    def validate_batch(self, dags: list[DagDefinition]) -> ValidationResult:
        """Validate multiple DAGs, merging results.

        Can be overridden for cross-DAG validation (e.g., unique DAG IDs).

        Args:
            dags: List of DagDefinitions to validate.

        Returns:
            Merged ValidationResult from all DAGs.
        """
        result = ValidationResult()
        for dag in dags:
            dag_result = self.validate(dag)
            result = result.merge(dag_result)
        return result
