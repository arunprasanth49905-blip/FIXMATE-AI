import uuid
from typing import Optional
from app.schemas.parsing import SyntaxDiagnostic


class DiagnosticsFactory:
    @staticmethod
    def create(
        file_path: str,
        message: str,
        line: int,
        column: int = 0,
        severity: str = "error",
        category: str = "syntax",
        parser_name: str = "unknown",
        file_id: Optional[str] = None,
        end_line: Optional[int] = None,
        end_column: Optional[int] = None,
        error_code: Optional[str] = None,
    ) -> SyntaxDiagnostic:
        # Guarantee line is at least 1
        safe_line = max(1, line)
        safe_col = max(0, column)

        return SyntaxDiagnostic(
            id=str(uuid.uuid4()),
            file_id=file_id,
            file_path=file_path,
            severity=severity,
            category=category,
            message=message.strip(),
            line=safe_line,
            column=safe_col,
            end_line=end_line if end_line is not None else safe_line,
            end_column=end_column if end_column is not None else safe_col,
            parser_name=parser_name,
            error_code=error_code,
        )
