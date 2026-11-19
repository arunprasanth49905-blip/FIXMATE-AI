import ast
import builtins
from typing import List, Set, Dict, Optional, Any
from app.schemas.detection import Finding, FindingSeverity, FindingCategory
from app.services.detection.base_rule import BaseRule
from app.services.detection.rule_context import RuleContext

PYTHON_BUILTINS = set(dir(builtins)) | {
    "__file__",
    "__name__",
    "__doc__",
    "__package__",
    "__all__",
    "self",
    "cls",
}


class DangerousDefaultArgumentRule(BaseRule):
    rule_id = "PY-W001"
    name = "dangerous-default-argument"
    language = "Python"
    severity = FindingSeverity.HIGH
    confidence = 0.95
    category = FindingCategory.CORRECTNESS
    description = (
        "Function definition contains a mutable default argument (list, dict, set). "
        "Default arguments are evaluated once at function definition time, leading to shared state bugs."
    )
    remediation_guide = (
        "Replace the mutable default argument with 'None' and initialize inside the function: "
        "'if arg is None: arg = []'."
    )

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.ast_tree:
            return []
        findings = []

        class Visitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                self._check_defaults(node)
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node):
                self._check_defaults(node)
                self.generic_visit(node)

            def _check_defaults(self, node):
                defaults = node.args.defaults + [d for d in node.args.kw_defaults if d is not None]
                for default in defaults:
                    is_mutable = False
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        is_mutable = True
                    elif isinstance(default, ast.Call) and isinstance(default.func, ast.Name):
                        if default.func.id in ("list", "dict", "set"):
                            is_mutable = True

                    if is_mutable:
                        findings.append(
                            DangerousDefaultArgumentRule.create_default_finding(
                                context, node, default
                            )
                        )

        Visitor().visit(context.ast_tree)
        return findings

    @classmethod
    def create_default_finding(cls, context: RuleContext, func_node: ast.AST, default_node: ast.AST) -> Finding:
        rule = cls()
        start_line = getattr(default_node, "lineno", func_node.lineno)
        start_col = getattr(default_node, "col_offset", func_node.col_offset)
        end_line = getattr(default_node, "end_lineno", start_line)
        end_col = getattr(default_node, "end_col_offset", start_col + 10)

        func_name = getattr(func_node, "name", "function")
        return rule.create_finding(
            context=context,
            start_line=start_line,
            start_column=start_col,
            end_line=end_line,
            end_column=end_col,
            message=f"Mutable default argument in function '{func_name}'",
            explanation=rule.description,
        )


class EmptyExceptBlockRule(BaseRule):
    rule_id = "PY-W002"
    name = "empty-except-block"
    language = "Python"
    severity = FindingSeverity.MEDIUM
    confidence = 0.95
    category = FindingCategory.MAINTAINABILITY
    description = (
        "Exception handler block is empty or contains only 'pass' / '...'. "
        "This silences unexpected runtime exceptions and makes debugging severe bugs difficult."
    )
    remediation_guide = "Log the exception, handle the failure explicitly, or specify narrower exception types."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.ast_tree:
            return []
        findings = []

        class Visitor(ast.NodeVisitor):
            def visit_ExceptHandler(self, node: ast.ExceptHandler):
                is_empty = False
                if not node.body:
                    is_empty = True
                elif len(node.body) == 1:
                    stmt = node.body[0]
                    if isinstance(stmt, ast.Pass):
                        is_empty = True
                    elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                        if stmt.value.value is ... or stmt.value.value is Ellipsis:
                            is_empty = True

                if is_empty:
                    findings.append(
                        EmptyExceptBlockRule().create_finding(
                            context=context,
                            start_line=node.lineno,
                            start_column=node.col_offset,
                            end_line=getattr(node, "end_lineno", node.lineno),
                            end_column=getattr(node, "end_col_offset", node.col_offset + 10),
                            message="Empty exception handler silently swallows errors",
                        )
                    )
                self.generic_visit(node)

        Visitor().visit(context.ast_tree)
        return findings


