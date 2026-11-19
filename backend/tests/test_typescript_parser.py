import pytest
from app.services.parsing.typescript_parser import TypeScriptParser


@pytest.fixture
def parser():
    return TypeScriptParser()


def test_typescript_parser_metadata(parser):
    assert parser.language == "TypeScript"
    assert parser.parser_name == "tree-sitter-typescript"
    assert ".ts" in parser.supported_extensions
    assert ".tsx" in parser.supported_extensions


def test_typescript_parse_interfaces_types_enums(parser):
    code = """
export interface UserProfile<T> {
    id: string;
    metadata: T;
}

export type UserRole = "admin" | "editor" | "viewer";

export enum AccountStatus {
    ACTIVE = "ACTIVE",
    PENDING = "PENDING",
    SUSPENDED = "SUSPENDED"
}
"""
    res = parser.parse(code, "types.ts")
    assert res.status == "success"
    assert len(res.symbols) == 3

    if_sym = next(s for s in res.symbols if s.name == "UserProfile")
    assert if_sym.kind == "interface"

    type_sym = next(s for s in res.symbols if s.name == "UserRole")
    assert type_sym.kind == "type_alias"

    enum_sym = next(s for s in res.symbols if s.name == "AccountStatus")
    assert enum_sym.kind == "enum"


def test_typescript_parse_typed_classes_and_methods(parser):
    code = """
class DataRepository<T> implements IRepository<T> {
    private items: T[] = [];

    public async findById(id: string): Promise<T | null> {
        return this.items[0] || null;
    }

    protected validate(item: T): boolean {
        return Boolean(item);
    }
}
"""
    res = parser.parse(code, "repo.ts")
    assert res.status == "success"
    assert res.statistics.classes == 1
    assert res.statistics.methods >= 2

    repo_cls = next(s for s in res.symbols if s.name == "DataRepository")
    assert repo_cls.kind == "class"

    find_method = next(s for s in res.symbols if s.name == "findById")
    assert find_method.kind == "method"
    assert find_method.is_async is True
    assert "Promise" in (find_method.return_type or "")
    assert find_method.visibility == "public"

    val_method = next(s for s in res.symbols if s.name == "validate")
    assert val_method.visibility == "protected"


def test_typescript_parse_imports_type_only(parser):
    code = """
import type { Config } from './config';
import { serviceManager } from './manager';
"""
    res = parser.parse(code, "index.ts")
    assert res.status == "success"
    assert len(res.imports) == 2

    type_imp = next(i for i in res.imports if i.source_module == "./config")
    assert type_imp.is_type_only is True

    std_imp = next(i for i in res.imports if i.source_module == "./manager")
    assert std_imp.is_type_only is False


def test_typescript_parse_tsx(parser):
    code = """
import React from 'react';

interface Props {
    title: string;
}

export const HeaderComponent: React.FC<Props> = ({ title }) => {
    return (
        <header className="header">
            <h1>{title}</h1>
        </header>
    );
};
"""
    res = parser.parse(code, "Header.tsx")
    assert res.status == "success"
    assert len(res.symbols) >= 2
    assert any(s.kind == "interface" and s.name == "Props" for s in res.symbols)
    assert any(s.name == "HeaderComponent" for s in res.symbols)


def test_typescript_syntax_error_detection(parser):
    broken_code = "interface Broken { name: string ;"
    res = parser.parse(broken_code, "broken.ts")
    assert res.status in ["diagnostics", "failed"]
    assert len(res.diagnostics) >= 1
