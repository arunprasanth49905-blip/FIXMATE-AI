from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import settings
from app.schemas.parsing import ParserStatusResponse, ParserLimitConfig
from app.services.parsing.base_parser import BaseParser
from app.services.parsing.python_parser import PythonParser
from app.services.parsing.javascript_parser import JavaScriptParser
from app.services.parsing.typescript_parser import TypeScriptParser


class ParserRegistry:
    def __init__(self):
        self._parsers: Dict[str, BaseParser] = {}
        self._extension_map: Dict[str, BaseParser] = {}
        self._register_default_parsers()

    def _register_default_parsers(self):
        py_parser = PythonParser()
        js_parser = JavaScriptParser()
        ts_parser = TypeScriptParser()

        self.register(py_parser)
        self.register(js_parser)
        self.register(ts_parser)

    def register(self, parser: BaseParser):
        self._parsers[parser.language.lower()] = parser
        for ext in parser.supported_extensions:
            self._extension_map[ext.lower()] = parser

    def get_parser_for_extension(self, extension: str) -> Optional[BaseParser]:
        ext = extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        return self._extension_map.get(ext)

    def get_parser_for_path(self, path: str) -> Optional[BaseParser]:
        p = Path(path)
        ext = p.suffix.lower()
        return self.get_parser_for_extension(ext)

    def is_supported_path(self, path: str) -> bool:
        return self.get_parser_for_path(path) is not None

    def get_supported_languages(self) -> List[str]:
        return [p.language for p in self._parsers.values()]

    def get_supported_extensions(self) -> Dict[str, List[str]]:
        return {p.language: p.supported_extensions for p in self._parsers.values()}

    def get_status(self) -> ParserStatusResponse:
        limits = ParserLimitConfig(
            max_file_size_bytes=settings.MAX_PARSER_FILE_SIZE_BYTES,
            max_files_per_analysis=settings.MAX_FILES_PER_ANALYSIS,
            max_total_source_bytes=settings.MAX_TOTAL_ANALYSIS_SOURCE_BYTES,
            excluded_directories=settings.PARSER_EXCLUDE_DIRS,
        )

        return ParserStatusResponse(
            available_parsers={p.language: p.parser_name for p in self._parsers.values()},
            supported_languages=self.get_supported_languages(),
            supported_extensions=self.get_supported_extensions(),
            parser_versions={
                "Python": "native-ast (Python 3.13)",
                "JavaScript": "tree-sitter-javascript 0.25.0",
                "TypeScript": "tree-sitter-typescript 0.23.2",
            },
            limits=limits,
            readiness=True,
            capabilities={
                "Python": ["classes", "functions", "async", "methods", "imports", "calls", "variables", "syntax_diagnostics", "decorators", "type_annotations"],
                "JavaScript": ["classes", "functions", "async", "methods", "imports", "require", "calls", "variables", "syntax_diagnostics", "jsx"],
                "TypeScript": ["classes", "functions", "async", "methods", "imports", "interfaces", "type_aliases", "enums", "generics", "calls", "variables", "syntax_diagnostics", "tsx"],
            },
        )


parser_registry = ParserRegistry()
