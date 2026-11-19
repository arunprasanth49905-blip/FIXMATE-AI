import pytest
from app.services.parsing.javascript_parser import JavaScriptParser


@pytest.fixture
def parser():
    return JavaScriptParser()


def test_javascript_parser_metadata(parser):
    assert parser.language == "JavaScript"
    assert parser.parser_name == "tree-sitter-javascript"
    assert ".js" in parser.supported_extensions
    assert ".jsx" in parser.supported_extensions
    assert ".mjs" in parser.supported_extensions


def test_javascript_parse_empty_file(parser):
    res = parser.parse("", "empty.js")
    assert res.status == "success"
    assert len(res.symbols) == 0
    assert len(res.imports) == 0


def test_javascript_parse_functions_and_arrow(parser):
    code = """
function standardFunction(a, b = 10) {
    return a + b;
}

const arrowFunc = async (x, y) => {
    return await compute(x, y);
};
"""
    res = parser.parse(code, "funcs.js")
    assert res.status == "success"
    assert res.statistics.functions == 2
    assert res.statistics.async_functions == 1

    fn_std = next(s for s in res.symbols if s.name == "standardFunction")
    assert fn_std.kind == "function"
    assert fn_std.is_async is False

    fn_arrow = next(s for s in res.symbols if s.name == "arrowFunc")
    assert fn_arrow.kind == "async_function"
    assert fn_arrow.is_async is True


def test_javascript_parse_classes_and_methods(parser):
    code = """
class Animal {
    constructor(name) {
        this.name = name;
    }
}

class Dog extends Animal {
    speak() {
        return "Woof";
    }

    async fetchBall() {
        return true;
    }
}
"""
    res = parser.parse(code, "classes.js")
    assert res.status == "success"
    assert res.statistics.classes == 2
    assert res.statistics.methods >= 2

    dog_cls = next(s for s in res.symbols if s.name == "Dog")
    assert dog_cls.kind == "class"
    assert "Animal" in dog_cls.metadata["bases"]

    fetch_method = next(s for s in res.symbols if s.name == "fetchBall")
    assert fetch_method.kind == "method"
    assert fetch_method.is_async is True


def test_javascript_parse_imports_and_require(parser):
    code = """
import React, { useState, useEffect as useEff } from 'react';
import * as utils from './utils';
const path = require('path');
"""
    res = parser.parse(code, "imports.js")
    assert res.status == "success"
    assert len(res.imports) >= 3

    react_imp = next(i for i in res.imports if i.source_module == "react")
    assert "useState" in str(react_imp.imported_names)

    path_imp = next(i for i in res.imports if i.source_module == "path")
    assert path_imp.import_type == "require"


def test_javascript_parse_control_flow(parser):
    code = """
const items = [1, 2, 3];
for (let i = 0; i < items.length; i++) {
    if (items[i] > 1) {
        console.log(items[i]);
    }
}
"""
    res = parser.parse(code, "flow.js")
    assert res.status == "success"
    assert res.statistics.loops == 1
    assert res.statistics.conditions == 1
    assert res.statistics.calls >= 1


def test_javascript_syntax_error_detection(parser):
    broken_code = "const unclosed = { a: 1, ;"
    res = parser.parse(broken_code, "broken.js")
    assert res.status in ["diagnostics", "failed"]
    assert len(res.diagnostics) >= 1
    diag = res.diagnostics[0]
    assert diag.severity == "error"
    assert diag.line >= 1
