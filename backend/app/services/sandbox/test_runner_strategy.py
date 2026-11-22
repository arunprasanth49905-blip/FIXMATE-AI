import re
from typing import Dict, Any, Tuple
from app.schemas.sandbox import TestSummarySchema


class TestRunnerStrategy:
    @staticmethod
    def get_test_command(language: str, test_file_name: str, test_case: str | None = None) -> Tuple[list[str], str]:
        """
        Returns the command to execute inside the container, along with the framework name.
        """
        lang = language.strip().lower()
        if lang == "python":
            cmd = ["python", "-m", "pytest", "-v", "--no-header", test_file_name]
            if test_case:
                cmd.extend(["-k", test_case])
            return cmd, "pytest"

        elif lang in ("javascript", "typescript"):
            # Using Node.js built-in native test runner (node:test) available in Node 18+
            cmd = ["node", "--test", test_file_name]
            if test_case:
                cmd.extend(["--test-name-pattern", test_case])
            return cmd, "node:test"

        else:
            raise ValueError(f"Unsupported language for test execution: {language}")

    @staticmethod
    def parse_test_results(language: str, stdout: str, stderr: str, exit_code: int) -> Tuple[str, TestSummarySchema]:
        """
        Parses test output and returns (overall_status, TestSummarySchema).
        Possible statuses: PASSED, FAILED, ERROR, DEPENDENCIES_UNAVAILABLE, UNSUPPORTED_TEST_FRAMEWORK
        """
        lang = language.strip().lower()
        combined = f"{stdout}\n{stderr}"

        # 1. Dependency checks
        if "No module named pytest" in combined or "ModuleNotFoundError: No module named 'pytest'" in combined:
            return "DEPENDENCIES_UNAVAILABLE", TestSummarySchema(
                total=0,
                passed=0,
                failed=0,
                errors=1,
                skipped=0,
                framework="pytest",
                details="pytest test framework is not installed in the sandbox container image.",
            )

        if "command not found" in combined.lower() or "not recognized as an internal or external command" in combined.lower():
            return "UNSUPPORTED_TEST_FRAMEWORK", TestSummarySchema(
                total=0,
                passed=0,
                failed=0,
                errors=1,
                skipped=0,
                framework="unknown",
                details="Configured test runner binary was not found in container.",
            )

        if lang == "python":
            return TestRunnerStrategy._parse_pytest(stdout, stderr, exit_code)
        elif lang in ("javascript", "typescript"):
            return TestRunnerStrategy._parse_node_test(stdout, stderr, exit_code)
        else:
            return "UNSUPPORTED", TestSummarySchema(framework="unsupported", details=f"Unsupported test language {language}")

    @staticmethod
    def _parse_pytest(stdout: str, stderr: str, exit_code: int) -> Tuple[str, TestSummarySchema]:
        # Pytest summary line example:
        # "=== 2 passed, 1 failed, 1 error, 1 skipped in 0.25s ==="
        combined = f"{stdout}\n{stderr}"

        passed = 0
        failed = 0
        errors = 0
        skipped = 0

        # Regex for summary matches
        p_match = re.search(r"(\d+)\s+passed", combined)
        f_match = re.search(r"(\d+)\s+failed", combined)
        e_match = re.search(r"(\d+)\s+error", combined)
        s_match = re.search(r"(\d+)\s+skipped", combined)

        if p_match:
            passed = int(p_match.group(1))
        if f_match:
            failed = int(f_match.group(1))
        if e_match:
            errors = int(e_match.group(1))
        if s_match:
            skipped = int(s_match.group(1))

        total = passed + failed + errors + skipped

        # Pytest exit codes:
        # 0: all tests passed
        # 1: tests were run and some failed
        # 2: test execution was interrupted by user
        # 3: internal error happened
        # 4: pytest command line usage error
        # 5: no tests were collected
        if exit_code == 0:
            status = "PASSED"
        elif exit_code == 1:
            status = "FAILED"
        elif exit_code == 5:
            status = "FAILED"
            errors = max(1, errors)
        else:
            status = "ERROR"

        summary = TestSummarySchema(
            total=total,
            passed=passed,
            failed=failed,
            errors=errors,
            skipped=skipped,
            framework="pytest",
            details=f"pytest exit code {exit_code}",
        )
        return status, summary

    @staticmethod
    def _parse_node_test(stdout: str, stderr: str, exit_code: int) -> Tuple[str, TestSummarySchema]:
        combined = f"{stdout}\n{stderr}"

        total = 0
        passed = 0
        failed = 0
        cancelled = 0

        # Node test runner summary:
        # ℹ tests 3
        # ℹ pass 2
        # ℹ fail 1
        # ℹ cancelled 0
        t_match = re.search(r"ℹ\s+tests\s+(\d+)", combined)
        p_match = re.search(r"ℹ\s+pass\s+(\d+)", combined)
        f_match = re.search(r"ℹ\s+fail\s+(\d+)", combined)
        c_match = re.search(r"ℹ\s+cancelled\s+(\d+)", combined)

        if t_match:
            total = int(t_match.group(1))
        if p_match:
            passed = int(p_match.group(1))
        if f_match:
            failed = int(f_match.group(1))
        if c_match:
            cancelled = int(c_match.group(1))

        if total == 0:
            # Fallback counting checkmarks
            passed = len(re.findall(r"✔", combined))
            failed = len(re.findall(r"✖", combined))
            total = passed + failed

        if exit_code == 0:
            status = "PASSED"
        elif failed > 0 or exit_code == 1:
            status = "FAILED"
        else:
            status = "ERROR"

        summary = TestSummarySchema(
            total=total,
            passed=passed,
            failed=failed,
            errors=cancelled,
            skipped=0,
            framework="node:test",
            details=f"node:test exit code {exit_code}",
        )
        return status, summary


test_runner_strategy = TestRunnerStrategy()
