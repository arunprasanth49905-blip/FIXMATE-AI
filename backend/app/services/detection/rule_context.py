from typing import List, Optional, Any
from app.schemas.parsing import FileAnalysis


class RuleContext:
    """Encapsulates file content, syntax trees, lines, and Phase 3 structural analysis.
    
    Rules inspect this context deterministically without re-reading from disk or re-parsing unnecessarily.
    """

    def __init__(
        self,
        file_path: str,
        language: str,
        source_code: str,
        ast_tree: Optional[Any] = None,
        tree_sitter_node: Optional[Any] = None,
        file_analysis: Optional[FileAnalysis] = None,
    ):
        self.file_path = file_path
        self.language = language
        self.source_code = source_code
        self.source_lines = source_code.splitlines()
        self.ast_tree = ast_tree
        self.tree_sitter_node = tree_sitter_node
        self.file_analysis = file_analysis

    def get_line_content(self, line_number: int) -> str:
        """Returns the 1-indexed line content, or empty string if out of bounds."""
        if 1 <= line_number <= len(self.source_lines):
            return self.source_lines[line_number - 1]
        return ""

    def extract_evidence(self, start_line: int, end_line: int, max_lines: int = 5) -> str:
        """Extracts and trims evidence lines surrounding the target finding."""
        if not self.source_lines:
            return ""
        
        start_idx = max(0, start_line - 1)
        end_idx = min(len(self.source_lines), end_line)

        # Enforce max lines for clean evidence display
        if (end_idx - start_idx) > max_lines:
            end_idx = start_idx + max_lines
            truncated = True
        else:
            truncated = False

        evidence_lines = self.source_lines[start_idx:end_idx]
        evidence_str = "\n".join(evidence_lines)
        if truncated:
            evidence_str += "\n... (truncated)"
        return evidence_str
