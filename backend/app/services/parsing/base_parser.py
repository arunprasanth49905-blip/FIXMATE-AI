from abc import ABC, abstractmethod
from typing import List, Optional
from app.schemas.parsing import FileAnalysis


class BaseParser(ABC):
    @property
    @abstractmethod
    def language(self) -> str:
        """Name of programming language (e.g. Python, JavaScript, TypeScript)."""
        pass

    @property
    @abstractmethod
    def parser_name(self) -> str:
        """Name of the underlying parser engine."""
        pass

    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """List of supported extensions, e.g. ['.py', '.pyw']."""
        pass

    @abstractmethod
    def parse(
        self,
        source_code: str,
        file_path: str,
        file_id: Optional[str] = None,
        project_id: str = "",
        analysis_id: Optional[str] = None,
    ) -> FileAnalysis:
        """Parses the source code string and returns a standardized FileAnalysis object."""
        pass
