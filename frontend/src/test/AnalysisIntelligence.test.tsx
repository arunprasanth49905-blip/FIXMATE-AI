import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AnalysisSummaryCard } from '../components/analysis/AnalysisSummaryCard';
import { StructuralViewer } from '../components/analysis/StructuralViewer';
import { AnalysisPanel } from '../components/analysis/AnalysisPanel';
import { WorkspacePage } from '../pages/WorkspacePage';
import { NewAnalysisPage } from '../pages/NewAnalysisPage';
import { apiClient } from '../services/apiClient';
import { ProjectAnalysisResponse, FileAnalysis } from '../types/api';

// Mock Monaco Editor
vi.mock('@monaco-editor/react', () => ({
  default: ({ value, onChange }: { value: string; onChange: (val: string) => void }) => (
    <textarea
      data-testid="monaco-mock-editor"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  ),
}));

// Mock apiClient methods
vi.mock('../services/apiClient', async () => {
  const actual = await vi.importActual<typeof import('../services/apiClient')>('../services/apiClient');
  return {
    ...actual,
    apiClient: {
      getHealth: vi.fn(),
      getSystemInfo: vi.fn(),
      getAIStatus: vi.fn(),
      testAIConnection: vi.fn(),
      getProjects: vi.fn(),
      createProject: vi.fn(),
      getProject: vi.fn(),
      updateProject: vi.fn(),
      deleteProject: vi.fn(),
      getProjectFiles: vi.fn(),
      createProjectFile: vi.fn(),
      getFileContent: vi.fn(),
      saveFileContent: vi.fn(),
      renameFile: vi.fn(),
      deleteFile: vi.fn(),
      uploadFiles: vi.fn(),
      getParserStatus: vi.fn(),
      analyzeProject: vi.fn(),
      getLatestAnalysis: vi.fn(),
      getAnalysisById: vi.fn(),
      getAnalyzedFiles: vi.fn(),
      getFileAnalysis: vi.fn(),
      getAnalysisDiagnostics: vi.fn(),
    },
  };
});

const mockFileAnalysis: FileAnalysis = {
  analysis_id: 'an-1',
  project_id: 'proj-1',
  file_id: 'file-1',
  file_path: 'src/worker.py',
  language: 'Python',
  parser: 'python-ast',
  status: 'success',
  source_hash: 'abc123hash',
  source_size: 150,
  analysis_timestamp: '2026-11-19T00:00:00Z',
  statistics: {
    lines: 20,
    functions: 2,
    async_functions: 1,
    classes: 1,
    methods: 1,
    imports: 2,
    variables: 1,
    constants: 0,
    loops: 1,
    conditions: 1,
    calls: 2,
  },
  symbols: [
    {
      id: 'sym-1',
      name: 'Worker',
      kind: 'class',
      file_path: 'src/worker.py',
      start_line: 4,
      end_line: 15,
      start_column: 0,
      end_column: 12,
      nesting_level: 0,
      is_async: false,
      is_exported: true,
      metadata: { bases: ['BaseWorker'] },
    },
    {
      id: 'sym-2',
      name: 'executeTask',
      kind: 'async_function',
      file_path: 'src/worker.py',
      start_line: 8,
      end_line: 12,
      start_column: 4,
      end_column: 20,
      nesting_level: 1,
      parent_symbol: 'Worker',
      is_async: true,
      is_exported: true,
      parameters: [{ name: 'taskId', type: 'str' }],
      return_type: 'bool',
      visibility: 'public',
    },
  ],
  imports: [
    {
      source_module: 'os',
      imported_names: ['os'],
      file_path: 'src/worker.py',
      line: 1,
      column: 0,
      import_type: 'standard',
      is_type_only: false,
    },
  ],
  diagnostics: [],
  structure: {},
};

const mockProjectAnalysis: ProjectAnalysisResponse = {
  analysis_id: 'an-1',
  project_id: 'proj-1',
  status: 'completed',
  start_time: '2026-11-19T00:00:00Z',
  end_time: '2026-11-19T00:00:01Z',
  duration_ms: 125.5,
  statistics: {
    total_files: 3,
    supported_files: 3,
    parsed_files: 3,
    failed_files: 0,
    skipped_files: 0,
    python_files: 1,
    javascript_files: 1,
    typescript_files: 1,
    total_lines: 65,
    total_functions: 4,
    total_async_functions: 2,
    total_classes: 2,
    total_methods: 2,
    total_imports: 5,
    total_variables: 3,
    total_loops: 2,
    total_conditions: 2,
    total_calls: 6,
    total_diagnostics: 0,
    duration_ms: 125.5,
  },
  language_distribution: {
    Python: 1,
    JavaScript: 1,
    TypeScript: 1,
  },
  skipped_files: [],
  warnings: [],
  total_diagnostics_count: 0,
  files: [mockFileAnalysis],
};