class UnreachableCodeRule(BaseRule):
    rule_id = "PY-W003"
    name = "unreachable-code"
    language = "Python"
    severity = FindingSeverity.MEDIUM
    confidence = 0.90
    category = FindingCategory.CORRECTNESS
    description = (
        "Statements exist immediately after a terminating statement (return, raise, break, continue) "
        "in the same block and will never be executed."
    )
    remediation_guide = "Remove unreachable dead code or correct conditional flow."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.ast_tree:
            return []
        findings = []

        def check_block(stmts: List[ast.stmt]):
            for idx, stmt in enumerate(stmts[:-1]):
                if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                    unreachable_stmt = stmts[idx + 1]
                    findings.append(
                        UnreachableCodeRule().create_finding(
                            context=context,
                            start_line=unreachable_stmt.lineno,
                            start_column=unreachable_stmt.col_offset,
                            end_line=getattr(unreachable_stmt, "end_lineno", unreachable_stmt.lineno),
                            end_column=getattr(unreachable_stmt, "end_col_offset", unreachable_stmt.col_offset + 10),
                            message=f"Code following '{type(stmt).__name__.lower()}' is unreachable",
                        )
                    )
                    break

        class Visitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                check_block(node.body)
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node):
                check_block(node.body)
                self.generic_visit(node)

            def visit_If(self, node):
                check_block(node.body)
                check_block(node.orelse)
                self.generic_visit(node)

            def visit_For(self, node):
                check_block(node.body)
                check_block(node.orelse)
                self.generic_visit(node)

            def visit_While(self, node):
                check_block(node.body)
                check_block(node.orelse)
                self.generic_visit(node)

            def visit_Try(self, node):
                check_block(node.body)
                check_block(node.orelse)
                check_block(node.finalbody)
                self.generic_visit(node)

        Visitor().visit(context.ast_tree)
        return findings


class SuspiciousComparisonRule(BaseRule):
    rule_id = "PY-W004"
    name = "suspicious-comparison"
    language = "Python"
    severity = FindingSeverity.MEDIUM
    confidence = 0.90
    category = FindingCategory.CORRECTNESS
    description = (
        "Suspicious comparison detected: comparing with singleton/literal using incorrect operator "
        "(e.g., '== None', '!= None', 'is 10') or comparing variable against itself ('x == x')."
    )
    remediation_guide = "Use 'is None' / 'is not None' for singletons, '==' for literal equality, and avoid self-comparison."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.ast_tree:
            return []
        findings = []

        class Visitor(ast.NodeVisitor):
            def visit_Compare(self, node: ast.Compare):
                for op, comparator in zip(node.ops, node.comparators):
                    # Check == None or != None
                    if isinstance(op, (ast.Eq, ast.NotEq)):
                        if (isinstance(comparator, ast.Constant) and comparator.value is None) or \
                           (isinstance(node.left, ast.Constant) and node.left.value is None):
                            op_str = "==" if isinstance(op, ast.Eq) else "!="
                            rec = "is None" if isinstance(op, ast.Eq) else "is not None"
                            findings.append(
                                SuspiciousComparisonRule().create_finding(
                                    context=context,
                                    start_line=node.lineno,
                                    start_column=node.col_offset,
                                    end_line=getattr(node, "end_lineno", node.lineno),
                                    end_column=getattr(node, "end_col_offset", node.col_offset + 10),
                                    message=f"Comparison using '{op_str} None'. Use '{rec}' instead.",
                                )
                            )

                        # Check self-comparison x == x
                        elif isinstance(node.left, ast.Name) and isinstance(comparator, ast.Name):
                            if node.left.id == comparator.id:
                                findings.append(
                                    SuspiciousComparisonRule().create_finding(
                                        context=context,
                                        start_line=node.lineno,
                                        start_column=node.col_offset,
                                        end_line=getattr(node, "end_lineno", node.lineno),
                                        end_column=getattr(node, "end_col_offset", node.col_offset + 10),
                                        message=f"Self-comparison '{node.left.id} == {comparator.id}' is always true.",
                                    )
                                )

                    # Check 'is' / 'is not' with int/str literal
                    elif isinstance(op, (ast.Is, ast.IsNot)):
                        if isinstance(comparator, ast.Constant) and isinstance(comparator.value, (int, float, str)):
                            op_str = "is" if isinstance(op, ast.Is) else "is not"
                            findings.append(
                                SuspiciousComparisonRule().create_finding(
                                    context=context,
                                    start_line=node.lineno,
                                    start_column=node.col_offset,
                                    end_line=getattr(node, "end_lineno", node.lineno),
                                    end_column=getattr(node, "end_col_offset", node.col_offset + 10),
                                    message=f"Identity comparison '{op_str}' used with literal value. Use '==' instead.",
                                )
                            )

                self.generic_visit(node)

        Visitor().visit(context.ast_tree)
        return findings


