import React, { useState } from 'react';
import {
  X,
  Play,
  RotateCw,
  FileCode,
  Layers,
  ShieldAlert,
  CheckCircle2,
  ArrowRight,
  Code2,
} from 'lucide-react';
import { ProjectAnalysisResponse } from '../../types/api';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { AnalysisSummaryCard } from './AnalysisSummaryCard';
import { StructuralViewer } from './StructuralViewer';

interface AnalysisPanelProps {
  projectId: string;
  analysis: ProjectAnalysisResponse | null;
  isAnalyzing: boolean;
  onAnalyzeProject: () => void;
  onClose: () => void;
  onNavigateToSource: (filePath: string, line: number, column: number) => void;
}

export const AnalysisPanel: React.FC<AnalysisPanelProps> = ({
  analysis,
  isAnalyzing,
  onAnalyzeProject,
  onClose,
  onNavigateToSource,
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'files' | 'diagnostics'>('overview');
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [fileSearch, setFileSearch] = useState('');
  const [langFilter, setLangFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const files = analysis?.files || [];

  // Filter files
  const filteredFiles = files.filter((f) => {
    if (fileSearch.trim() && !f.file_path.toLowerCase().includes(fileSearch.toLowerCase().trim())) {
      return false;
    }
    if (langFilter !== 'all' && f.language.toLowerCase() !== langFilter.toLowerCase()) {
      return false;
    }
    if (statusFilter !== 'all' && f.status.toLowerCase() !== statusFilter.toLowerCase()) {
      return false;
    }
    return true;
  });

  const selectedFileAnalysis = files.find((f) => f.file_path === selectedFilePath) || (filteredFiles.length > 0 ? filteredFiles[0] : null);

  // All diagnostics
  const allDiagnostics = files.flatMap((f) => f.diagnostics);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: 'var(--color-surface)',
        borderLeft: '1px solid var(--color-border)',
        width: '100%',
        overflow: 'hidden',
      }}
    >
      {/* Top Header */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: 'var(--color-surface-subtle)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Code2 size={18} style={{ color: 'var(--color-blue-primary)' }} />
          <span style={{ fontWeight: 700, fontSize: '14px', color: 'var(--color-navy-900)' }}>
            Code Intelligence
          </span>
          <Badge variant="blue">PHASE 3</Badge>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Button
            variant="primary"
            size="sm"
            onClick={onAnalyzeProject}
            disabled={isAnalyzing}
            isLoading={isAnalyzing}
            data-testid="run-analysis-button"
            title="Parse all supported source files and build structural model"
          >
            <RotateCw size={13} />
            <span>{isAnalyzing ? 'Analyzing AST...' : 'Analyze Codebase'}</span>
          </Button>

          <button
            type="button"
            className="icon-btn"
            onClick={onClose}
            title="Close Panel"
            style={{ padding: '4px', borderRadius: '4px' }}
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      {analysis && (
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid var(--color-border)',
            backgroundColor: 'var(--color-surface)',
            padding: '0 16px',
            gap: '16px',
          }}
        >
          <button
            type="button"
            onClick={() => setActiveTab('overview')}
            style={{
              padding: '10px 4px',
              fontSize: '12.5px',
              fontWeight: activeTab === 'overview' ? 600 : 500,
              color: activeTab === 'overview' ? 'var(--color-blue-primary)' : 'var(--color-navy-500)',
              borderBottom: activeTab === 'overview' ? '2px solid var(--color-blue-primary)' : '2px solid transparent',
              background: 'none',
              borderTop: 'none',
              borderLeft: 'none',
              borderRight: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <Layers size={14} /> Overview
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('files')}
            style={{
              padding: '10px 4px',
              fontSize: '12.5px',
              fontWeight: activeTab === 'files' ? 600 : 500,
              color: activeTab === 'files' ? 'var(--color-blue-primary)' : 'var(--color-navy-500)',
              borderBottom: activeTab === 'files' ? '2px solid var(--color-blue-primary)' : '2px solid transparent',
              background: 'none',
              borderTop: 'none',
              borderLeft: 'none',
              borderRight: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <FileCode size={14} /> Files & Symbols ({files.length})
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('diagnostics')}
            style={{
              padding: '10px 4px',
              fontSize: '12.5px',
              fontWeight: activeTab === 'diagnostics' ? 600 : 500,
              color: activeTab === 'diagnostics' ? 'var(--color-blue-primary)' : 'var(--color-navy-500)',
              borderBottom: activeTab === 'diagnostics' ? '2px solid var(--color-blue-primary)' : '2px solid transparent',
              background: 'none',
              borderTop: 'none',
              borderLeft: 'none',
              borderRight: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <ShieldAlert size={14} style={{ color: allDiagnostics.length > 0 ? 'var(--color-amber-warning)' : 'inherit' }} />
            Diagnostics ({allDiagnostics.length})
          </button>
        </div>
      )}

      {/* Main Content Area */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
        {!analysis && !isAnalyzing && (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--color-navy-600)' }}>
            <Code2 size={40} style={{ color: 'var(--color-navy-300)', margin: '0 auto 12px' }} />
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-navy-800)', marginBottom: '6px' }}>
              No Analysis Performed Yet
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-navy-500)', maxWidth: '360px', margin: '0 auto 16px', lineHeight: 1.5 }}>
              Trigger structural analysis to extract symbols, classes, functions, imports, and detect syntax errors across Python, JavaScript, and TypeScript files.
            </p>
            <Button variant="primary" size="sm" onClick={onAnalyzeProject}>
              <Play size={13} />
              <span>Run Code Intelligence</span>
            </Button>
          </div>
        )}

        {isAnalyzing && (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--color-navy-600)' }}>
            <div style={{ display: 'inline-block', width: '28px', height: '28px', border: '3px solid var(--color-border)', borderTopColor: 'var(--color-blue-primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite', marginBottom: '12px' }} />
            <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-navy-800)', marginBottom: '4px' }}>
              Parsing Workspace AST...
            </h3>
            <p style={{ fontSize: '12.5px', color: 'var(--color-navy-500)' }}>
              Analyzing syntax trees, symbols, types, and dependencies.
            </p>
          </div>
        )}

        {analysis && !isAnalyzing && (
          <>
            {/* TAB 1: OVERVIEW */}
            {activeTab === 'overview' && (
              <AnalysisSummaryCard analysis={analysis} />
            )}

            {/* TAB 2: FILES & SYMBOLS */}
            {activeTab === 'files' && (
              <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: '16px', height: '100%', minHeight: '400px' }}>
                {/* File List Column */}
                <div style={{ borderRight: '1px solid var(--color-border)', paddingRight: '12px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {/* Search and Filters */}
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Search files..."
                    value={fileSearch}
                    onChange={(e) => setFileSearch(e.target.value)}
                    style={{ fontSize: '12px', padding: '6px 8px' }}
                  />

                  <div style={{ display: 'flex', gap: '6px' }}>
                    <select
                      className="form-input"
                      value={langFilter}
                      onChange={(e) => setLangFilter(e.target.value)}
                      style={{ fontSize: '11px', padding: '4px 6px' }}
                    >
                      <option value="all">All Languages</option>
                      <option value="python">Python</option>
                      <option value="javascript">JavaScript</option>
                      <option value="typescript">TypeScript</option>
                    </select>

                    <select
                      className="form-input"
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                      style={{ fontSize: '11px', padding: '4px 6px' }}
                    >
                      <option value="all">All Status</option>
                      <option value="success">Success</option>
                      <option value="diagnostics">Diagnostics</option>
                      <option value="failed">Failed</option>
                    </select>
                  </div>

                  {/* List of Files */}
                  <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {filteredFiles.map((file) => {
                      const isSelected = selectedFileAnalysis?.file_path === file.file_path;
                      return (
                        <div
                          key={file.file_path}
                          onClick={() => setSelectedFilePath(file.file_path)}
                          style={{
                            padding: '8px 10px',
                            borderRadius: '6px',
                            border: `1px solid ${isSelected ? 'var(--color-blue-primary)' : 'var(--color-border)'}`,
                            backgroundColor: isSelected ? 'var(--color-blue-subtle)' : 'var(--color-surface)',
                            cursor: 'pointer',
                            fontSize: '12px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '2px',
                          }}
                        >
                          <div style={{ fontWeight: 600, color: 'var(--color-navy-900)', wordBreak: 'break-all' }}>
                            {file.file_path}
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', color: 'var(--color-navy-500)' }}>
                            <span>{file.language}</span>
                            <span>{file.symbols.length} syms</span>
                            {file.diagnostics.length > 0 && (
                              <span style={{ color: 'var(--color-red-danger)', fontWeight: 600 }}>
                                {file.diagnostics.length} err
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Structural Details Column */}
                <div style={{ overflowY: 'auto' }}>
                  {selectedFileAnalysis ? (
                    <StructuralViewer
                      fileAnalysis={selectedFileAnalysis}
                      onNavigateToSource={onNavigateToSource}
                    />
                  ) : (
                    <div style={{ color: 'var(--color-navy-500)', fontSize: '13px', textAlign: 'center', padding: '40px' }}>
                      Select a file on the left to view extracted symbols, classes, functions, and imports.
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 3: DIAGNOSTICS */}
            {activeTab === 'diagnostics' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-navy-800)' }}>
                  Total Syntax Diagnostics: {allDiagnostics.length}
                </div>

                {allDiagnostics.length === 0 ? (
                  <div style={{ padding: '30px', textAlign: 'center', backgroundColor: 'var(--color-green-subtle)', borderRadius: '8px', color: 'var(--color-green-success)', fontSize: '13px', fontWeight: 600 }}>
                    <CheckCircle2 size={24} style={{ margin: '0 auto 8px' }} />
                    Zero syntax errors detected across all analyzed source files!
                  </div>
                ) : (
                  allDiagnostics.map((d) => (
                    <div
                      key={d.id}
                      onClick={() => onNavigateToSource(d.file_path, d.line, d.column)}
                      style={{
                        padding: '10px 14px',
                        borderRadius: '8px',
                        border: '1px solid var(--color-red-danger)',
                        backgroundColor: 'var(--color-surface)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'flex-start',
                        justifyContent: 'space-between',
                        gap: '12px',
                      }}
                      title="Click to jump to line in code editor"
                    >
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px' }}>
                          <Badge variant="danger">SYNTAX ERROR</Badge>
                          <span style={{ fontWeight: 600, color: 'var(--color-navy-900)' }}>{d.file_path}</span>
                          <span style={{ color: 'var(--color-navy-500)', fontFamily: 'var(--font-mono)' }}>
                            Line {d.line}:{d.column}
                          </span>
                        </div>
                        <div style={{ marginTop: '6px', fontSize: '12.5px', color: 'var(--color-navy-800)', fontFamily: 'var(--font-mono)' }}>
                          {d.message}
                        </div>
                      </div>
                      <ArrowRight size={14} style={{ color: 'var(--color-navy-400)', marginTop: '4px', flexShrink: 0 }} />
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
