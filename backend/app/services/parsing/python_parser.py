import ast
import hashlib
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from app.schemas.parsing import (
    FileAnalysis,
    FileStatistics,
    Symbol,
    ImportSymbol,
    ParameterInfo,
)
from app.services.parsing.base_parser import BaseParser
from app.services.parsing.syntax_diagnostics import DiagnosticsFactory


class PythonASTVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str, file_id: Optional[str] = None):
        self.file_path = file_path
        self.file_id = file_id
        self.symbols: List[Symbol] = []
        self.imports: List[ImportSymbol] = []
        self.stats = FileStatistics()
        self.call_names: List[str] = []
        self.exception_types: List[str] = []

        # Traversal context stacks
        self._scope_stack: List[str] = []
        self._class_stack: List[str] = []
        self._nesting_level: int = 0

    def _get_parent(self) -> Optional[str]:
        return self._scope_stack[-1] if self._scope_stack else None

    def _safe_unparse(self, node: Optional[ast.AST]) -> Optional[str]:
        if node is None:
            return None
        try:
            return ast.unparse(node)
        except Exception:
            return None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_function(node, is_async=True)

    def _handle_function(self, node: ast.AST, is_async: bool):
        is_method = len(self._class_stack) > 0
        kind = "method" if is_method else ("async_function" if is_async else "function")

        if is_async:
            self.stats.async_functions += 1
        if is_method:
            self.stats.methods += 1
        else:
            self.stats.functions += 1

        # Extract parameters
        params: List[ParameterInfo] = []
        args_node = getattr(node, "args", None)
        if args_node:
            # Positional / Keyword args
            for arg in args_node.args:
                type_ann = self._safe_unparse(arg.annotation)
                params.append(ParameterInfo(name=arg.arg, type=type_ann))
            # Varargs (*args)
            if args_node.vararg:
                type_ann = self._safe_unparse(args_node.vararg.annotation)
                params.append(ParameterInfo(name=f"*{args_node.vararg.arg}", type=type_ann))
            # Kwarg (**kwargs)
            if args_node.kwarg:
                type_ann = self._safe_unparse(args_node.kwarg.annotation)
                params.append(ParameterInfo(name=f"**{args_node.kwarg.arg}", type=type_ann))

        # Return annotation
        return_type = self._safe_unparse(getattr(node, "returns", None))

        # Decorators
        decorators = [self._safe_unparse(d) for d in getattr(node, "decorator_list", [])]

        # Docstring
        docstring = ast.get_docstring(node)

        symbol_id = str(uuid.uuid4())
        name = getattr(node, "name", "anonymous")

        symbol = Symbol(
            id=symbol_id,
            name=name,
            kind=kind,
            file_id=self.file_id,
            file_path=self.file_path,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            start_column=getattr(node, "col_offset", 0),
            end_column=getattr(node, "end_col_offset", 0),
            nesting_level=self._nesting_level,
            parent_symbol=self._get_parent(),
            is_async=is_async,
            is_exported=not name.startswith("_"),
            parameters=params,
            return_type=return_type,
            visibility="private" if name.startswith("__") and not name.endswith("__") else ("protected" if name.startswith("_") else "public"),
            docstring=docstring,
            metadata={"decorators": decorators, "is_method": is_method},
        )
        self.symbols.append(symbol)

        # Enter function scope
        self._scope_stack.append(name)
        self._nesting_level += 1
        self.generic_visit(node)
        self._nesting_level -= 1
        self._scope_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef):
        self.stats.classes += 1
        name = node.name

        # Bases / inheritance
        bases = [self._safe_unparse(b) for b in node.bases if b is not None]
        decorators = [self._safe_unparse(d) for d in node.decorator_list]
        docstring = ast.get_docstring(node)

        symbol_id = str(uuid.uuid4())
        symbol = Symbol(
            id=symbol_id,
            name=name,
            kind="class",
            file_id=self.file_id,
            file_path=self.file_path,
            start_line=node.lineno,
            end_line=getattr(node, "end_lineno", node.lineno),
            start_column=getattr(node, "col_offset", 0),
            end_column=getattr(node, "end_col_offset", 0),
            nesting_level=self._nesting_level,
            parent_symbol=self._get_parent(),
            is_async=False,
            is_exported=not name.startswith("_"),
            parameters=None,
            return_type=None,
            visibility="protected" if name.startswith("_") else "public",
            docstring=docstring,
            metadata={"bases": bases, "decorators": decorators},
        )
        self.symbols.append(symbol)

        # Enter class scope
        self._class_stack.append(name)
        self._scope_stack.append(name)
        self._nesting_level += 1
        self.generic_visit(node)
        self._nesting_level -= 1
        self._scope_stack.pop()
        self._class_stack.pop()

    def visit_Import(self, node: ast.Import):
        self.stats.imports += len(node.names)
        for alias in node.names:
            self.imports.append(
                ImportSymbol(
                    source_module=alias.name,
                    imported_names=[alias.name],
                    alias=alias.asname,
                    import_type="standard",
                    file_id=self.file_id,
                    file_path=self.file_path,
                    line=node.lineno,
                    column=getattr(node, "col_offset", 0),
                    is_type_only=False,
                )
            )

    def visit_ImportFrom(self, node: ast.ImportFrom):
        self.stats.imports += len(node.names)
        module = node.module or ("." * node.level)
        names = [alias.name for alias in node.names]
        aliases = {alias.name: alias.asname for alias in node.names if alias.asname}

        self.imports.append(
            ImportSymbol(
                source_module=module,
                imported_names=names,
                alias=", ".join(f"{k} as {v}" for k, v in aliases.items()) if aliases else None,
                import_type="from_import",
                file_id=self.file_id,
                file_path=self.file_path,
                line=node.lineno,
                column=getattr(node, "col_offset", 0),
                is_type_only=False,
            )
        )

    def visit_Assign(self, node: ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                is_const = name.isupper() and len(name) > 1
                if is_const:
                    self.stats.constants += 1
                else:
                    self.stats.variables += 1

                symbol = Symbol(
                    id=str(uuid.uuid4()),
                    name=name,
                    kind="constant" if is_const else "variable",
                    file_id=self.file_id,
                    file_path=self.file_path,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                    start_column=getattr(node, "col_offset", 0),
                    end_column=getattr(node, "end_col_offset", 0),
                    nesting_level=self._nesting_level,
                    parent_symbol=self._get_parent(),
                )
                self.symbols.append(symbol)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        if isinstance(node.target, ast.Name):
            name = node.target.id
            is_const = name.isupper() and len(name) > 1
            if is_const:
                self.stats.constants += 1
            else:
                self.stats.variables += 1

            type_str = self._safe_unparse(node.annotation)
            symbol = Symbol(
                id=str(uuid.uuid4()),
                name=name,
                kind="constant" if is_const else "variable",
                file_id=self.file_id,
                file_path=self.file_path,
                start_line=node.lineno,
                end_line=getattr(node, "end_lineno", node.lineno),
                start_column=getattr(node, "col_offset", 0),
                end_column=getattr(node, "end_col_offset", 0),
                nesting_level=self._nesting_level,
                parent_symbol=self._get_parent(),
                return_type=type_str,
            )
            self.symbols.append(symbol)
        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        self.stats.loops += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor):
        self.stats.loops += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        self.stats.loops += 1
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        self.stats.conditions += 1
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try):
        for handler in node.handlers:
            if handler.type:
                exc_name = self._safe_unparse(handler.type)
                if exc_name:
                    self.exception_types.append(exc_name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        self.stats.calls += 1
        call_name = self._safe_unparse(node.func)
        if call_name:
            self.call_names.append(call_name)
        self.generic_visit(node)


class PythonParser(BaseParser):
    @property
    def language(self) -> str:
        return "Python"

    @property
    def parser_name(self) -> str:
        return "python-ast"

    @property
    def supported_extensions(self) -> List[str]:
        return [".py", ".pyw"]

    def parse(
        self,
        source_code: str,
        file_path: str,
        file_id: Optional[str] = None,
        project_id: str = "",
        analysis_id: Optional[str] = None,
    ) -> FileAnalysis:
        source_hash = hashlib.sha256(source_code.encode("utf-8")).hexdigest()
        source_size = len(source_code.encode("utf-8"))
        lines_count = len(source_code.splitlines()) if source_code else 0
        timestamp = datetime.now(timezone.utc).isoformat()

        # Handle empty file
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
            tree = ast.parse(source_code, filename=file_path)
            visitor = PythonASTVisitor(file_path=file_path, file_id=file_id)
            visitor.visit(tree)
            visitor.stats.lines = lines_count

            # Organize structure
            classes = [s for s in visitor.symbols if s.kind == "class"]
            functions = [s for s in visitor.symbols if s.kind in ["function", "async_function"]]
            methods = [s for s in visitor.symbols if s.kind == "method"]
            variables = [s for s in visitor.symbols if s.kind in ["variable", "constant"]]

            structure = {
                "classes": [c.model_dump() for c in classes],
                "functions": [f.model_dump() for f in functions],
                "methods": [m.model_dump() for m in methods],
                "variables": [v.model_dump() for v in variables],
                "calls": visitor.call_names[:50],
                "exceptions": list(set(visitor.exception_types)),
            }

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
                statistics=visitor.stats,
                symbols=visitor.symbols,
                imports=visitor.imports,
                diagnostics=[],
                structure=structure,
            )

        except (SyntaxError, IndentationError) as err:
            err_msg = err.msg or "Syntax error"
            line = err.lineno or 1
            col = (err.offset - 1) if err.offset else 0
            diagnostic = DiagnosticsFactory.create(
                file_path=file_path,
                file_id=file_id,
                message=f"{err_msg}: {err.text.strip() if err.text else ''}".strip(": "),
                line=line,
                column=col,
                severity="error",
                category="syntax",
                parser_name=self.parser_name,
                error_code="PYTHON_SYNTAX_ERROR",
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
                structure={"classes": [], "functions": [], "variables": [], "imports": []},
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
                error_code="PYTHON_PARSER_EXCEPTION",
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