class DuplicateDictKeyRule(BaseRule):
    rule_id = "PY-W005"
    name = "duplicate-dict-key"
    language = "Python"
    severity = FindingSeverity.HIGH
    confidence = 0.95
    category = FindingCategory.CORRECTNESS
    description = "Dictionary literal contains duplicate literal keys. Earlier keys will be overwritten."
    remediation_guide = "Remove or rename the duplicate dictionary key."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.ast_tree:
            return []
        findings = []

        class Visitor(ast.NodeVisitor):
            def visit_Dict(self, node: ast.Dict):
                seen_keys: Dict[Any, ast.AST] = {}
                for key_node in node.keys:
                    if key_node is not None and isinstance(key_node, ast.Constant):
                        key_val = key_node.value
                        if key_val in seen_keys:
                            findings.append(
                                DuplicateDictKeyRule().create_finding(
                                    context=context,
                                    start_line=key_node.lineno,
                                    start_column=key_node.col_offset,
                                    end_line=getattr(key_node, "end_lineno", key_node.lineno),
                                    end_column=getattr(key_node, "end_col_offset", key_node.col_offset + 5),
                                    message=f"Duplicate dictionary key '{repr(key_val)}' overwrites previous entry",
                                )
                            )
                        else:
                            seen_keys[key_val] = key_node
                self.generic_visit(node)

        Visitor().visit(context.ast_tree)
        return findings


class ConstantConditionRule(BaseRule):
    rule_id = "PY-W006"
    name = "constant-condition"
    language = "Python"
    severity = FindingSeverity.LOW
    confidence = 0.90
    category = FindingCategory.SUSPICIOUS
    description = (
        "Conditional expression evaluates to a constant literal (e.g. 'if True:', 'if False:', 'if 0:', 'while False:'). "
        "The branch is either dead or redundant."
    )
    remediation_guide = "Replace constant test with a dynamic boolean expression or remove the redundant condition."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.ast_tree:
            return []
        findings = []

        class Visitor(ast.NodeVisitor):
            def visit_If(self, node: ast.If):
                # Check for constant boolean/int literal in If test (exclude TYPE_CHECKING)
                if isinstance(node.test, ast.Constant):
                    if node.test.value in (True, False, 0, 1):
                        findings.append(
                            ConstantConditionRule().create_finding(
                                context=context,
                                start_line=node.test.lineno,
                                start_column=node.test.col_offset,
                                end_line=getattr(node.test, "end_lineno", node.test.lineno),
                                end_column=getattr(node.test, "end_col_offset", node.test.col_offset + 5),
                                message=f"Constant condition 'if {node.test.value}' creates redundant or dead branch",
                            )
                        )
                self.generic_visit(node)

            def visit_While(self, node: ast.While):
                # Allow while True: idiom, but flag while False: or while 0:
                if isinstance(node.test, ast.Constant) and node.test.value in (False, 0):
                    findings.append(
                        ConstantConditionRule().create_finding(
                            context=context,
                            start_line=node.test.lineno,
                            start_column=node.test.col_offset,
                            end_line=getattr(node.test, "end_lineno", node.test.lineno),
                            end_column=getattr(node.test, "end_col_offset", node.test.col_offset + 5),
                            message=f"While loop with constant condition '{node.test.value}' will never execute",
                        )
                    )
                self.generic_visit(node)

        Visitor().visit(context.ast_tree)
        return findings


