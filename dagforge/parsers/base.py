"""Abstract base class for input parsers.

All parsers must implement the `parse` method, which takes a file path
and returns a ParseResult containing one or more DagDefinitions.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from dagforge.core.models import ParseResult


logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Abstract base class for all input parsers.

    Subclasses must implement:
        - parse(source): Parse a file and return a ParseResult
        - supported_extensions: Property returning supported file extensions

    Example:
        @registry.parser("csv")
        class CsvParser(BaseParser):
            @property
            def supported_extensions(self) -> set[str]:
                return {".csv"}

            def parse(self, source: Path) -> ParseResult:
                ...
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> set[str]:
        """Return the set of file extensions this parser handles (e.g., {'.xlsx'})."""
        ...

    @abstractmethod
    def parse(self, source: Path) -> ParseResult:
        """Parse an input file and return structured DAG definitions.

        Args:
            source: Path to the input file.

        Returns:
            ParseResult containing parsed DagDefinitions and any warnings.

        Raises:
            ParseError: If the file cannot be parsed.
        """
        ...

    def can_handle(self, source: Path) -> bool:
        """Check if this parser can handle the given file."""
        return source.suffix.lower() in self.supported_extensions
