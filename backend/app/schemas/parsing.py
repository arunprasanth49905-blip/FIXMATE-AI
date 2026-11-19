from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class SourcePosition(BaseModel):
    start_line: int = Field(..., description="1-based start line")
    start_column: int = Field(0, description="0-based start column offset")
    end_line: int = Field(..., description="1-based end line")
    end_column: int = Field(0, description="0-based end column offset")


class ParameterInfo(BaseModel):
    name: str
    type: Optional[str] = None
    default_value: Optional[str] = None


class Symbol(BaseModel):
    id: str = Field(..., description="Unique symbol identifier")
    name: str
    kind: str = Field(..., description="function, async_function, method, class, interface, enum, type_alias, variable, constant")
    file_id: Optional[str] = None
    file_path: Optional[str] = None
    start_line: int
    end_line: int
    start_column: int = 0
    end_column: int = 0
    nesting_level: int = 0
    parent_symbol: Optional[str] = None
    is_async: bool = False
    is_exported: bool = False
    parameters: Optional[List[ParameterInfo]] = None
    return_type: Optional[str] = None
    visibility: Optional[str] = None  # public, private, protected
    docstring: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ImportSymbol(BaseModel):
    source_module: str
    imported_names: List[str] = Field(default_factory=list)
    alias: Optional[str] = None
    import_type: str = "standard"  # standard, from_import, default, namespace, require, type_only
    file_id: Optional[str] = None
    file_path: Optional[str] = None
    line: int
    column: int = 0
    is_type_only: bool = False


class SyntaxDiagnostic(BaseModel):
    id: str
    file_id: Optional[str] = None
    file_path: str
    severity: str = "error"  # error, warning, info
    category: str = "syntax"  # syntax, limit, parser_error, unsupported
    message: str
    line: int
    column: int = 0
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    parser_name: str
    error_code: Optional[str] = None


class FileStatistics(BaseModel):
    lines: int = 0
    functions: int = 0
    async_functions: int = 0
    classes: int = 0
    methods: int = 0
    imports: int = 0
    variables: int = 0
    constants: int = 0
    loops: int = 0
    conditions: int = 0
    calls: int = 0


class FileAnalysis(BaseModel):
    analysis_id: Optional[str] = None
    project_id: str
    file_id: Optional[str] = None
    file_path: str
    language: str
    parser: str
    status: str = "success"  # success, diagnostics, failed, skipped
    source_hash: str
    source_size: int
    analysis_timestamp: str
    statistics: FileStatistics
    symbols: List[Symbol] = Field(default_factory=list)
    imports: List[ImportSymbol] = Field(default_factory=list)
    diagnostics: List[SyntaxDiagnostic] = Field(default_factory=list)
    structure: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


class SkippedFile(BaseModel):
    file_path: str
    reason: str
    size_bytes: int = 0


class ProjectStatistics(BaseModel):
    total_files: int = 0
    supported_files: int = 0
    parsed_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    python_files: int = 0
    javascript_files: int = 0
    typescript_files: int = 0
    total_lines: int = 0
    total_functions: int = 0
    total_async_functions: int = 0
    total_classes: int = 0
    total_methods: int = 0
    total_imports: int = 0
    total_variables: int = 0
    total_loops: int = 0
    total_conditions: int = 0
    total_calls: int = 0
    total_diagnostics: int = 0
    duration_ms: float = 0.0


class ProjectAnalysisSummary(BaseModel):
    analysis_id: str
    project_id: str
    status: str  # completed, completed_with_diagnostics, failed, cancelled
    start_time: str
    end_time: str
    duration_ms: float
    statistics: ProjectStatistics
    language_distribution: Dict[str, int] = Field(default_factory=dict)
    skipped_files: List[SkippedFile] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    total_diagnostics_count: int = 0


class ProjectAnalysisResponse(ProjectAnalysisSummary):
    files: List[FileAnalysis] = Field(default_factory=list)


class ParserLimitConfig(BaseModel):
    max_file_size_bytes: int
    max_files_per_analysis: int
    max_total_source_bytes: int
    excluded_directories: List[str]


class ParserStatusResponse(BaseModel):
    available_parsers: Dict[str, str]
    supported_languages: List[str]
    supported_extensions: Dict[str, List[str]]
    parser_versions: Dict[str, str]
    limits: ParserLimitConfig
    readiness: bool
    capabilities: Dict[str, List[str]]


class ProjectParseRequest(BaseModel):
    file_ids: Optional[List[str]] = None
    file_paths: Optional[List[str]] = None
    exclude_dirs: Optional[List[str]] = None