class DivisionByZeroRule(BaseRule):
    rule_id = "PY-W007"
    name = "division-by-zero"
    language = "Python"
    severity = FindingSeverity.HIGH
    confidence = 0.95
    category = FindingCategory.CORRECTNESS
    description = "Division or modulo by literal zero will raise a ZeroDivisionError at runtime."
    remediation_guide = "Ensure the divisor is non-zero or add a conditional guard check before division."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.ast_tree:
            return []
        findings = []

        class Visitor(ast.NodeVisitor):
            def visit_BinOp(self, node: ast.BinOp):
                if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                    if isinstance(node.right, ast.Constant) and node.right.value in (0, 0.0):
                        op_char = "/" if isinstance(node.op, ast.Div) else ("//" if isinstance(node.op, ast.FloorDiv) else "%")
                        findings.append(
                            DivisionByZeroRule().create_finding(
                                context=context,
                                start_line=node.lineno,
                                start_column=node.col_offset,
                                end_line=getattr(node, "end_lineno", node.lineno),
                                end_column=getattr(node, "end_col_offset", node.col_offset + 5),
                                message=f"Potential division by zero: operator '{op_char}' with divisor 0",
                            )
                        )
                self.generic_visit(node)

        Visitor().visit(context.ast_tree)
        return findings


class UnusedImportRule(BaseRule):
    rule_id = "PY-W008"
    name = "unused-import"
    language = "Python"
    severity = FindingSeverity.LOW
    confidence = 0.85
    category = FindingCategory.MAINTAINABILITY
    description = "Imported module or symbol is never referenced in this file."
    remediation_guide = "Remove the unused import to keep dependencies and module scope clean."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.ast_tree or context.file_path.endswith("__init__.py"):
            return []
        findings = []

        imported_symbols: Dict[str, ast.AST] = {}

        class ImportCollector(ast.NodeVisitor):
            def visit_Import(self, node: ast.Import):
                for alias in node.names:
                    name_to_track = alias.asname if alias.asname else alias.name.split(".")[0]
                    imported_symbols[name_to_track] = node

            def visit_ImportFrom(self, node: ast.ImportFrom):
                for alias in node.names:
                    if alias.name != "*":
                        name_to_track = alias.asname if alias.asname else alias.name
                        imported_symbols[name_to_track] = node

        ImportCollector().visit(context.ast_tree)

        # Collect all used names across the AST
        used_names: Set[str] = set()

        class NameCollector(ast.NodeVisitor):
            def visit_Name(self, node: ast.Name):
                used_names.add(node.id)
                self.generic_visit(node)

            def visit_Attribute(self, node: ast.Attribute):
                used_names.add(node.attr)
                self.generic_visit(node)

        NameCollector().visit(context.ast_tree)

        for sym, node in imported_symbols.items():
            if sym not in used_names:
                findings.append(
                    UnusedImportRule().create_finding(
                        context=context,
                        start_line=node.lineno,
                        start_column=node.col_offset,
                        end_line=getattr(node, "end_lineno", node.lineno),
                        end_column=getattr(node, "end_col_offset", node.col_offset + 10),
                        message=f"Unused import '{sym}' is never referenced",
                    )
                )

        return findings


