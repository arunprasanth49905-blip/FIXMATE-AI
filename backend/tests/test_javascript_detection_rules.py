import pytest
from app.schemas.detection import FindingSeverity
from app.services.detection.rule_context import RuleContext
from app.services.detection.rules.javascript_rules import (
    SuspiciousEqualityRule,
    EmptyCatchBlockRule,
    UnreachableCodeJSRule,
    DuplicateObjectKeyRule,
    ConstantConditionJSRule,
    DangerousEvalRule,
    AssignmentInConditionRule,
    UnusedImportJSRule,
    NullDereferenceRule,
    UnawaitedAsyncCallRule,
)
from app.services.parsing.parser_registry import parser_registry


def evaluate_js_code(rule, code: str, file_path: str = "test.js"):
    parser = parser_registry.get_parser_for_path(file_path)
    lang = parser.language if parser else "JavaScript"
    source_bytes = code.encode("utf-8")
    
    if lang == "TypeScript" and hasattr(parser, "_ts_parser"):
        node = parser._ts_parser.parse(source_bytes).root_node
    elif hasattr(parser, "_parser"):
        node = parser._parser.parse(source_bytes).root_node
    else:
        node = None

    ctx = RuleContext(
        file_path=file_path,
        language=lang,
        source_code=code,
        tree_sitter_node=node,
    )
    return rule.evaluate(ctx)


def test_suspicious_equality_rule():
    rule = SuspiciousEqualityRule()

    # Positive detection
    bad_code = """
if (x === NaN) {
    console.log("Not a number");
}
if (y === y) {
    console.log("Self comparison");
}
"""
    findings = evaluate_js_code(rule, bad_code)
    assert len(findings) == 2
    assert all(f.rule_id == "JS-W001" for f in findings)

    # Negative test
    clean_code = """
if (Number.isNaN(x)) {
    console.log("Valid NaN check");
}
if (x === y) {
    console.log("Comparing two vars");
}
"""
    clean_findings = evaluate_js_code(rule, clean_code)
    assert len(clean_findings) == 0


def test_empty_catch_block_rule():
    rule = EmptyCatchBlockRule()

    # Positive detection
    bad_code = """
try {
    doRisky();
} catch (err) {}
"""
    findings = evaluate_js_code(rule, bad_code)
    assert len(findings) == 1
    assert findings[0].rule_id == "JS-W002"

    # Negative test
    clean_code = """
try {
    doRisky();
} catch (err) {
    console.error("Caught error:", err);
}
"""
    clean_findings = evaluate_js_code(rule, clean_code)
    assert len(clean_findings) == 0


def test_unreachable_code_js_rule():
    rule = UnreachableCodeJSRule()

    # Positive detection
    bad_code = """
function calculate(val) {
    return val * 10;
    console.log("unreachable");
    let z = 5;
}
"""
    findings = evaluate_js_code(rule, bad_code)
    assert len(findings) >= 1
    assert findings[0].rule_id == "JS-W003"
    assert "unreachable" in findings[0].message.lower()

    # Negative test
    clean_code = """
function calculate(val) {
    if (val > 0) {
        return val * 10;
    }
    console.log("fallback");
    return 0;
}
"""
    clean_findings = evaluate_js_code(rule, clean_code)
    assert len(clean_findings) == 0


def test_duplicate_object_key_rule():
    rule = DuplicateObjectKeyRule()

    # Positive detection
    bad_code = """
const user = {
    name: "Alice",
    age: 28,
    name: "Bob"
};
"""
    findings = evaluate_js_code(rule, bad_code)
    assert len(findings) == 1
    assert findings[0].rule_id == "JS-W004"
    assert "name" in findings[0].message

    # Negative test
    clean_code = """
const user = {
    firstName: "Alice",
    lastName: "Bob"
};
"""
    clean_findings = evaluate_js_code(rule, clean_code)
    assert len(clean_findings) == 0


def test_constant_condition_js_rule():
    rule = ConstantConditionJSRule()

    # Positive detection
    bad_code = """
if (true) {
    doAction();
}
if (false) {
    neverRun();
}
"""
    findings = evaluate_js_code(rule, bad_code)
    assert len(findings) == 2
    assert all(f.rule_id == "JS-W005" for f in findings)

    # Negative test
    clean_code = """
if (isActive && hasPermission) {
    doAction();
}
"""
    clean_findings = evaluate_js_code(rule, clean_code)
    assert len(clean_findings) == 0


def test_dangerous_eval_rule():
    rule = DangerousEvalRule()

    # Positive detection
    bad_code = """
const result = eval("2 + 2");
window.eval("alert(1)");
"""
    findings = evaluate_js_code(rule, bad_code)
    assert len(findings) == 2
    assert all(f.rule_id == "JS-W006" for f in findings)
    assert all(f.severity == FindingSeverity.CRITICAL for f in findings)

    # Negative test
    clean_code = """
const parsed = JSON.parse('{"a": 1}');
"""
    clean_findings = evaluate_js_code(rule, clean_code)
    assert len(clean_findings) == 0


def test_assignment_in_condition_rule():
    rule = AssignmentInConditionRule()

    # Positive detection
    bad_code = """
if (x = 10) {
    console.log("Accidental assignment");
}
while (y = 5) {
    break;
}
"""
    findings = evaluate_js_code(rule, bad_code)
    assert len(findings) == 2
    assert all(f.rule_id == "JS-W007" for f in findings)

    # Negative test
    clean_code = """
if (x === 10) {
    console.log("Proper equality");
}
"""
    clean_findings = evaluate_js_code(rule, clean_code)
    assert len(clean_findings) == 0


def test_unused_import_js_rule():
    rule = UnusedImportJSRule()

    # Positive detection
    bad_code = """
import { usedHelper, unusedHelper } from './helpers.js';

console.log(usedHelper());
"""
    findings = evaluate_js_code(rule, bad_code)
    assert len(findings) == 1
    assert findings[0].rule_id == "JS-W008"
    assert "unusedHelper" in findings[0].message

    # Negative test
    clean_code = """
import { usedHelper } from './helpers.js';

console.log(usedHelper());
"""
    clean_findings = evaluate_js_code(rule, clean_code)
    assert len(clean_findings) == 0


def test_null_dereference_rule():
    rule = NullDereferenceRule()

    # Positive detection
    bad_code = """
const a = null.property;
const b = undefined.method();
"""
    findings = evaluate_js_code(rule, bad_code)
    assert len(findings) == 2
    assert all(f.rule_id == "JS-W009" for f in findings)

    # Negative test
    clean_code = """
const a = user?.property;
const b = user ? user.method() : null;
"""
    clean_findings = evaluate_js_code(rule, clean_code)
    assert len(clean_findings) == 0


def test_unawaited_async_call_rule():
    rule = UnawaitedAsyncCallRule()

    # Positive detection
    bad_code = """
async function syncData() {
    fetch("https://api.example.com");
}
"""
    findings = evaluate_js_code(rule, bad_code)
    assert len(findings) == 1
    assert findings[0].rule_id == "JS-W010"

    # Negative test
    clean_code = """
async function syncData() {
    const res = await fetch("https://api.example.com");
    return res;
}
"""
    clean_findings = evaluate_js_code(rule, clean_code)
    assert len(clean_findings) == 0
