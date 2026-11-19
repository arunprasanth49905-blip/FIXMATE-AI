from typing import List, Set, Dict, Optional, Any
from tree_sitter import Node
from app.schemas.detection import Finding, FindingSeverity, FindingCategory
from app.services.detection.base_rule import BaseRule
from app.services.detection.rule_context import RuleContext


def get_node_text(node: Optional[Node], source_bytes: bytes) -> str:
    if node is None:
        return ""
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def walk_tree(node: Node):
    """Generator traversing tree-sitter node recursively."""
    yield node
    for child in node.children:
        yield from walk_tree(child)


class SuspiciousEqualityRule(BaseRule):
    rule_id = "JS-W001"
    name = "suspicious-equality"
    language = "Multi"
    severity = FindingSeverity.MEDIUM
    confidence = 0.90
    category = FindingCategory.CORRECTNESS
    description = (
        "Suspicious equality comparison: 'x === NaN' is always false (NaN never equals itself); "
        "or self-comparison 'x === x' is redundant; or loose equality '== null'."
    )
    remediation_guide = "Use 'Number.isNaN(x)' to test for NaN; avoid self-comparison; use '=== null' or '??'."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.tree_sitter_node:
            return []
        findings = []
        source_bytes = context.source_code.encode("utf-8")

        for node in walk_tree(context.tree_sitter_node):
            if node.type == "binary_expression":
                left = node.child_by_field_name("left")
                operator = node.child_by_field_name("operator")
                right = node.child_by_field_name("right")

                if left and operator and right:
                    op_text = get_node_text(operator, source_bytes)
                    left_text = get_node_text(left, source_bytes).strip()
                    right_text = get_node_text(right, source_bytes).strip()

                    # Check NaN comparison
                    if op_text in ("===", "==", "!==", "!=") and (left_text == "NaN" or right_text == "NaN"):
                        findings.append(
                            SuspiciousEqualityRule().create_finding(
                                context=context,
                                start_line=node.start_point[0] + 1,
                                start_column=node.start_point[1],
                                end_line=node.end_point[0] + 1,
                                end_column=node.end_point[1],
                                message=f"Comparison with NaN using '{op_text}'. Use 'Number.isNaN()' instead.",
                            )
                        )
                    # Check self comparison
                    elif op_text in ("===", "==", "!==", "!=") and left_text == right_text and left.type in ("identifier", "member_expression"):
                        findings.append(
                            SuspiciousEqualityRule().create_finding(
                                context=context,
                                start_line=node.start_point[0] + 1,
                                start_column=node.start_point[1],
                                end_line=node.end_point[0] + 1,
                                end_column=node.end_point[1],
                                message=f"Redundant self-comparison '{left_text} {op_text} {right_text}'.",
                            )
                        )

        return findings


class EmptyCatchBlockRule(BaseRule):
    rule_id = "JS-W002"
    name = "empty-catch-block"
    language = "Multi"
    severity = FindingSeverity.MEDIUM
    confidence = 0.95
    category = FindingCategory.MAINTAINABILITY
    description = "Catch block is empty. Unhandled exceptions are silently ignored, hiding runtime failures."
    remediation_guide = "Log the error, handle the failure condition, or re-throw the exception."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.tree_sitter_node:
            return []
        findings = []
        source_bytes = context.source_code.encode("utf-8")

        for node in walk_tree(context.tree_sitter_node):
            if node.type == "catch_clause":
                body = node.child_by_field_name("body")
                if body and body.type == "statement_block":
                    # Check if body contains any named statements other than comments
                    named_children = [
                        c for c in body.children
                        if c.is_named and not c.type.endswith("comment") and c.type not in ("{", "}")
                    ]
                    if len(named_children) == 0:
                        findings.append(
                            EmptyCatchBlockRule().create_finding(
                                context=context,
                                start_line=node.start_point[0] + 1,
                                start_column=node.start_point[1],
                                end_line=node.end_point[0] + 1,
                                end_column=node.end_point[1],
                                message="Empty catch block silently ignores runtime errors",
                            )
                        )

        return findings


class UnreachableCodeJSRule(BaseRule):
    rule_id = "JS-W003"
    name = "unreachable-code-js"
    language = "Multi"
    severity = FindingSeverity.MEDIUM
    confidence = 0.90
    category = FindingCategory.CORRECTNESS
    description = "Statements following return, throw, break, or continue in the same block are unreachable."
    remediation_guide = "Remove dead code or correct conditional execution logic."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.tree_sitter_node:
            return []
        findings = []

        terminal_types = {"return_statement", "throw_statement", "break_statement", "continue_statement"}

        for node in walk_tree(context.tree_sitter_node):
            if node.type == "statement_block":
                children = [c for c in node.children if c.is_named and not c.type.endswith("comment")]
                for idx, stmt in enumerate(children[:-1]):
                    if stmt.type in terminal_types:
                        unreachable = children[idx + 1]
                        findings.append(
                            UnreachableCodeJSRule().create_finding(
                                context=context,
                                start_line=unreachable.start_point[0] + 1,
                                start_column=unreachable.start_point[1],
                                end_line=unreachable.end_point[0] + 1,
                                end_column=unreachable.end_point[1],
                                message=f"Code following '{stmt.type.replace('_statement', '')}' is unreachable",
                            )
                        )
                        break

        return findings


