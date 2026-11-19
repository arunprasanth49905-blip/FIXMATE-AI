import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  RotateCw,
  FolderOpen,
  Code2,
  Play,
} from 'lucide-react';
import { apiClient, parseErrorMessage } from '../services/apiClient';
import { Project, ProjectAnalysisResponse } from '../types/api';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';
import { Button } from '../components/common/Button';
import { AnalysisSummaryCard } from '../components/analysis/AnalysisSummaryCard';
import { StructuralViewer } from '../components/analysis/StructuralViewer';

export const NewAnalysisPage: React.FC = () => {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [isLoadingProjects, setIsLoadingProjects] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [analysis, setAnalysis] = useState<ProjectAnalysisResponse | null>(null);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);

  // Load all projects on mount
  useEffect(() => {
    const fetchProjects = async () => {
      setIsLoadingProjects(true);
      try {
        const res = await apiClient.getProjects();
        setProjects(res.projects);
        if (res.projects.length > 0) {
          setSelectedProjectId(res.projects[0].id);
        }
      } catch (err) {
        setLoadError(parseErrorMessage(err, 'Failed to load projects list.'));
      } finally {
        setIsLoadingProjects(false);
      }
    };
    fetchProjects();
  }, []);

  // When selected project changes, load its latest analysis
  useEffect(() => {
    if (!selectedProjectId) {
      setAnalysis(null);
      return;
    }

    const fetchLatest = async () => {
      setIsLoadingAnalysis(true);
      setAnalysisError(null);
      try {
        const res = await apiClient.getLatestAnalysis(selectedProjectId);
        setAnalysis(res);
        if (res.files.length > 0) {
          setSelectedFilePath(res.files[0].file_path);
        }
      } catch {
        // No analysis exists yet, normal initial state
        setAnalysis(null);
        setSelectedFilePath(null);
      } finally {
        setIsLoadingAnalysis(false);
      }
    };
    fetchLatest();
  }, [selectedProjectId]);

  const handleRunAnalysis = async () => {
    if (!selectedProjectId) return;
    setIsAnalyzing(true);
    setAnalysisError(null);
    try {
      const res = await apiClient.analyzeProject(selectedProjectId);
      setAnalysis(res);
      if (res.files.length > 0) {
        setSelectedFilePath(res.files[0].file_path);
      }
    } catch (err) {
      setAnalysisError(parseErrorMessage(err, 'Project analysis failed.'));
    } finally {
      setIsAnalyzing(false);
    }
  };

  const selectedFile = analysis?.files.find((f) => f.file_path === selectedFilePath);

  return (
    <div style={{ maxWidth: '1080px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <Link to="/" className="btn btn-secondary btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
          <ArrowLeft size={14} />
          <span>Back to Dashboard</span>
        </Link>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Badge variant="danger">PHASE 4 ACTIVE</Badge>
          <Badge variant="blue">PHASE 3 ACTIVE</Badge>
          <Badge variant="warning">PHASE 2 ROADMAP</Badge>
          <Badge variant="neutral">Deterministic Bug Detection</Badge>
        </div>
      </div>

      {/* Project Selector Card */}
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-navy-900)', marginBottom: '4px' }}>
              Autonomous Code Analysis Engine
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--color-navy-600)', margin: 0 }}>
              Parse Python, JavaScript, and TypeScript source code into AST models, extract symbols, and inspect syntax diagnostics.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {isLoadingProjects ? (
              <span style={{ fontSize: '12px', color: 'var(--color-navy-500)' }}>Loading projects...</span>
            ) : projects.length > 0 ? (
              <>
                <select
                  className="form-input"
                  value={selectedProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  style={{ minWidth: '180px', fontSize: '13px', padding: '6px 10px' }}
                  disabled={isAnalyzing || isLoadingAnalysis}
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.language})
                    </option>
                  ))}
                </select>

                <Button
                  variant="primary"
                  onClick={handleRunAnalysis}
                  disabled={isAnalyzing || isLoadingAnalysis || !selectedProjectId}
                  isLoading={isAnalyzing}
                  data-testid="start-analysis-btn"
                >
                  <RotateCw size={14} />
                  <span>{isAnalyzing ? 'Analyzing AST...' : 'Run Analysis'}</span>
                </Button>

                <Button
                  variant="secondary"
                  onClick={() => navigate(`/projects/${selectedProjectId}`)}
                  disabled={!selectedProjectId}
                  title="Open Workspace"
                >
                  <FolderOpen size={14} />
                  <span>Open Workspace</span>
                </Button>
              </>
            ) : (
              <Link to="/projects" className="btn btn-primary btn-sm">
                <span>Create a Project First</span>
              </Link>
            )}
          </div>
        </div>

        {loadError && (
          <div style={{ marginTop: '14px', padding: '10px 14px', backgroundColor: 'var(--color-red-subtle)', color: 'var(--color-red-danger)', borderRadius: '6px', fontSize: '12.5px', border: '1px solid var(--color-red-border)' }}>
            {loadError}
          </div>
        )}

        {analysisError && (
          <div style={{ marginTop: '14px', padding: '10px 14px', backgroundColor: 'var(--color-red-subtle)', color: 'var(--color-red-danger)', borderRadius: '6px', fontSize: '12.5px', border: '1px solid var(--color-red-border)' }}>
            {analysisError}
          </div>
        )}
      </Card>

      {/* Analysis Results View */}
      {isAnalyzing && (
        <Card>
          <div style={{ textAlign: 'center', padding: '40px 20px' }}>
            <div style={{ display: 'inline-block', width: '32px', height: '32px', border: '3px solid var(--color-border)', borderTopColor: 'var(--color-blue-primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite', marginBottom: '14px' }} />
            <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--color-navy-800)', marginBottom: '4px' }}>
              Analyzing Codebase AST Structure...
            </h3>
            <p style={{ fontSize: '13px', color: 'var(--color-navy-500)' }}>
              Executing static parsing across all supported files in the project workspace.
            </p>
          </div>
        </Card>
      )}

      {analysis && !isAnalyzing && (
        <>
          <Card>
            <AnalysisSummaryCard analysis={analysis} />
          </Card>

          {/* Files and AST Structural Viewer */}
          <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '20px' }}>
            {/* File List Column */}
            <Card>
              <div style={{ fontWeight: 600, fontSize: '13px', color: 'var(--color-navy-800)', marginBottom: '10px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span>Analyzed Files ({analysis.files.length})</span>
                <span style={{ fontSize: '11px', color: 'var(--color-navy-400)' }}>Select to inspect</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '500px', overflowY: 'auto' }}>
                {analysis.files.map((file) => {
                  const isSelected = selectedFilePath === file.file_path;
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
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, color: 'var(--color-navy-900)' }}>{file.file_path}</div>
                        <div style={{ fontSize: '11px', color: 'var(--color-navy-500)', marginTop: '2px' }}>
                          {file.language} · {file.symbols.length} symbols
                        </div>
                      </div>
                      {file.diagnostics.length > 0 && (
                        <Badge variant="danger">{file.diagnostics.length} err</Badge>
                      )}
                    </div>
                  );
                })}
              </div>
            </Card>

            {/* AST Structural Viewer Column */}
            <Card>
              {selectedFile ? (
                <StructuralViewer
                  fileAnalysis={selectedFile}
                  onNavigateToSource={() => navigate(`/projects/${selectedProjectId}`)}
                />
              ) : (
                <div style={{ textAlign: 'center', padding: '40px', color: 'var(--color-navy-500)', fontSize: '13px' }}>
                  Select a file from the list to view its extracted structure.
                </div>
              )}
            </Card>
          </div>
        </>
      )}

      {!analysis && !isAnalyzing && (
        <Card>
          <div style={{ textAlign: 'center', padding: '50px 20px', color: 'var(--color-navy-600)' }}>
            <Code2 size={48} style={{ color: 'var(--color-navy-300)', margin: '0 auto 16px' }} />
            <h3 style={{ fontSize: '17px', fontWeight: 600, color: 'var(--color-navy-800)', marginBottom: '6px' }}>
              No Structural Analysis Yet
            </h3>
            <p style={{ fontSize: '13.5px', color: 'var(--color-navy-500)', maxWidth: '460px', margin: '0 auto 20px', lineHeight: 1.6 }}>
              Select a project and click <strong>Run Analysis</strong> to parse your Python, JavaScript, and TypeScript codebase into structural AST representations.
            </p>
            {selectedProjectId && (
              <Button variant="primary" onClick={handleRunAnalysis}>
                <Play size={14} />
                <span>Start Project Analysis</span>
              </Button>
            )}
          </div>
        </Card>
      )}
    </div>
  );
};
