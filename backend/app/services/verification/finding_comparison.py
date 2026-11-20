import re
from typing import List, Tuple, Optional, Set
from app.schemas.detection import Finding
from app.schemas.verification import FindingComparisonItem, FindingsComparison


class FindingComparator:
    """
    Compares pre-repair findings against post-repair findings to determine:
    1. Target bug resolution status (RESOLVED, STILL_PRESENT, INCONCLUSIVE, NOT_APPLICABLE).
    2. Newly introduced findings (regressions).
    3. Removed findings (fixed bugs).
    4. Unchanged findings.
    """

    @classmethod
    def compare_findings(
        cls,
        target_rule_id: str,
        target_start_line: int,
        target_end_line: int,
        original_findings: List[Finding],
        current_findings: List[Finding],
        target_evidence: Optional[str] = None,
    ) -> FindingsComparison:
        def normalize_evidence(ev: Optional[str]) -> str:
            if not ev:
                return ""
            return re.sub(r"\s+", " ", ev.strip())

        norm_target_ev = normalize_evidence(target_evidence)

        # 1. Target finding resolution check
        target_status = "resolved"

        # Check if any current finding matches the target rule and target scope/evidence
        matching_current_targets = []
        for cf in current_findings:
            if cf.rule_id == target_rule_id:
                cf_norm_ev = normalize_evidence(cf.evidence)
                # Check line proximity (+-5 lines accounting for additions/deletions) or evidence match
                lines_overlap = (
                    abs(cf.start_line - target_start_line) <= 5
                    or (cf.start_line <= target_end_line + 5 and cf.end_line >= target_start_line - 5)
                )
                evidence_matches = norm_target_ev and (norm_target_ev in cf_norm_ev or cf_norm_ev in norm_target_ev)

                if lines_overlap or evidence_matches:
                    matching_current_targets.append(cf)

        if matching_current_targets:
            target_status = "still_present"
        else:
            target_status = "resolved"

        # 2. Categorize all findings into new (regressions), removed, unchanged
        # Pair findings based on (rule_id, normalized_evidence) or (rule_id, start_line)
        orig_items = [cls._to_comparison_item(of, is_target=(of.rule_id == target_rule_id and abs(of.start_line - target_start_line) <= 3)) for of in original_findings]
        curr_items = [cls._to_comparison_item(cf, is_target=(cf.rule_id == target_rule_id and abs(cf.start_line - target_start_line) <= 5)) for cf in current_findings]

        matched_curr_indices: Set[int] = set()
        matched_orig_indices: Set[int] = set()

        # First pass: match exact rule_id + evidence
        for oi, orig in enumerate(orig_items):
            for ci, curr in enumerate(curr_items):
                if ci in matched_curr_indices:
                    continue
                if orig.rule_id == curr.rule_id and normalize_evidence(orig.evidence) == normalize_evidence(curr.evidence) and normalize_evidence(orig.evidence):
                    matched_orig_indices.add(oi)
                    matched_curr_indices.add(ci)
                    break

        # Second pass: match rule_id + close line proximity (for unchanged non-target findings)
        for oi, orig in enumerate(orig_items):
            if oi in matched_orig_indices:
                continue
            for ci, curr in enumerate(curr_items):
                if ci in matched_curr_indices:
                    continue
                if orig.rule_id == curr.rule_id and abs(orig.start_line - curr.start_line) <= 3:
                    matched_orig_indices.add(oi)
                    matched_curr_indices.add(ci)
                    break

        unchanged_findings = [curr_items[ci] for ci in sorted(matched_curr_indices)]
        removed_findings = [orig_items[oi] for oi in range(len(orig_items)) if oi not in matched_orig_indices]
        new_findings = [curr_items[ci] for ci in range(len(curr_items)) if ci not in matched_curr_indices]

        return FindingsComparison(
            target_rule_id=target_rule_id,
            target_finding_status=target_status,
            before_count=len(orig_items),
            after_count=len(curr_items),
            resolved_count=len(removed_findings),
            regression_count=len(new_findings),
            new_findings=new_findings,
            removed_findings=removed_findings,
            unchanged_findings=unchanged_findings,
        )

    @staticmethod
    def _to_comparison_item(f: Finding, is_target: bool = False) -> FindingComparisonItem:
        return FindingComparisonItem(
            id=getattr(f, "id", None),
            rule_id=f.rule_id,
            rule_name=f.rule_name,
            severity=f.severity,
            category=getattr(f, "category", "correctness"),
            file_path=f.file_path,
            start_line=f.start_line,
            start_column=getattr(f, "start_column", 1),
            end_line=f.end_line,
            end_column=getattr(f, "end_column", 1),
            message=f.message,
            evidence=f.evidence or "",
            is_target=is_target,
        )
