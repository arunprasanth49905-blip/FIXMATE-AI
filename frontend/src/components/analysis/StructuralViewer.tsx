import React, { useState } from 'react';
import {
  Box,
  Code2,
  ChevronDown,
  ChevronRight,
  ShieldAlert,
  ArrowRight,
  Package,
  Layers,
  Variable,
  FileText,
  AlertCircle,
} from 'lucide-react';
import { FileAnalysis } from '../../types/api';
import { Badge } from '../common/Badge';

interface StructuralViewerProps {
  fileAnalysis: FileAnalysis;
  onNavigateToSource?: (filePath: string, line: number, column: number) => void;
}

export const StructuralViewer: React.FC<StructuralViewerProps> = ({
  fileAnalysis,
  onNavigateToSource,
}) => {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    diagnostics: true,
    classes: true,
    functions: true,
    types: true,
    imports: false,
    variables: false,
  });

  const [searchFilter, setSearchFilter] = useState('');

  const toggleSection = (sec: string) => {
    setExpandedSections((prev) => ({ ...prev, [sec]: !prev[sec] }));
  };

  const { symbols, imports, diagnostics, statistics: stats, file_path, language } = fileAnalysis;

  // Filter symbols
  const filterMatch = (name: string) => {
    if (!searchFilter.trim()) return true;
    return name.toLowerCase().includes(searchFilter.toLowerCase().trim());
  };

  const classes = symbols.filter((s) => s.kind === 'class' && filterMatch(s.name));
  const interfaces = symbols.filter((s) => s.kind === 'interface' && filterMatch(s.name));
  const typesAndEnums = symbols.filter((s) => (s.kind === 'type_alias' || s.kind === 'enum') && filterMatch(s.name));
  const functions = symbols.filter((s) => (s.kind === 'function' || s.kind === 'async_function') && filterMatch(s.name));
  const methods = symbols.filter((s) => s.kind === 'method' && filterMatch(s.name));
  const variables = symbols.filter((s) => (s.kind === 'variable' || s.kind === 'constant') && filterMatch(s.name));
  const filteredImports = imports.filter((i) => filterMatch(i.source_module) || i.imported_names.some((n) => filterMatch(n)));

  const handleSymbolClick = (line: number, col: number) => {
    if (onNavigateToSource) {
      onNavigateToSource(file_path, line, col);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* File Header Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 14px',
          backgroundColor: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          borderRadius: '8px',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FileText size={16} style={{ color: 'var(--color-blue-primary)' }} />
          <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--color-navy-900)' }}>
            {file_path}
          </span>
          <Badge variant="neutral">{language}</Badge>
          {fileAnalysis.status === 'failed' && <Badge variant="danger">SYNTAX ERROR</Badge>}
          {fileAnalysis.status === 'diagnostics' && <Badge variant="warning">DIAGNOSTICS</Badge>}
        </div>

        <div style={{ fontSize: '11.5px', color: 'var(--color-navy-500)', display: 'flex', gap: '12px' }}>
          <span>{stats.lines} lines</span>
          <span>{symbols.length} symbols</span>
          <span>{imports.length} imports</span>
        </div>
      </div>

      {/* Symbol Filter Input */}
      <div>
        <input
          type="text"
          className="form-input"
          placeholder="Filter symbols, methods, or imports..."
          value={searchFilter}
          onChange={(e) => setSearchFilter(e.target.value)}
          style={{ fontSize: '12.5px', padding: '6px 10px' }}
        />
      </div>

      {/* Diagnostics Section */}
      {diagnostics.length > 0 && (
        <div style={{ border: '1px solid var(--color-red-danger)', borderRadius: '8px', overflow: 'hidden' }}>
          <div
            onClick={() => toggleSection('diagnostics')}
            style={{
              padding: '8px 12px',
              backgroundColor: 'var(--color-red-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, fontSize: '12.5px', color: 'var(--color-red-danger)' }}>
              <ShieldAlert size={14} />
              <span>Syntax Diagnostics ({diagnostics.length})</span>
            </div>
            {expandedSections.diagnostics ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </div>

          {expandedSections.diagnostics && (
            <div style={{ padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: '8px', backgroundColor: 'var(--color-surface)' }}>
              {diagnostics.map((d) => (
                <div
                  key={d.id}
                  onClick={() => handleSymbolClick(d.line, d.column)}
                  style={{
                    padding: '8px 10px',
                    borderRadius: '6px',
                    border: '1px solid var(--color-border)',
                    backgroundColor: 'var(--color-surface-subtle)',
                    cursor: 'pointer',
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between',
                    gap: '8px',
                  }}
                  title="Click to jump to line in editor"
                >
                  <div>
                    <div style={{ fontWeight: 600, color: 'var(--color-red-danger)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <AlertCircle size={13} />
                      <span>Line {d.line}:{d.column}</span>
                      <span style={{ fontSize: '10.5px', color: 'var(--color-navy-500)', fontWeight: 400 }}>[{d.parser_name}]</span>
                    </div>
                    <div style={{ color: 'var(--color-navy-800)', marginTop: '2px', fontFamily: 'var(--font-mono)', fontSize: '11.5px' }}>
                      {d.message}
                    </div>
                  </div>
                  <ArrowRight size={13} style={{ color: 'var(--color-navy-400)', marginTop: '2px', flexShrink: 0 }} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Classes Section */}
      {(classes.length > 0 || interfaces.length > 0) && (
        <div style={{ border: '1px solid var(--color-border)', borderRadius: '8px', overflow: 'hidden' }}>
          <div
            onClick={() => toggleSection('classes')}
            style={{
              padding: '8px 12px',
              backgroundColor: 'var(--color-surface-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, fontSize: '12.5px', color: 'var(--color-navy-800)' }}>
              <Box size={14} style={{ color: 'var(--color-blue-primary)' }} />
              <span>Classes & Interfaces ({classes.length + interfaces.length})</span>
            </div>
            {expandedSections.classes ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </div>

          {expandedSections.classes && (
            <div style={{ padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: '6px', backgroundColor: 'var(--color-surface)' }}>
              {classes.map((c) => (
                <div
                  key={c.id}
                  onClick={() => handleSymbolClick(c.start_line, c.start_column)}
                  style={{
                    padding: '6px 10px',
                    borderRadius: '6px',
                    border: '1px solid var(--color-border)',
                    cursor: 'pointer',
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                  title="Click to jump to line in editor"
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Badge variant="blue">class</Badge>
                    <span style={{ fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--color-navy-900)' }}>{c.name}</span>
                    {c.metadata && Array.isArray(c.metadata.bases) && c.metadata.bases.length > 0 && (
                      <span style={{ fontSize: '11px', color: 'var(--color-navy-500)' }}>
                        extends {c.metadata.bases.join(', ')}
                      </span>
                    )}
                  </div>
                  <span style={{ fontSize: '11px', color: 'var(--color-navy-400)', fontFamily: 'var(--font-mono)' }}>
                    L{c.start_line}-{c.end_line}
                  </span>
                </div>
              ))}

              {interfaces.map((i) => (
                <div
                  key={i.id}
                  onClick={() => handleSymbolClick(i.start_line, i.start_column)}
                  style={{
                    padding: '6px 10px',
                    borderRadius: '6px',
                    border: '1px solid var(--color-border)',
                    cursor: 'pointer',
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Badge variant="blue">interface</Badge>
                    <span style={{ fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--color-navy-900)' }}>{i.name}</span>
                  </div>
                  <span style={{ fontSize: '11px', color: 'var(--color-navy-400)', fontFamily: 'var(--font-mono)' }}>
                    L{i.start_line}-{i.end_line}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Functions & Methods Section */}
      {(functions.length > 0 || methods.length > 0) && (
        <div style={{ border: '1px solid var(--color-border)', borderRadius: '8px', overflow: 'hidden' }}>
          <div
            onClick={() => toggleSection('functions')}
            style={{
              padding: '8px 12px',
              backgroundColor: 'var(--color-surface-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, fontSize: '12.5px', color: 'var(--color-navy-800)' }}>
              <Layers size={14} style={{ color: 'var(--color-cyan-primary)' }} />
              <span>Functions & Methods ({functions.length + methods.length})</span>
            </div>
            {expandedSections.functions ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </div>

          {expandedSections.functions && (
            <div style={{ padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: '6px', backgroundColor: 'var(--color-surface)' }}>
              {functions.concat(methods).map((fn) => (
                <div
                  key={fn.id}
                  onClick={() => handleSymbolClick(fn.start_line, fn.start_column)}
                  style={{
                    padding: '6px 10px',
                    borderRadius: '6px',
                    border: '1px solid var(--color-border)',
                    cursor: 'pointer',
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    flexWrap: 'wrap',
                    gap: '6px',
                  }}
                  title="Click to jump to line in editor"
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                    <Badge variant={fn.is_async ? 'warning' : 'neutral'}>
                      {fn.is_async ? 'async ' : ''}{fn.kind}
                    </Badge>
                    {fn.visibility && fn.visibility !== 'public' && (
                      <Badge variant="neutral">{fn.visibility}</Badge>
                    )}
                    <span style={{ fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--color-navy-900)' }}>
                      {fn.parent_symbol ? `${fn.parent_symbol}.` : ''}{fn.name}
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--color-navy-500)', fontFamily: 'var(--font-mono)' }}>
                      ({fn.parameters ? fn.parameters.map((p) => p.type ? `${p.name}: ${p.type}` : p.name).join(', ') : ''})
                    </span>
                    {fn.return_type && (
                      <span style={{ fontSize: '11px', color: 'var(--color-blue-dark)', fontFamily: 'var(--font-mono)' }}>
                        → {fn.return_type}
                      </span>
                    )}
                  </div>
                  <span style={{ fontSize: '11px', color: 'var(--color-navy-400)', fontFamily: 'var(--font-mono)' }}>
                    L{fn.start_line}-{fn.end_line}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Types & Enums Section */}
      {typesAndEnums.length > 0 && (
        <div style={{ border: '1px solid var(--color-border)', borderRadius: '8px', overflow: 'hidden' }}>
          <div
            onClick={() => toggleSection('types')}
            style={{
              padding: '8px 12px',
              backgroundColor: 'var(--color-surface-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, fontSize: '12.5px', color: 'var(--color-navy-800)' }}>
              <Code2 size={14} style={{ color: 'var(--color-blue-primary)' }} />
              <span>Types & Enums ({typesAndEnums.length})</span>
            </div>
            {expandedSections.types ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </div>

          {expandedSections.types && (
            <div style={{ padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: '6px', backgroundColor: 'var(--color-surface)' }}>
              {typesAndEnums.map((t) => (
                <div
                  key={t.id}
                  onClick={() => handleSymbolClick(t.start_line, t.start_column)}
                  style={{
                    padding: '6px 10px',
                    borderRadius: '6px',
                    border: '1px solid var(--color-border)',
                    cursor: 'pointer',
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Badge variant="neutral">{t.kind}</Badge>
                    <span style={{ fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--color-navy-900)' }}>{t.name}</span>
                    {t.return_type && (
                      <span style={{ fontSize: '11px', color: 'var(--color-navy-500)', fontFamily: 'var(--font-mono)' }}>
                        = {t.return_type}
                      </span>
                    )}
                  </div>
                  <span style={{ fontSize: '11px', color: 'var(--color-navy-400)', fontFamily: 'var(--font-mono)' }}>
                    L{t.start_line}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Imports Section */}
      {filteredImports.length > 0 && (
        <div style={{ border: '1px solid var(--color-border)', borderRadius: '8px', overflow: 'hidden' }}>
          <div
            onClick={() => toggleSection('imports')}
            style={{
              padding: '8px 12px',
              backgroundColor: 'var(--color-surface-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, fontSize: '12.5px', color: 'var(--color-navy-800)' }}>
              <Package size={14} style={{ color: 'var(--color-navy-500)' }} />
              <span>Imports ({filteredImports.length})</span>
            </div>
            {expandedSections.imports ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </div>

          {expandedSections.imports && (
            <div style={{ padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: '6px', backgroundColor: 'var(--color-surface)' }}>
              {filteredImports.map((imp, idx) => (
                <div
                  key={idx}
                  onClick={() => handleSymbolClick(imp.line, imp.column)}
                  style={{
                    padding: '6px 10px',
                    borderRadius: '6px',
                    border: '1px solid var(--color-border)',
                    cursor: 'pointer',
                    fontSize: '11.5px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                  title="Click to jump to line in editor"
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-navy-700)' }}>from</span>
                    <span style={{ fontWeight: 600, fontFamily: 'var(--font-mono)', color: 'var(--color-blue-primary)' }}>
                      '{imp.source_module}'
                    </span>
                    {imp.imported_names.length > 0 && (
                      <span style={{ color: 'var(--color-navy-500)', fontFamily: 'var(--font-mono)' }}>
                        import {imp.imported_names.join(', ')}
                      </span>
                    )}
                    {imp.is_type_only && <Badge variant="neutral">type</Badge>}
                  </div>
                  <span style={{ fontSize: '10.5px', color: 'var(--color-navy-400)', fontFamily: 'var(--font-mono)' }}>
                    L{imp.line}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Variables Section */}
      {variables.length > 0 && (
        <div style={{ border: '1px solid var(--color-border)', borderRadius: '8px', overflow: 'hidden' }}>
          <div
            onClick={() => toggleSection('variables')}
            style={{
              padding: '8px 12px',
              backgroundColor: 'var(--color-surface-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, fontSize: '12.5px', color: 'var(--color-navy-800)' }}>
              <Variable size={14} style={{ color: 'var(--color-navy-400)' }} />
              <span>Variables & Constants ({variables.length})</span>
            </div>
            {expandedSections.variables ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </div>

          {expandedSections.variables && (
            <div style={{ padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: '6px', backgroundColor: 'var(--color-surface)' }}>
              {variables.map((v) => (
                <div
                  key={v.id}
                  onClick={() => handleSymbolClick(v.start_line, v.start_column)}
                  style={{
                    padding: '6px 10px',
                    borderRadius: '6px',
                    border: '1px solid var(--color-border)',
                    cursor: 'pointer',
                    fontSize: '11.5px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Badge variant={v.kind === 'constant' ? 'blue' : 'neutral'}>{v.kind}</Badge>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--color-navy-900)' }}>{v.name}</span>
                    {v.return_type && (
                      <span style={{ fontSize: '11px', color: 'var(--color-navy-500)', fontFamily: 'var(--font-mono)' }}>
                        : {v.return_type}
                      </span>
                    )}
                  </div>
                  <span style={{ fontSize: '11px', color: 'var(--color-navy-400)', fontFamily: 'var(--font-mono)' }}>
                    L{v.start_line}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
