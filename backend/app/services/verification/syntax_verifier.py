import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from app.services.parsing.parser_registry import parser_registry


@dataclass
class SyntaxVerificationResult:
    is_valid: bool
    status: str  # passed, failed, skipped
    language: str
    errors: List[str] = field(default_factory=list)
    error_line: Optional[int] = None
    error_column: Optional[int] = None
    error_message: Optional[str] = None


class SyntaxVerifier:
    """
    Performs deterministic, read-only static syntax verification across supported languages.
    CRITICAL: Never executes user code under any circumstance.
    """

    @classmethod
    def verify_syntax(cls, file_path: str, source_code: str, language: str) -> SyntaxVerificationResult:
        lang_lower = (language or "").lower()

        if lang_lower == "python" or file_path.endswith((".py", ".pyw")):
            return cls._verify_python(file_path, source_code)
        elif lang_lower in ("javascript", "js") or file_path.endswith((".js", ".jsx", ".mjs", ".cjs")):
            return cls._verify_javascript(file_path, source_code)
        elif lang_lower in ("typescript", "ts") or file_path.endswith((".ts", ".tsx")):
            return cls._verify_typescript(file_path, source_code)
        else:
            return SyntaxVerificationResult(
                is_valid=True,
                status="skipped",
                language=language or "unknown",
                errors=[f"Syntax verification skipped: Language '{language}' is not supported."],
            )

    @classmethod
    def _verify_python(cls, file_path: str, source_code: str) -> SyntaxVerificationResult:
        try:
            ast.parse(source_code, filename=file_path)
            return SyntaxVerificationResult(
                is_valid=True,
                status="passed",
                language="Python",
            )
        except SyntaxError as e:
            msg = f"Python SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}"
            return SyntaxVerificationResult(
                is_valid=False,
                status="failed",
                language="Python",
                errors=[msg],
                error_line=e.lineno,
                error_column=e.offset,
                error_message=e.msg,
            )
        except Exception as e:
            return SyntaxVerificationResult(
                is_valid=False,
                status="failed",
                language="Python",
                errors=[f"Python parse failure: {str(e)}"],
                error_message=str(e),
            )

    @classmethod
    def _verify_javascript(cls, file_path: str, source_code: str) -> SyntaxVerificationResult:
        try:
            js_parser = parser_registry._parsers.get("javascript")
            if not js_parser or not hasattr(js_parser, "_parser"):
                return SyntaxVerificationResult(
                    is_valid=True,
                    status="skipped",
                    language="JavaScript",
                    errors=["JavaScript Tree-sitter parser unavailable"],
                )

            source_bytes = source_code.encode("utf-8")
            tree = js_parser._parser.parse(source_bytes)
            error_nodes = cls._find_tree_sitter_errors(tree.root_node)

            if error_nodes:
                first = error_nodes[0]
                line = first.start_point[0] + 1
                col = first.start_point[1] + 1
                msg = f"JavaScript syntax error near line {line}, column {col} ({first.type})"
                return SyntaxVerificationResult(
                    is_valid=False,
                    status="failed",
                    language="JavaScript",
                    errors=[f"Line {n.start_point[0] + 1}:{n.start_point[1] + 1}: Syntax error node '{n.type}'" for n in error_nodes],
                    error_line=line,
                    error_column=col,
                    error_message=msg,
                )

            return SyntaxVerificationResult(
                is_valid=True,
                status="passed",
                language="JavaScript",
            )
        except Exception as e:
            return SyntaxVerificationResult(
                is_valid=False,
                status="failed",
                language="JavaScript",
                errors=[f"JavaScript parse error: {str(e)}"],
                error_message=str(e),
            )

    @classmethod
    def _verify_typescript(cls, file_path: str, source_code: str) -> SyntaxVerificationResult:
        try:
            ts_parser = parser_registry._parsers.get("typescript")
            if not ts_parser or not hasattr(ts_parser, "_ts_parser"):
                return SyntaxVerificationResult(
                    is_valid=True,
                    status="skipped",
                    language="TypeScript",
                    errors=["TypeScript Tree-sitter parser unavailable"],
                )

            source_bytes = source_code.encode("utf-8")
            p = ts_parser._tsx_parser if file_path.endswith((".tsx", ".jsx")) else ts_parser._ts_parser
            tree = p.parse(source_bytes)
            error_nodes = cls._find_tree_sitter_errors(tree.root_node)

            if error_nodes:
                first = error_nodes[0]
                line = first.start_point[0] + 1
                col = first.start_point[1] + 1
                msg = f"TypeScript syntax error near line {line}, column {col} ({first.type})"
                return SyntaxVerificationResult(
                    is_valid=False,
                    status="failed",
                    language="TypeScript",
                    errors=[f"Line {n.start_point[0] + 1}:{n.start_point[1] + 1}: Syntax error node '{n.type}'" for n in error_nodes],
                    error_line=line,
                    error_column=col,
                    error_message=msg,
                )

            return SyntaxVerificationResult(
                is_valid=True,
                status="passed",
                language="TypeScript",
            )
        except Exception as e:
            return SyntaxVerificationResult(
                is_valid=False,
                status="failed",
                language="TypeScript",
                errors=[f"TypeScript parse error: {str(e)}"],
                error_message=str(e),
            )

    @classmethod
    def _find_tree_sitter_errors(cls, node) -> list:
        errors = []
        if node.type in ("ERROR", "MISSING") or node.is_missing:
            errors.append(node)
        for child in node.children:
            errors.extend(cls._find_tree_sitter_errors(child))
        return errors