class DuplicateObjectKeyRule(BaseRule):
    rule_id = "JS-W004"
    name = "duplicate-object-key"
    language = "Multi"
    severity = FindingSeverity.HIGH
    confidence = 0.95
    category = FindingCategory.CORRECTNESS
    description = "Object literal contains duplicate property names. The later property overwrites earlier ones."
    remediation_guide = "Remove or rename the redundant duplicate object property."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.tree_sitter_node:
            return []
        findings = []
        source_bytes = context.source_code.encode("utf-8")

        for node in walk_tree(context.tree_sitter_node):
            if node.type == "object":
                seen_keys: Set[str] = set()
                for child in node.children:
                    if child.type in ("pair", "property_assignment"):
                        key_node = child.child_by_field_name("key")
                        if key_node:
                            key_text = get_node_text(key_node, source_bytes).strip("'\"")
                            if key_text in seen_keys:
                                findings.append(
                                    DuplicateObjectKeyRule().create_finding(
                                        context=context,
                                        start_line=key_node.start_point[0] + 1,
                                        start_column=key_node.start_point[1],
                                        end_line=key_node.end_point[0] + 1,
                                        end_column=key_node.end_point[1],
                                        message=f"Duplicate object property '{key_text}' overwrites previous value",
                                    )
                                )
                            else:
                                seen_keys.add(key_text)

        return findings


class ConstantConditionJSRule(BaseRule):
    rule_id = "JS-W005"
    name = "constant-condition-js"
    language = "Multi"
    severity = FindingSeverity.LOW
    confidence = 0.90
    category = FindingCategory.SUSPICIOUS
    description = "Conditional statement has a constant condition ('if (true)', 'if (false)', 'if (0)')."
    remediation_guide = "Replace the literal condition with a dynamic test or remove the redundant check."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.tree_sitter_node:
            return []
        findings = []
        source_bytes = context.source_code.encode("utf-8")

        for node in walk_tree(context.tree_sitter_node):
            if node.type == "if_statement":
                cond = node.child_by_field_name("condition")
                if cond:
                    cond_text = get_node_text(cond, source_bytes).strip("()")
                    if cond_text in ("true", "false", "0", "1"):
                        findings.append(
                            ConstantConditionJSRule().create_finding(
                                context=context,
                                start_line=cond.start_point[0] + 1,
                                start_column=cond.start_point[1],
                                end_line=cond.end_point[0] + 1,
                                end_column=cond.end_point[1],
                                message=f"Constant condition 'if ({cond_text})' results in redundant or dead branch",
                            )
                        )

        return findings


class DangerousEvalRule(BaseRule):
    rule_id = "JS-W006"
    name = "dangerous-eval"
    language = "Multi"
    severity = FindingSeverity.CRITICAL
    confidence = 0.95
    category = FindingCategory.SECURITY
    description = (
        "Invocation of 'eval()' allows arbitrary script execution, opens severe security vulnerabilities "
        "(XSS / remote code execution), and prevents JavaScript engine optimizations."
    )
    remediation_guide = "Refactor away from 'eval()'; use 'JSON.parse()', maps, or structured functions."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.tree_sitter_node:
            return []
        findings = []
        source_bytes = context.source_code.encode("utf-8")

        for node in walk_tree(context.tree_sitter_node):
            if node.type == "call_expression":
                func = node.child_by_field_name("function")
                if func:
                    func_text = get_node_text(func, source_bytes).strip()
                    if func_text in ("eval", "window.eval", "global.eval", "globalThis.eval"):
                        findings.append(
                            DangerousEvalRule().create_finding(
                                context=context,
                                start_line=node.start_point[0] + 1,
                                start_column=node.start_point[1],
                                end_line=node.end_point[0] + 1,
                                end_column=node.end_point[1],
                                message=f"Dangerous execution of '{func_text}()'",
                            )
                        )

        return findings


class AssignmentInConditionRule(BaseRule):
    rule_id = "JS-W007"
    name = "assignment-in-condition"
    language = "Multi"
    severity = FindingSeverity.HIGH
    confidence = 0.90
    category = FindingCategory.CORRECTNESS
    description = (
        "Assignment operator '=' used inside conditional expression instead of comparison operator '==='."
    )
    remediation_guide = "Replace '=' with strict comparison '===' or perform assignment outside the condition."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.tree_sitter_node:
            return []
        findings = []

        for node in walk_tree(context.tree_sitter_node):
            if node.type in ("if_statement", "while_statement", "do_statement"):
                cond = node.child_by_field_name("condition")
                if cond:
                    for child in walk_tree(cond):
                        if child.type == "assignment_expression":
                            findings.append(
                                AssignmentInConditionRule().create_finding(
                                    context=context,
                                    start_line=child.start_point[0] + 1,
                                    start_column=child.start_point[1],
                                    end_line=child.end_point[0] + 1,
                                    end_column=child.end_point[1],
                                    message="Unexpected assignment '=' in conditional test. Did you mean '==='?",
                                )
                            )

        return findings


