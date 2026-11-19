from typing import Dict, List, Optional
from app.schemas.detection import DetectionRuleInfo, FindingSeverity
from app.services.detection.base_rule import BaseRule
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


class RuleRegistry:
    """Central registry for static detection rules."""

    def __init__(self):
        self._rules: Dict[str, BaseRule] = {}
        self._register_default_rules()

    def _register_default_rules(self):
        # Python Rules
        python_rules = [
            DangerousDefaultArgumentRule(),
            EmptyExceptBlockRule(),
            UnreachableCodeRule(),
            SuspiciousComparisonRule(),
            DuplicateDictKeyRule(),
            ConstantConditionRule(),
            DivisionByZeroRule(),
            UnusedImportRule(),
            UndefinedVariableRule(),
            MissingReturnPathRule(),
        ]
        for r in python_rules:
            self.register(r)

        # JavaScript / TypeScript Rules
        js_rules = [
            SuspiciousEqualityRule(),
            EmptyCatchBlockRule(),
            UnreachableCodeJSRule(),
            DuplicateObjectKeyRule(),
            ConstantConditionJSRule(),
            DangerousEvalRule(),
            AssignmentInConditionRule(),
            UnusedImportJSRule(),
            NullDereferenceRule(),
            UnawaitedAsyncCallRule(),
        ]
        for r in js_rules:
            self.register(r)

    def register(self, rule: BaseRule):
        self._rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> Optional[BaseRule]:
        return self._rules.get(rule_id)

    def get_rules_for_language(self, language: str) -> List[BaseRule]:
        lang_norm = language.lower()
        matched = []
        for rule in self._rules.values():
            rule_lang = rule.language.lower()
            if rule_lang in ("multi", "all"):
                matched.append(rule)
            elif rule_lang == "python" and lang_norm == "python":
                matched.append(rule)
            elif rule_lang in ("javascript", "typescript") and lang_norm in ("javascript", "typescript"):
                matched.append(rule)
        return matched

    def list_rules(self, severity: Optional[FindingSeverity] = None) -> List[DetectionRuleInfo]:
        rules = [r.to_info() for r in self._rules.values()]
        if severity:
            rules = [r for r in rules if r.severity == severity]
        return sorted(rules, key=lambda x: x.rule_id)


rule_registry = RuleRegistry()
