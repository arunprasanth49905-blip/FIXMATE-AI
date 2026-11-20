from typing import List, Tuple
from app.schemas.verification import FindingComparisonItem


class RegressionVerifier:
    """
    Evaluates new findings introduced in the repaired code and classifies their regression severity.
    """

    @classmethod
    def evaluate_regressions(cls, new_findings: List[FindingComparisonItem]) -> Tuple[str, str]:
        """
        Returns (status, summary_message) where status is:
        - "passed": 0 new findings
        - "warning": new medium or low/info findings
        - "failed": new critical or high findings introduced
        """
        if not new_findings:
            return "passed", "Zero new findings detected. No regressions introduced."

        critical_high = [f for f in new_findings if (f.severity or "").lower() in ("critical", "high")]
        medium_low = [f for f in new_findings if (f.severity or "").lower() in ("medium", "low", "info")]

        if critical_high:
            rules_str = ", ".join(f"{f.rule_id} (line {f.start_line})" for f in critical_high[:3])
            msg = f"CRITICAL REGRESSION: Repair introduced {len(critical_high)} high-severity finding(s): {rules_str}."
            return "failed", msg

        if medium_low:
            rules_str = ", ".join(f"{f.rule_id} (line {f.start_line})" for f in medium_low[:3])
            msg = f"Regression Warning: Repair introduced {len(medium_low)} warning finding(s): {rules_str}."
            return "warning", msg

        return "passed", "No regressions detected."