class UndefinedVariableRule(BaseRule):
    rule_id = "PY-W009"
    name = "undefined-variable"
    language = "Python"
    severity = FindingSeverity.CRITICAL
    confidence = 0.85
    category = FindingCategory.CORRECTNESS
    description = (
        "Variable is referenced in local function scope without being defined, "
        "imported, or passed as a parameter."
    )
    remediation_guide = "Define, initialize, or import the variable before using it."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.ast_tree:
            return []
        findings = []

        # Collect top-level imports and module globals
        module_globals: Set[str] = set(PYTHON_BUILTINS)

        class GlobalCollector(ast.NodeVisitor):
            def visit_Import(self, node: ast.Import):
                for alias in node.names:
                    module_globals.add(alias.asname or alias.name.split(".")[0])

            def visit_ImportFrom(self, node: ast.ImportFrom):
                for alias in node.names:
                    module_globals.add(alias.asname or alias.name)

            def visit_FunctionDef(self, node: ast.FunctionDef):
                module_globals.add(node.name)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                module_globals.add(node.name)

            def visit_ClassDef(self, node: ast.ClassDef):
                module_globals.add(node.name)

            def visit_Assign(self, node: ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        module_globals.add(target.id)

        GlobalCollector().visit(context.ast_tree)

        # Inspect local scopes
        class FunctionScopeChecker(ast.NodeVisitor):
            def visit_FunctionDef(self, node: ast.FunctionDef):
                self._check_func(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                self._check_func(node)

            def _check_func(self, node: ast.AST):
                local_names: Set[str] = set(module_globals)
                # Add parameters
                for arg in node.args.args + node.args.kwonlyargs:
                    local_names.add(arg.arg)
                if node.args.vararg:
                    local_names.add(node.args.vararg.arg)
                if node.args.kwarg:
                    local_names.add(node.args.kwarg.arg)

                # Pre-collect local definitions inside this function
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Assign):
                        for t in sub.targets:
                            if isinstance(t, ast.Name):
                                local_names.add(t.id)
                    elif isinstance(sub, (ast.For, ast.AsyncFor)) and isinstance(sub.target, ast.Name):
                        local_names.add(sub.target.id)
                    elif isinstance(sub, ast.With):
                        for item in sub.items:
                            if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                                local_names.add(item.optional_vars.id)
                    elif isinstance(sub, ast.ExceptHandler) and sub.name:
                        local_names.add(sub.name)
                    elif isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        local_names.add(sub.name)

                # Now check all loaded names
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Load):
                        if sub.id not in local_names:
                            findings.append(
                                UndefinedVariableRule().create_finding(
                                    context=context,
                                    start_line=sub.lineno,
                                    start_column=sub.col_offset,
                                    end_line=getattr(sub, "end_lineno", sub.lineno),
                                    end_column=getattr(sub, "end_col_offset", sub.col_offset + len(sub.id)),
                                    message=f"Undefined variable '{sub.id}' accessed in local scope",
                                )
                            )

        FunctionScopeChecker().visit(context.ast_tree)
        return findings


class MissingReturnPathRule(BaseRule):
    rule_id = "PY-W010"
    name = "missing-return-path"
    language = "Python"
    severity = FindingSeverity.MEDIUM
    confidence = 0.80
    category = FindingCategory.CORRECTNESS
    description = (
        "Function contains an explicit value return path but can fall through to implicit None "
        "without returning a value."
    )
    remediation_guide = "Ensure all execution branches explicitly return a value or raise an exception."

    def evaluate(self, context: RuleContext) -> List[Finding]:
        if not context.ast_tree:
            return []
        findings = []

        class Visitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node: ast.FunctionDef):
                self._check_returns(node)
                self.generic_visit(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
                self._check_returns(node)
                self.generic_visit(node)

            def _check_returns(self, node: ast.AST):
                # Ignore dunder methods like __init__
                if node.name.startswith("__") and node.name.endswith("__"):
                    return

                has_value_return = False
                terminal_return_at_end = False

                for stmt in ast.walk(node):
                    if isinstance(stmt, ast.Return) and stmt.value is not None:
                        has_value_return = True
                        break

                if not has_value_return or not node.body:
                    return

                last_stmt = node.body[-1]
                if isinstance(last_stmt, (ast.Return, ast.Raise)):
                    terminal_return_at_end = True

                if has_value_return and not terminal_return_at_end:
                    findings.append(
                        MissingReturnPathRule().create_finding(
                            context=context,
                            start_line=node.lineno,
                            start_column=node.col_offset,
                            end_line=node.lineno,
                            end_column=node.col_offset + len(node.name),
                            message=f"Function '{node.name}' has branches returning values but may fall through without returning",
                        )
                    )

        Visitor().visit(context.ast_tree)
        return findings