class UnusedImportJSRule(BaseRule):
    rule_id = "JS-W008"
    name = "unused-import-js"
    language = "Multi"
    severity = FindingSeverity.LOW
    confidence = 0.85
    category = FindingCategory.MAINTAINABILITY
    description = "Imported identifier is never referenced in this module."
    remediation_guide = "Remove the unused import specifier to minimize bundle size and clutter."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.tree_sitter_node:
            return []
        findings = []
        source_bytes = context.source_code.encode("utf-8")

        imported_specifiers: Dict[str, Node] = {}
        all_other_identifiers: Set[str] = set()

        for node in walk_tree(context.tree_sitter_node):
            if node.type in ("import_specifier", "import_default_specifier"):
                name_node = node.child_by_field_name("name") or node
                spec_text = get_node_text(name_node, source_bytes).strip()
                if spec_text:
                    imported_specifiers[spec_text] = node
            elif node.type == "identifier":
                # Check if this identifier is not inside an import_statement
                parent = node.parent
                is_import = False
                while parent:
                    if parent.type == "import_statement":
                        is_import = True
                        break
                    parent = parent.parent

                if not is_import:
                    all_other_identifiers.add(get_node_text(node, source_bytes).strip())

        for name, spec_node in imported_specifiers.items():
            if name not in all_other_identifiers:
                findings.append(
                    UnusedImportJSRule().create_finding(
                        context=context,
                        start_line=spec_node.start_point[0] + 1,
                        start_column=spec_node.start_point[1],
                        end_line=spec_node.end_point[0] + 1,
                        end_column=spec_node.end_point[1],
                        message=f"Unused import '{name}' is never referenced",
                    )
                )

        return findings


class NullDereferenceRule(BaseRule):
    rule_id = "JS-W009"
    name = "null-dereference"
    language = "Multi"
    severity = FindingSeverity.HIGH
    confidence = 0.90
    category = FindingCategory.CORRECTNESS
    description = "Property access or invocation on literal 'null' or 'undefined' will throw TypeError at runtime."
    remediation_guide = "Guard property access with optional chaining '?.' or check variable before access."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.tree_sitter_node:
            return []
        findings = []
        source_bytes = context.source_code.encode("utf-8")

        for node in walk_tree(context.tree_sitter_node):
            if node.type in ("member_expression", "call_expression"):
                obj = node.child_by_field_name("object") or node.child_by_field_name("function")
                if obj:
                    obj_text = get_node_text(obj, source_bytes).strip()
                    if obj_text in ("null", "undefined"):
                        findings.append(
                            NullDereferenceRule().create_finding(
                                context=context,
                                start_line=node.start_point[0] + 1,
                                start_column=node.start_point[1],
                                end_line=node.end_point[0] + 1,
                                end_column=node.end_point[1],
                                message=f"Deterministic property access on literal '{obj_text}'",
                            )
                        )

        return findings


class UnawaitedAsyncCallRule(BaseRule):
    rule_id = "JS-W010"
    name = "unawaited-async-call"
    language = "Multi"
    severity = FindingSeverity.MEDIUM
    confidence = 0.80
    category = FindingCategory.CORRECTNESS
    description = (
        "Asynchronous function call or promise expression is executed in an expression statement "
        "without 'await' or promise chaining, which may lead to unhandled promise rejections."
    )
    remediation_guide = "Prefix with 'await' or attach a '.catch()' handler to handle errors."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.tree_sitter_node:
            return []
        findings = []
        source_bytes = context.source_code.encode("utf-8")

        # Walk for expression statements inside async functions
        for node in walk_tree(context.tree_sitter_node):
            if node.type == "expression_statement":
                child = node.named_children[0] if node.named_children else None
                if child and child.type == "call_expression":
                    # Check if call ends in .then(...) or is a fetch(...) call
                    call_text = get_node_text(child, source_bytes).strip()
                    if call_text.startswith("fetch(") or ".then(" in call_text:
                        # Check if parent scope is async function
                        p = node.parent
                        is_in_async = False
                        while p:
                            if p.type in ("function_declaration", "arrow_function", "method_definition"):
                                for c in p.children:
                                    if c.type == "async":
                                        is_in_async = True
                                        break
                                break
                            p = p.parent

                        if is_in_async:
                            findings.append(
                                UnawaitedAsyncCallRule().create_finding(
                                    context=context,
                                    start_line=node.start_point[0] + 1,
                                    start_column=node.start_point[1],
                                    end_line=node.end_point[0] + 1,
                                    end_column=node.end_point[1],
                                    message="Asynchronous promise call executed without 'await' in async scope",
                                )
                            )

        return findings
