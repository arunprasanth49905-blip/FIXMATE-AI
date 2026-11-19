import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

import tree_sitter_javascript as tsjs
from tree_sitter import Language, Parser, Node

from app.schemas.parsing import (
    FileAnalysis,
    FileStatistics,
    Symbol,
    ImportSymbol,
    ParameterInfo,
    SyntaxDiagnostic,
)
from app.services.parsing.base_parser import BaseParser
from app.services.parsing.syntax_diagnostics import DiagnosticsFactory


class JavaScriptParser(BaseParser):
    def __init__(self):
        self._language = Language(tsjs.language())
        self._parser = Parser(self._language)

    @property
    def language(self) -> str:
        return "JavaScript"

    @property
    def parser_name(self) -> str:
        return "tree-sitter-javascript"

    @property
    def supported_extensions(self) -> List[str]:
        return [".js", ".jsx", ".mjs", ".cjs"]

    def _get_node_text(self, node: Optional[Node], source_bytes: bytes) -> str:
        if node is None:
            return ""
        return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    def _collect_errors(self, node: Node, file_path: str, file_id: Optional[str], source_bytes: bytes) -> List[SyntaxDiagnostic]:
        diagnostics = []
        if node.type == "ERROR" or node.is_missing:
            snippet = self._get_node_text(node, source_bytes).strip()
            msg = f"Syntax error near '{snippet[:40]}'" if snippet else "Unexpected or missing token"
            line = node.start_point[0] + 1
            col = node.start_point[1]
            end_line = node.end_point[0] + 1
            end_col = node.end_point[1]
            diagnostics.append(
                DiagnosticsFactory.create(
                    file_path=file_path,
                    file_id=file_id,
                    message=msg,
                    line=line,
                    column=col,
                    end_line=end_line,
                    end_column=end_col,
                    severity="error",
                    category="syntax",
                    parser_name=self.parser_name,
                    error_code="JS_SYNTAX_ERROR",
                )
            )

        for child in node.children:
            diagnostics.extend(self._collect_errors(child, file_path, file_id, source_bytes))
        return diagnostics

    def parse(
        self,
        source_code: str,
        file_path: str,
        file_id: Optional[str] = None,
        project_id: str = "",
        analysis_id: Optional[str] = None,
    ) -> FileAnalysis:
        source_bytes = source_code.encode("utf-8")
        source_hash = hashlib.sha256(source_bytes).hexdigest()
        source_size = len(source_bytes)
        lines_count = len(source_code.splitlines()) if source_code else 0
        timestamp = datetime.now(timezone.utc).isoformat()

        if not source_code.strip():
            stats = FileStatistics(lines=lines_count)
            return FileAnalysis(
                analysis_id=analysis_id,
                project_id=project_id,
                file_id=file_id,
                file_path=file_path,
                language=self.language,
                parser=self.parser_name,
                status="success",
                source_hash=source_hash,
                source_size=source_size,
                analysis_timestamp=timestamp,
                statistics=stats,
                symbols=[],
                imports=[],
                diagnostics=[],
                structure={"classes": [], "functions": [], "variables": [], "imports": []},
            )

        try:
            tree = self._parser.parse(source_bytes)
            root = tree.root_node

            diagnostics: List[SyntaxDiagnostic] = []
            if root.has_error:
                diagnostics = self._collect_errors(root, file_path, file_id, source_bytes)

            stats = FileStatistics(lines=lines_count)
            symbols: List[Symbol] = []
            imports: List[ImportSymbol] = []
            call_names: List[str] = []

            # Traverse AST
            def traverse(node: Node, parent_name: Optional[str] = None, nesting: int = 0):
                nonlocal stats

                ntype = node.type

                # 1. Imports
                if ntype == "import_statement":
                    stats.imports += 1
                    source_mod = ""
                    imported_names = []
                    for child in node.children:
                        if child.type == "string":
                            source_mod = self._get_node_text(child, source_bytes).strip("\"'")
                        elif child.type == "import_clause":
                            for sub in child.children:
                                if sub.type == "identifier":
                                    imported_names.append(self._get_node_text(sub, source_bytes))
                                elif sub.type == "named_imports":
                                    for spec in sub.children:
                                        if spec.type == "import_specifier":
                                            imported_names.append(self._get_node_text(spec, source_bytes))
                                elif sub.type == "namespace_import":
                                    imported_names.append(self._get_node_text(sub, source_bytes))

                    imports.append(
                        ImportSymbol(
                            source_module=source_mod,
                            imported_names=imported_names,
                            file_id=file_id,
                            file_path=file_path,
                            line=node.start_point[0] + 1,
                            column=node.start_point[1],
                            import_type="standard",
                        )
                    )

                # 2. Require calls: const x = require("...")
                if ntype == "call_expression":
                    stats.calls += 1
                    fn_node = node.child_by_field_name("function")
                    fn_name = self._get_node_text(fn_node, source_bytes)
                    if fn_name:
                        call_names.append(fn_name)
                    if fn_name == "require":
                        args_node = node.child_by_field_name("arguments")
                        if args_node and args_node.children:
                            for arg in args_node.children:
                                if arg.type == "string":
                                    mod_name = self._get_node_text(arg, source_bytes).strip("\"'")
                                    stats.imports += 1
                                    imports.append(
                                        ImportSymbol(
                                            source_module=mod_name,
                                            imported_names=[],
                                            file_id=file_id,
                                            file_path=file_path,
                                            line=node.start_point[0] + 1,
                                            column=node.start_point[1],
                                            import_type="require",
                                        )
                                    )

                # 3. Functions
                if ntype in ["function_declaration", "function_expression"]:
                    name_node = node.child_by_field_name("name")
                    fn_name = self._get_node_text(name_node, source_bytes) if name_node else "anonymous"
                    is_async = any(c.type == "async" for c in node.children)
                    if is_async:
                        stats.async_functions += 1
                    stats.functions += 1

                    # Extract parameters
                    params_list: List[ParameterInfo] = []
                    params_node = node.child_by_field_name("parameters")
                    if params_node:
                        for p in params_node.children:
                            if p.type in ["identifier", "formal_parameters"]:
                                params_list.append(ParameterInfo(name=self._get_node_text(p, source_bytes)))
                            elif p.type == "assignment_pattern":
                                left = p.child_by_field_name("left")
                                right = p.child_by_field_name("right")
                                p_name = self._get_node_text(left, source_bytes)
                                p_val = self._get_node_text(right, source_bytes)
                                params_list.append(ParameterInfo(name=p_name, default_value=p_val))

                    symbols.append(
                        Symbol(
                            id=str(uuid.uuid4()),
                            name=fn_name,
                            kind="async_function" if is_async else "function",
                            file_id=file_id,
                            file_path=file_path,
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1,
                            start_column=node.start_point[1],
                            end_column=node.end_point[1],
                            nesting_level=nesting,
                            parent_symbol=parent_name,
                            is_async=is_async,
                            parameters=params_list,
                        )
                    )
                    # Recurse children with updated scope
                    for child in node.children:
                        if child.type == "statement_block":
                            traverse(child, parent_name=fn_name, nesting=nesting + 1)
                    return

                # 4. Classes
                if ntype in ["class_declaration", "class_expression"]:
                    stats.classes += 1
                    name_node = node.child_by_field_name("name")
                    class_name = self._get_node_text(name_node, source_bytes) if name_node else "AnonymousClass"

                    # Heritage / extends
                    bases = []
                    for child in node.children:
                        if child.type == "class_heritage":
                            for sc in child.children:
                                if sc.type == "identifier":
                                    bases.append(self._get_node_text(sc, source_bytes))

                    symbols.append(
                        Symbol(
                            id=str(uuid.uuid4()),
                            name=class_name,
                            kind="class",
                            file_id=file_id,
                            file_path=file_path,
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1,
                            start_column=node.start_point[1],
                            end_column=node.end_point[1],
                            nesting_level=nesting,
                            parent_symbol=parent_name,
                            metadata={"bases": bases},
                        )
                    )

                    body = node.child_by_field_name("body")
                    if body:
                        traverse(body, parent_name=class_name, nesting=nesting + 1)
                    return

                # 5. Methods inside class
                if ntype == "method_definition":
                    stats.methods += 1
                    name_node = node.child_by_field_name("name")
                    m_name = self._get_node_text(name_node, source_bytes) if name_node else "method"
                    is_async = any(c.type == "async" for c in node.children)
                    if is_async:
                        stats.async_functions += 1

                    params_list = []
                    params_node = node.child_by_field_name("parameters")
                    if params_node:
                        for p in params_node.children:
                            if p.type in ["identifier", "formal_parameters"]:
                                params_list.append(ParameterInfo(name=self._get_node_text(p, source_bytes)))

                    symbols.append(
                        Symbol(
                            id=str(uuid.uuid4()),
                            name=m_name,
                            kind="method",
                            file_id=file_id,
                            file_path=file_path,
                            start_line=node.start_point[0] + 1,
                            end_line=node.end_point[0] + 1,
                            start_column=node.start_point[1],
                            end_column=node.end_point[1],
                            nesting_level=nesting,
                            parent_symbol=parent_name,
                            is_async=is_async,
                            parameters=params_list,
                        )
                    )
                    body = node.child_by_field_name("body")
                    if body:
                        traverse(body, parent_name=f"{parent_name}.{m_name}", nesting=nesting + 1)
                    return

                # 6. Variable declarations (const, let, var, arrow functions)
                if ntype in ["variable_declaration", "lexical_declaration"]:
                    is_const = any(c.type == "const" for c in node.children)
                    for child in node.children:
                        if child.type == "variable_declarator":
                            name_node = child.child_by_field_name("name")
                            val_node = child.child_by_field_name("value")
                            v_name = self._get_node_text(name_node, source_bytes) if name_node else ""

                            if val_node and val_node.type == "arrow_function":
                                # Treat arrow function as function symbol
                                is_async = any(c.type == "async" for c in val_node.children)
                                if is_async:
                                    stats.async_functions += 1
                                stats.functions += 1

                                params_list = []
                                params_node = val_node.child_by_field_name("parameters")
                                if params_node:
                                    for p in params_node.children:
                                        if p.type in ["identifier", "formal_parameters"]:
                                            params_list.append(ParameterInfo(name=self._get_node_text(p, source_bytes)))

                                symbols.append(
                                    Symbol(
                                        id=str(uuid.uuid4()),
                                        name=v_name or "arrow_function",
                                        kind="async_function" if is_async else "function",
                                        file_id=file_id,
                                        file_path=file_path,
                                        start_line=node.start_point[0] + 1,
                                        end_line=node.end_point[0] + 1,
                                        start_column=node.start_point[1],
                                        end_column=node.end_point[1],
                                        nesting_level=nesting,
                                        parent_symbol=parent_name,
                                        is_async=is_async,
                                        parameters=params_list,
                                    )
                                )
                                body = val_node.child_by_field_name("body")
                                if body:
                                    traverse(body, parent_name=v_name, nesting=nesting + 1)
                            else:
                                if is_const:
                                    stats.constants += 1
                                else:
                                    stats.variables += 1

                                if v_name:
                                    symbols.append(
                                        Symbol(
                                            id=str(uuid.uuid4()),
                                            name=v_name,
                                            kind="constant" if is_const else "variable",
                                            file_id=file_id,
                                            file_path=file_path,
                                            start_line=node.start_point[0] + 1,
                                            end_line=node.end_point[0] + 1,
                                            start_column=node.start_point[1],
                                            end_column=node.end_point[1],
                                            nesting_level=nesting,
                                            parent_symbol=parent_name,
                                        )
                                    )

                # 7. Loops
                if ntype in ["for_statement", "for_in_statement", "for_of_statement", "while_statement", "do_statement"]:
                    stats.loops += 1

                # 8. Conditions
                if ntype in ["if_statement", "switch_statement", "ternary_expression"]:
                    stats.conditions += 1

                # Recurse general children
                for child in node.children:
                    traverse(child, parent_name=parent_name, nesting=nesting)

            traverse(root)

            # Determine parse status
            if len(diagnostics) > 0 and len(symbols) == 0:
                status = "failed"
            elif len(diagnostics) > 0:
                status = "diagnostics"
            else:
                status = "success"

            classes = [s for s in symbols if s.kind == "class"]
            functions = [s for s in symbols if s.kind in ["function", "async_function"]]
            methods = [s for s in symbols if s.kind == "method"]
            variables = [s for s in symbols if s.kind in ["variable", "constant"]]

            structure = {
                "classes": [c.model_dump() for c in classes],
                "functions": [f.model_dump() for f in functions],
                "methods": [m.model_dump() for m in methods],
                "variables": [v.model_dump() for v in variables],
                "calls": call_names[:50],
            }

            return FileAnalysis(
                analysis_id=analysis_id,
                project_id=project_id,
                file_id=file_id,
                file_path=file_path,
                language=self.language,
                parser=self.parser_name,
                status=status,
                source_hash=source_hash,
                source_size=source_size,
                analysis_timestamp=timestamp,
                statistics=stats,
                symbols=symbols,
                imports=imports,
                diagnostics=diagnostics,
                structure=structure,
            )

        except Exception as exc:
            diagnostic = DiagnosticsFactory.create(
                file_path=file_path,
                file_id=file_id,
                message=f"Parser failure: {str(exc)}",
                line=1,
                column=0,
                severity="error",
                category="parser_error",
                parser_name=self.parser_name,
                error_code="JS_PARSER_EXCEPTION",
            )
            stats = FileStatistics(lines=lines_count)
            return FileAnalysis(
                analysis_id=analysis_id,
                project_id=project_id,
                file_id=file_id,
                file_path=file_path,
                language=self.language,
                parser=self.parser_name,
                status="failed",
                source_hash=source_hash,
                source_size=source_size,
                analysis_timestamp=timestamp,
                statistics=stats,
                symbols=[],
                imports=[],
                diagnostics=[diagnostic],
                structure={},
            )
