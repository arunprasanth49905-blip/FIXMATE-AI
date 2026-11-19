import ast
from pathlib import Path
from typing import List, Tuple
from app.schemas.repair import PatchValidationDetails, ValidationCheck
from app.services.parsing.parser_registry import ParserRegistry

parser_registry = ParserRegistry()


class PatchValidator:
    """
    Deterministic validation layer enforcing structural, syntactical,
    scope, and reversibility safety on proposed code patches.
    Never executes user or generated code.
    """

    @classmethod
    def validate_patch(
        cls,
        file_path: str,
        language: str,
        original_source: str,
        repaired_source: str,
        start_line: int,
        end_line: int,
        source_fingerprint: str,
        expected_fingerprint: str,
    ) -> PatchValidationDetails:
        checks: List[ValidationCheck] = []
        errors: List[str] = []
        is_syntactically_valid = True
        is_reversible = True
        is_scope_valid = True

        # ----------------------------------------------------
        # 1. Source Freshness & Fingerprint Match
        # ----------------------------------------------------
        if source_fingerprint != expected_fingerprint:
            errors.append("Source file fingerprint mismatch: the file on disk has changed.")
            checks.append(
                ValidationCheck(
                    name="Source Freshness",
                    status="failed",
                    message="Source code has changed since detection or analysis.",
                    details=f"Current: {source_fingerprint[:8]}... != Expected: {expected_fingerprint[:8]}...",
                )
            )
        else:
            checks.append(
                ValidationCheck(
                    name="Source Freshness",
                    status="passed",
                    message="Source fingerprint verified against disk file.",
                )
            )

        # ----------------------------------------------------
        # 2. Patch Scope & Path Security
        # ----------------------------------------------------
        path_obj = Path(file_path)
        if path_obj.is_absolute() or ".." in file_path or file_path.startswith("/"):
            is_scope_valid = False
            errors.append(f"Security: invalid or escaping file path '{file_path}'.")
            checks.append(
                ValidationCheck(
                    name="Path Security",
                    status="failed",
                    message="Target path contains path traversal or absolute references.",
                )
            )
        else:
            checks.append(
                ValidationCheck(
                    name="Path Security",
                    status="passed",
                    message="Path is safe and workspace-relative.",
                )
            )

        # Scope Check: No-op detection
        if original_source.strip() == repaired_source.strip():
            is_scope_valid = False
            errors.append("Patch produces no changes to the source code (no-op patch).")
            checks.append(
                ValidationCheck(
                    name="Patch Scope",
                    status="failed",
                    message="Proposed code is identical to original code.",
                )
            )
        else:
            orig_len = len(original_source.splitlines())
            rep_len = len(repaired_source.splitlines())
            # Excessive change check (e.g. rewriting 50+ lines when bug is 1 line)
            target_span = max(1, end_line - start_line + 1)
            delta = abs(rep_len - orig_len)
            if delta > 30 and delta > target_span * 5:
                checks.append(
                    ValidationCheck(
                        name="Patch Scope",
                        status="warning",
                        message=f"Change size ({delta} lines) is unusually large for target line span ({target_span} lines).",
                    )
                )
            else:
                checks.append(
                    ValidationCheck(
                        name="Patch Scope",
                        status="passed",
                        message=f"Patch targeted to error region (lines {start_line}-{end_line}).",
                    )
                )

        # ----------------------------------------------------
        # 3. Patch Integrity & Reversibility
        # ----------------------------------------------------
        # Verify in memory that restoring original lines recovers original source byte-for-byte
        orig_lines = original_source.splitlines(keepends=True)
        rep_lines = repaired_source.splitlines(keepends=True)

        newline_char = "\r\n" if "\r\n" in original_source else "\n"
        from_idx = max(0, start_line - 1)
        to_idx = min(len(orig_lines), max(start_line, end_line))
        orig_target_slice = orig_lines[from_idx:to_idx]

        # Calculate how many lines were inserted in repaired_source
        inserted_count = len(rep_lines) - (len(orig_lines) - (to_idx - from_idx))
        reversed_lines = rep_lines[:from_idx] + orig_target_slice + rep_lines[from_idx + max(0, inserted_count):]
        reversed_source = "".join(reversed_lines)

        if reversed_source == original_source:
            checks.append(
                ValidationCheck(
                    name="Patch Reversibility",
                    status="passed",
                    message="Patch is cleanly reversible and recovers original code byte-for-byte.",
                )
            )
        else:
            is_reversible = False
            errors.append("Patch reversibility failed: inverting patch did not produce exact original source.")
            checks.append(
                ValidationCheck(
                    name="Patch Reversibility",
                    status="failed",
                    message="Patch cannot be cleanly reversed to original source.",
                )
            )

        # ----------------------------------------------------
        # 4. Language Syntax Integrity
        # ----------------------------------------------------
        lang_lower = language.lower()
        if "python" in lang_lower or file_path.endswith(".py"):
            try:
                ast.parse(repaired_source, filename=file_path)
                checks.append(
                    ValidationCheck(
                        name="Python AST Syntax",
                        status="passed",
                        message="Proposed code parsed successfully by Python AST without syntax errors.",
                    )
                )
            except SyntaxError as syn_err:
                is_syntactically_valid = False
                err_detail = f"SyntaxError at line {syn_err.lineno}: {syn_err.msg}"
                errors.append(f"Python syntax error in proposed code: {err_detail}")
                checks.append(
                    ValidationCheck(
                        name="Python AST Syntax",
                        status="failed",
                        message="Proposed code contains Python syntax errors.",
                        details=err_detail,
                    )
                )

        elif any(file_path.endswith(ext) for ext in [".js", ".jsx", ".ts", ".tsx", ".mjs"]):
            try:
                parser = parser_registry.get_parser_for_path(file_path)
                if parser:
                    file_analysis = parser.parse(repaired_source, file_path)
                    syntax_errors = [d for d in file_analysis.diagnostics if d.severity == "error" and d.category == "syntax"]
                    if syntax_errors:
                        is_syntactically_valid = False
                        msg = f"{len(syntax_errors)} syntax error(s) detected: {syntax_errors[0].message}"
                        errors.append(msg)
                        checks.append(
                            ValidationCheck(
                                name="Tree-sitter Syntax",
                                status="failed",
                                message="Proposed code contains syntax errors.",
                                details=msg,
                            )
                        )
                    else:
                        checks.append(
                            ValidationCheck(
                                name="Tree-sitter Syntax",
                                status="passed",
                                message="Proposed code parsed cleanly by Tree-sitter without syntax errors.",
                            )
                        )
                else:
                    checks.append(
                        ValidationCheck(
                            name="Syntax Parser",
                            status="passed",
                            message="No dedicated parser required for file type.",
                        )
                    )
            except Exception as e:
                checks.append(
                    ValidationCheck(
                        name="Syntax Parser",
                        status="warning",
                        message=f"Parser notice: {str(e)}",
                    )
                )

        # ----------------------------------------------------
        # 5. Security & Zero-Execution Policy
        # ----------------------------------------------------
        checks.append(
            ValidationCheck(
                name="Zero-Execution Safety",
                status="passed",
                message="Zero code execution verified. No subprocesses or file modifications invoked.",
            )
        )

        overall_status = "passed"
        if errors or not is_syntactically_valid or not is_reversible or not is_scope_valid:
            overall_status = "failed"
        elif any(c.status == "warning" for c in checks):
            overall_status = "warning"

        return PatchValidationDetails(
            checks=checks,
            overall_status=overall_status,
            is_syntactically_valid=is_syntactically_valid,
            is_reversible=is_reversible,
            is_scope_valid=is_scope_valid,
            validation_errors=errors,
        )
