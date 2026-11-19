import difflib
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class PatchArtifact:
    repaired_source: str
    diff: str
    additions: int
    deletions: int
    target_start_line: int
    target_end_line: int


class PatchGenerator:
    """
    Deterministically constructs the in-memory proposed source and standard unified diff
    by replacing the exact target line range.
    NEVER writes or modifies files on disk.
    """

    @classmethod
    def generate_patch(
        cls,
        full_source_raw: str,
        start_line: int,
        end_line: int,
        proposed_code: str,
        file_path: str,
    ) -> PatchArtifact:
        # Normalize newlines
        original_lines = full_source_raw.splitlines(keepends=True)
        total_lines = len(original_lines)

        # Handle edge cases (empty file or start_line out of bounds)
        from_idx = max(0, start_line - 1)
        to_idx = min(total_lines, max(start_line, end_line))

        # Format proposed code lines with matching newline convention
        newline_char = "\r\n" if "\r\n" in full_source_raw else "\n"
        proposed_clean = proposed_code.strip("\r\n")

        # Detect original target line indentation
        target_indent = ""
        if from_idx < total_lines:
            first_orig_line = original_lines[from_idx]
            target_indent = first_orig_line[: len(first_orig_line) - len(first_orig_line.lstrip())]

        formatted_proposed_lines = []
        for line in proposed_clean.splitlines():
            # If original line was indented but proposed line lacks indentation, apply target indentation
            if target_indent and not line.startswith(" ") and not line.startswith("\t"):
                formatted_proposed_lines.append(target_indent + line + newline_char)
            else:
                formatted_proposed_lines.append(line + newline_char)

        if not formatted_proposed_lines and proposed_clean:
            formatted_proposed_lines = [(target_indent if not proposed_clean.startswith(" ") else "") + proposed_clean + newline_char]

        # Construct repaired lines in memory
        before_slice = original_lines[:from_idx]
        after_slice = original_lines[to_idx:]
        repaired_lines = before_slice + formatted_proposed_lines + after_slice
        repaired_source = "".join(repaired_lines)

        # Generate standard unified diff
        diff_generator = difflib.unified_diff(
            original_lines,
            repaired_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=newline_char,
        )
        diff_lines = list(diff_generator)
        diff_text = "".join(diff_lines)

        # Compute additions and deletions (excluding diff header lines)
        additions = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
        deletions = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))

        return PatchArtifact(
            repaired_source=repaired_source,
            diff=diff_text,
            additions=additions,
            deletions=deletions,
            target_start_line=start_line,
            target_end_line=end_line,
        )
