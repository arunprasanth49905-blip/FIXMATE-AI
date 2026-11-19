import pytest
from app.services.parsing.python_parser import PythonParser


@pytest.fixture
def parser():
    return PythonParser()


def test_python_parser_metadata(parser):
    assert parser.language == "Python"
    assert parser.parser_name == "python-ast"
    assert ".py" in parser.supported_extensions
    assert ".pyw" in parser.supported_extensions


def test_python_parse_empty_file(parser):
    res = parser.parse("", "empty.py")
    assert res.status == "success"
    assert len(res.symbols) == 0
    assert len(res.imports) == 0
    assert res.statistics.lines == 0


def test_python_parse_functions_and_async(parser):
    code = """
def add(a: int, b: int = 0) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b

async def fetch_data(url: str, *args, **kwargs) -> dict:
    return {"status": "ok"}
"""
    res = parser.parse(code, "funcs.py")
    assert res.status == "success"
    assert res.statistics.functions == 2
    assert res.statistics.async_functions == 1
    assert len(res.symbols) == 2

    # Verify add function
    add_sym = next(s for s in res.symbols if s.name == "add")
    assert add_sym.kind == "function"
    assert add_sym.is_async is False
    assert add_sym.return_type == "int"
    assert len(add_sym.parameters) == 2
    assert add_sym.parameters[0].name == "a"
    assert add_sym.parameters[0].type == "int"
    assert add_sym.docstring == "Add two numbers."

    # Verify fetch_data async function
    fetch_sym = next(s for s in res.symbols if s.name == "fetch_data")
    assert fetch_sym.kind == "async_function"
    assert fetch_sym.is_async is True
    assert fetch_sym.return_type == "dict"
    assert any(p.name == "*args" for p in fetch_sym.parameters)
    assert any(p.name == "**kwargs" for p in fetch_sym.parameters)


def test_python_parse_classes_and_methods(parser):
    code = """
class BaseService:
    pass

class UserService(BaseService):
    def __init__(self, db_session):
        self.db = db_session

    async def get_user(self, user_id: str) -> Optional[User]:
        return None
"""
    res = parser.parse(code, "classes.py")
    assert res.status == "success"
    assert res.statistics.classes == 2
    assert res.statistics.methods == 2

    user_svc = next(s for s in res.symbols if s.name == "UserService")
    assert user_svc.kind == "class"
    assert "BaseService" in user_svc.metadata["bases"]

    get_user = next(s for s in res.symbols if s.name == "get_user")
    assert get_user.kind == "method"
    assert get_user.is_async is True
    assert get_user.parent_symbol == "UserService"


def test_python_parse_imports(parser):
    code = """
import os
import sys as system
from pathlib import Path, PurePath
from ..models import User as UserModel
"""
    res = parser.parse(code, "imports.py")
    assert res.status == "success"
    assert len(res.imports) == 4

    os_imp = next(i for i in res.imports if i.source_module == "os")
    assert os_imp.import_type == "standard"
    assert os_imp.alias is None

    sys_imp = next(i for i in res.imports if i.source_module == "sys")
    assert sys_imp.alias == "system"

    path_imp = next(i for i in res.imports if i.source_module == "pathlib")
    assert path_imp.import_type == "from_import"
    assert "Path" in path_imp.imported_names
    assert "PurePath" in path_imp.imported_names


def test_python_parse_control_flow_and_calls(parser):
    code = """
MAX_RETRIES = 5
timeout = 30

def process():
    if timeout > 0:
        for i in range(MAX_RETRIES):
            try:
                result = compute(i)
            except ValueError:
                break
"""
    res = parser.parse(code, "flow.py")
    assert res.status == "success"
    assert res.statistics.conditions == 1
    assert res.statistics.loops == 1
    assert res.statistics.constants == 1
    assert res.statistics.variables >= 1
    assert res.statistics.calls >= 2  # range(), compute()
    assert "ValueError" in res.structure["exceptions"]


def test_python_syntax_error_detection(parser):
    broken_code = """
def invalid_syntax(
    print("missing closing paren and colon"
"""
    res = parser.parse(broken_code, "broken.py")
    assert res.status == "failed"
    assert len(res.diagnostics) == 1
    diag = res.diagnostics[0]
    assert diag.severity == "error"
    assert diag.category == "syntax"
    assert diag.line >= 1
    assert "SYNTAX" in diag.error_code
