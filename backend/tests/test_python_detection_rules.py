import ast
import pytest
from app.schemas.detection import FindingSeverity, FindingCategory
from app.services.detection.rule_context import RuleContext
from app.services.detection.rules.python_rules import (
    DangerousDefaultArgumentRule,
    EmptyExceptBlockRule,
    UnreachableCodeRule,
    SuspiciousComparisonRule,
    DuplicateDictKeyRule,
    ConstantConditionRule,
    DivisionByZeroRule,
    UnusedImportRule,
    UndefinedVariableRule,
    MissingReturnPathRule,
)


def evaluate_python_code(rule, code: str, file_path: str = "test.py"):
    tree = ast.parse(code, filename=file_path)
    ctx = RuleContext(
        file_path=file_path,
        language="Python",
        source_code=code,
        ast_tree=tree,
    )
    return rule.evaluate(ctx)


def test_dangerous_default_argument_rule():
    rule = DangerousDefaultArgumentRule()

    # Positive detection
    bad_code = """
def process_items(items=[]):
    items.append(1)
    return items

def config(data=dict()):
    pass
"""
    findings = evaluate_python_code(rule, bad_code)
    assert len(findings) == 2
    assert findings[0].rule_id == "PY-W001"
    assert findings[0].severity == FindingSeverity.HIGH
    assert findings[0].start_line == 2

    # Negative test (clean code)
    clean_code = """
def process_items(items=None):
    if items is None:
        items = []
    return items
"""
    clean_findings = evaluate_python_code(rule, clean_code)
    assert len(clean_findings) == 0


def test_empty_except_block_rule():
    rule = EmptyExceptBlockRule()

    # Positive detection
    bad_code = """
try:
    risky_operation()
except Exception:
    pass

try:
    other()
except:
    ...
"""
    findings = evaluate_python_code(rule, bad_code)
    assert len(findings) == 2
    assert findings[0].rule_id == "PY-W002"
    assert findings[0].severity == FindingSeverity.MEDIUM

    # Negative test
    clean_code = """
try:
    risky_operation()
except Exception as e:
    logger.error("Failed: %s", e)
    raise
"""
    clean_findings = evaluate_python_code(rule, clean_code)
    assert len(clean_findings) == 0


def test_unreachable_code_rule():
    rule = UnreachableCodeRule()

    # Positive detection
    bad_code = """
def calculate(x):
    return x * 2
    print("Done")
    y = 10
"""
    findings = evaluate_python_code(rule, bad_code)
    assert len(findings) >= 1
    assert findings[0].rule_id == "PY-W003"
    assert findings[0].start_line == 4

    # Negative test
    clean_code = """
def calculate(x):
    if x > 0:
        return x * 2
    print("Zero or negative")
    return 0
"""
    clean_findings = evaluate_python_code(rule, clean_code)
    assert len(clean_findings) == 0


def test_suspicious_comparison_rule():
    rule = SuspiciousComparisonRule()

    # Positive detection
    bad_code = """
if val == None:
    pass
if val != None:
    pass
if count is 10:
    pass
if x == x:
    pass
"""
    findings = evaluate_python_code(rule, bad_code)
    assert len(findings) == 4
    assert all(f.rule_id == "PY-W004" for f in findings)

    # Negative test
    clean_code = """
if val is None:
    pass
if val is not None:
    pass
if count == 10:
    pass
if x == y:
    pass
"""
    clean_findings = evaluate_python_code(rule, clean_code)
    assert len(clean_findings) == 0


def test_duplicate_dict_key_rule():
    rule = DuplicateDictKeyRule()

    # Positive detection
    bad_code = """
config = {
    "host": "localhost",
    "port": 8080,
    "host": "0.0.0.0"
}
"""
    findings = evaluate_python_code(rule, bad_code)
    assert len(findings) == 1
    assert findings[0].rule_id == "PY-W005"
    assert "host" in findings[0].message

    # Negative test
    clean_code = """
config = {
    "host": "localhost",
    "port": 8080,
    "alt_host": "0.0.0.0"
}
"""
    clean_findings = evaluate_python_code(rule, clean_code)
    assert len(clean_findings) == 0


def test_constant_condition_rule():
    rule = ConstantConditionRule()

    # Positive detection
    bad_code = """
if True:
    do_something()
if False:
    unreachable()
while False:
    loop()
"""
    findings = evaluate_python_code(rule, bad_code)
    assert len(findings) == 3
    assert all(f.rule_id == "PY-W006" for f in findings)

    # Negative test (standard while True: is allowed)
    clean_code = """
while True:
    message = queue.get()
    if message.is_valid():
        break
"""
    clean_findings = evaluate_python_code(rule, clean_code)
    assert len(clean_findings) == 0


def test_division_by_zero_rule():
    rule = DivisionByZeroRule()

    # Positive detection
    bad_code = """
a = 100 / 0
b = 50 // 0
c = total % 0
"""
    findings = evaluate_python_code(rule, bad_code)
    assert len(findings) == 3
    assert all(f.rule_id == "PY-W007" for f in findings)

    # Negative test
    clean_code = """
if denominator != 0:
    res = numerator / denominator
"""
    clean_findings = evaluate_python_code(rule, clean_code)
    assert len(clean_findings) == 0


def test_unused_import_rule():
    rule = UnusedImportRule()

    # Positive detection
    bad_code = """
import os
import sys
from math import sqrt, pi

print(os.getcwd())
print(sqrt(16))
"""
    # sys and pi are unused
    findings = evaluate_python_code(rule, bad_code)
    assert len(findings) == 2
    rule_messages = [f.message for f in findings]
    assert any("sys" in m for m in rule_messages)
    assert any("pi" in m for m in rule_messages)

    # Negative test (__init__.py exemption)
    init_code = "from .module import Feature\n"
    init_findings = evaluate_python_code(rule, init_code, file_path="__init__.py")
    assert len(init_findings) == 0


def test_undefined_variable_rule():
    rule = UndefinedVariableRule()

    # Positive detection
    bad_code = """
def calculate(x):
    y = x + undeclared_var
    return y
"""
    findings = evaluate_python_code(rule, bad_code)
    assert len(findings) == 1
    assert findings[0].rule_id == "PY-W009"
    assert "undeclared_var" in findings[0].message
    assert findings[0].severity == FindingSeverity.CRITICAL

    # Negative test
    clean_code = """
import math

GLOBAL_CONST = 42

def calculate(x):
    local_val = 10
    for i in range(x):
        local_val += i
    return math.sqrt(local_val) + GLOBAL_CONST
"""
    clean_findings = evaluate_python_code(rule, clean_code)
    assert len(clean_findings) == 0


def test_missing_return_path_rule():
    rule = MissingReturnPathRule()

    # Positive detection
    bad_code = """
def get_user_status(user):
    if user.is_active:
        return "active"
    elif user.is_banned:
        return "banned"
    # Falls through without return
"""
    findings = evaluate_python_code(rule, bad_code)
    assert len(findings) == 1
    assert findings[0].rule_id == "PY-W010"

    # Negative test
    clean_code = """
def get_user_status(user):
    if user.is_active:
        return "active"
    return "inactive"
"""
    clean_findings = evaluate_python_code(rule, clean_code)
    assert len(clean_findings) == 0