describe('FIXMATE AI Phase 3: Code Parsing & Structural Intelligence Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('1. AnalysisSummaryCard renders parsed statistics, duration, and language breakdown', () => {
    render(<AnalysisSummaryCard analysis={mockProjectAnalysis} />);

    expect(screen.getByText('PARSING COMPLETED')).toBeInTheDocument();
    expect(screen.getByText('125.5 ms')).toBeInTheDocument();
    expect(screen.getByText('Files Parsed')).toBeInTheDocument();
    expect(screen.getByText('Functions')).toBeInTheDocument();
    expect(screen.getByText('Classes')).toBeInTheDocument();
    expect(screen.getByText('Python')).toBeInTheDocument();
    expect(screen.getByText('JavaScript')).toBeInTheDocument();
    expect(screen.getByText('TypeScript')).toBeInTheDocument();
  });

  it('2. StructuralViewer displays classes, methods, parameters, and handles navigation clicks', () => {
    const onNavigate = vi.fn();
    render(<StructuralViewer fileAnalysis={mockFileAnalysis} onNavigateToSource={onNavigate} />);

    expect(screen.getByText('src/worker.py')).toBeInTheDocument();
    expect(screen.getByText('Worker')).toBeInTheDocument();
    expect(screen.getByText('extends BaseWorker')).toBeInTheDocument();
    expect(screen.getByText('Worker.executeTask')).toBeInTheDocument();
    expect(screen.getByText('→ bool')).toBeInTheDocument();

    // Click on symbol
    fireEvent.click(screen.getByText('Worker'));
    expect(onNavigate).toHaveBeenCalledWith('src/worker.py', 4, 0);
  });

  it('3. AnalysisPanel renders tabs, filters, and triggers project analysis', () => {
    const onAnalyze = vi.fn();
    const onClose = vi.fn();

    render(
      <AnalysisPanel
        projectId="proj-1"
        analysis={mockProjectAnalysis}
        isAnalyzing={false}
        onAnalyzeProject={onAnalyze}
        onClose={onClose}
        onNavigateToSource={vi.fn()}
      />
    );

    expect(screen.getByText('Code Intelligence')).toBeInTheDocument();
    expect(screen.getByTestId('run-analysis-button')).toBeInTheDocument();

    // Click Re-Analyze button
    fireEvent.click(screen.getByTestId('run-analysis-button'));
    expect(onAnalyze).toHaveBeenCalled();

    // Switch to Files & Symbols tab
    fireEvent.click(screen.getByText(/Files & Symbols/i));
    expect(screen.getAllByText('src/worker.py').length).toBeGreaterThanOrEqual(1);

    // Switch to Diagnostics tab
    fireEvent.click(screen.getByRole('button', { name: /Diagnostics/i }));
    expect(screen.getByText(/Zero syntax errors detected/i)).toBeInTheDocument();
  });

  it('4. WorkspacePage integrates Intelligence toggle button and loads latest analysis', async () => {
    vi.mocked(apiClient.getProject).mockResolvedValueOnce({
      id: 'proj-1',
      name: 'my-service',
      description: 'Test service',
      language: 'python',
      created_at: '2026-11-19T00:00:00Z',
      updated_at: '2026-11-19T00:00:00Z',
      file_count: 1,
    });

    vi.mocked(apiClient.getProjectFiles).mockResolvedValueOnce([
      {
        id: 'file-1',
        path: 'src/worker.py',
        name: 'worker.py',
        is_directory: false,
        size: 150,
        extension: '.py',
        children: null,
      },
    ]);

    vi.mocked(apiClient.getLatestAnalysis).mockResolvedValueOnce(mockProjectAnalysis);

    render(
      <MemoryRouter initialEntries={['/projects/proj-1']}>
        <Routes>
          <Route path="/projects/:projectId" element={<WorkspacePage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('my-service')).toBeInTheDocument();
      expect(screen.getByTestId('toggle-intelligence-button')).toBeInTheDocument();
    });

    // Toggle intelligence panel
    fireEvent.click(screen.getByTestId('toggle-intelligence-button'));

    await waitFor(() => {
      expect(screen.getByText('Code Intelligence')).toBeInTheDocument();
      expect(screen.getByText('PARSING COMPLETED')).toBeInTheDocument();
    });
  });

  it('5. NewAnalysisPage allows selecting a project and running analysis', async () => {
    vi.mocked(apiClient.getProjects).mockResolvedValueOnce({
      total: 1,
      projects: [
        {
          id: 'proj-1',
          name: 'my-service',
          description: 'Test service',
          language: 'python',
          created_at: '2026-11-19T00:00:00Z',
          updated_at: '2026-11-19T00:00:00Z',
          file_count: 1,
        },
      ],
    });

    vi.mocked(apiClient.getLatestAnalysis).mockResolvedValueOnce(mockProjectAnalysis);

    render(
      <MemoryRouter initialEntries={['/analysis']}>
        <Routes>
          <Route path="/analysis" element={<NewAnalysisPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Autonomous Code Analysis Engine')).toBeInTheDocument();
      expect(screen.getByText(/my-service/)).toBeInTheDocument();
      expect(screen.getByText('PARSING COMPLETED')).toBeInTheDocument();
    });
  });
});
