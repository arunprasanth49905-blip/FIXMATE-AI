from typing import List, Tuple
from app.schemas.verification import VerificationCheck, FindingsComparison
from app.services.verification.syntax_verifier import SyntaxVerificationResult


class VerificationReportBuilder:
    """
    Constructs an evidence-based verification report synthesizing all 5 verification layers:
    1. Applied Repair Integrity
    2. Syntax Verification
    3. Target Bug Resolution
    4. Regression Analysis
    5. Change Scope Validation
    """

    @classmethod
    def build_checks(
        cls,
        integrity_passed: bool,
        integrity_message: str,
        is_stale: bool,
        syntax_res: SyntaxVerificationResult,
        comparison: FindingsComparison,
        regression_status: str,
        regression_message: str,
        scope_passed: bool,
        scope_message: str,
    ) -> Tuple[List[VerificationCheck], str]:
        checks: List[VerificationCheck] = []

        # Check 1: Applied Repair Integrity
        if is_stale:
            checks.append(
                VerificationCheck(
                    name="applied_integrity",
                    status="failed",
                    message="STALE SOURCE: Disk file has been modified since the repair patch was applied.",
                    details="Current disk SHA-256 does not match post_apply_fingerprint recorded at application time.",
                )
            )
        elif not integrity_passed:
            checks.append(
                VerificationCheck(
                    name="applied_integrity",
                    status="failed",
                    message=f"Integrity Check Failed: {integrity_message}",
                )
            )
        else:
            checks.append(
                VerificationCheck(
                    name="applied_integrity",
                    status="passed",
                    message="Applied Repair Integrity Verified: Disk file matches authoritative post-apply fingerprint.",
                )
            )

        # Check 2: Syntax Verification
        if syntax_res.status == "passed":
            checks.append(
                VerificationCheck(
                    name="syntax_verification",
                    status="passed",
                    message=f"{syntax_res.language} syntax validation passed with zero parse errors.",
                )
            )
        elif syntax_res.status == "skipped":
            checks.append(
                VerificationCheck(
                    name="syntax_verification",
                    status="skipped",
                    message=syntax_res.errors[0] if syntax_res.errors else "Syntax check skipped for unsupported language.",
                )
            )
        else:
            checks.append(
                VerificationCheck(
                    name="syntax_verification",
                    status="failed",
                    message=f"Syntax Error Detected: {syntax_res.error_message or 'Invalid syntax'}",
                    details="\n".join(syntax_res.errors),
                )
            )

        # Check 3: Original Target Bug Verification
        if comparison.target_finding_status == "resolved":
            checks.append(
                VerificationCheck(
                    name="original_bug_resolution",
                    status="passed",
                    message=f"Target bug '{comparison.target_rule_id}' is RESOLVED. Deterministic rule no longer triggers on repaired code.",
                )
            )
        elif comparison.target_finding_status == "still_present":
            checks.append(
                VerificationCheck(
                    name="original_bug_resolution",
                    status="failed",
                    message=f"Target bug '{comparison.target_rule_id}' is STILL PRESENT. Re-running deterministic rule detected the bug.",
                )
            )
        else:
            checks.append(
                VerificationCheck(
                    name="original_bug_resolution",
                    status="warning",
                    message=f"Target bug status is '{comparison.target_finding_status.upper()}'. Cannot conclusively match finding.",
                )
            )

        # Check 4: Regression Analysis
        checks.append(
            VerificationCheck(
                name="regression_analysis",
                status=regression_status,
                message=regression_message,
                details=f"New: {comparison.regression_count}, Resolved: {comparison.resolved_count}, Unchanged: {len(comparison.unchanged_findings)}",
            )
        )

        # Check 5: Change Scope Validation
        checks.append(
            VerificationCheck(
                name="change_scope_validation",
                status="passed" if scope_passed else "warning",
                message=scope_message,
            )
        )

        # Determine Overall Status
        overall_status = cls._compute_overall_status(
            is_stale=is_stale,
            integrity_passed=integrity_passed,
            syntax_status=syntax_res.status,
            target_status=comparison.target_finding_status,
            regression_status=regression_status,
        )

        return checks, overall_status

    @staticmethod
    def _compute_overall_status(
        is_stale: bool,
        integrity_passed: bool,
        syntax_status: str,
        target_status: str,
        regression_status: str,
    ) -> str:
        if is_stale:
            return "stale"

        if not integrity_passed or syntax_status == "failed" or target_status == "still_present" or regression_status == "failed":
            return "failed"

        if syntax_status == "skipped" or target_status in ("inconclusive", "not_applicable"):
            return "partial"

        if target_status == "resolved" and syntax_status == "passed" and regression_status in ("passed", "warning"):
            return "verified"

        return "inconclusive"
