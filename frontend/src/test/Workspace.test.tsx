import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ProjectsPage } from '../pages/ProjectsPage';
import { WorkspacePage } from '../pages/WorkspacePage';
import { apiClient } from '../services/apiClient';

// Mock Monaco Editor for jsdom
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
vi.mock('../services/apiClient', () => ({
  apiClient: {
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
  },
}));

describe('FIXMATE AI Phase 2: Project Management & Code Workspace Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('1. ProjectsPage renders project list with language badges and file counts', async () => {
    vi.mocked(apiClient.getProjects).mockResolvedValueOnce({
      total: 2,
      projects: [
        {
          id: 'proj-1',
          name: 'backend-api',
          description: 'FastAPI python service',
          language: 'python',
          created_at: '2026-11-19T00:00:00Z',
          updated_at: '2026-11-19T01:00:00Z',
          file_count: 5,
        },
        {
          id: 'proj-2',
          name: 'frontend-app',
          description: 'React TS dashboard',
          language: 'javascript',
          created_at: '2026-11-19T00:00:00Z',
          updated_at: '2026-11-19T02:00:00Z',
          file_count: 8,
        },
      ],
    });

    render(
      <MemoryRouter initialEntries={['/projects']}>
        <ProjectsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('backend-api')).toBeInTheDocument();
      expect(screen.getByText('frontend-app')).toBeInTheDocument();
      expect(screen.getByText('PYTHON')).toBeInTheDocument();
      expect(screen.getByText('5 files')).toBeInTheDocument();
    });
  });

  it('2. ProjectsPage opens create project modal and creates project', async () => {
    vi.mocked(apiClient.getProjects).mockResolvedValueOnce({
      total: 0,
      projects: [],
    });

    vi.mocked(apiClient.createProject).mockResolvedValueOnce({
      id: 'proj-new',
      name: 'microservice-auth',
      description: 'Authentication server',
      language: 'python',
      created_at: '2026-11-19T03:00:00Z',
      updated_at: '2026-11-19T03:00:00Z',
      file_count: 0,
    });

    render(
      <MemoryRouter initialEntries={['/projects']}>
        <ProjectsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('create-project-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('create-project-btn'));

    expect(screen.getByText('Create New Project')).toBeInTheDocument();

    const nameInput = screen.getByPlaceholderText(/ecommerce-backend/i);
    fireEvent.change(nameInput, { target: { value: 'microservice-auth' } });

    const submitBtn = screen.getByRole('button', { name: /^create project$/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiClient.createProject).toHaveBeenCalledWith({
        name: 'microservice-auth',
        description: undefined,
        language: 'python',
      });
    });
  });

  it('3. WorkspacePage loads project details and file tree hierarchy', async () => {
    vi.mocked(apiClient.getProject).mockResolvedValueOnce({
      id: 'proj-123',
      name: 'ai-core-service',
      description: 'Core logic',
      language: 'python',
      created_at: '2026-11-19T00:00:00Z',
      updated_at: '2026-11-19T00:00:00Z',
      file_count: 2,
    });

    vi.mocked(apiClient.getProjectFiles).mockResolvedValueOnce([
      {
        id: 'file-1',
        path: 'src/main.py',
        name: 'main.py',
        is_directory: false,
        size: 120,
        extension: '.py',
        children: null,
      },
    ]);

    render(
      <MemoryRouter initialEntries={['/projects/proj-123']}>
        <Routes>
          <Route path="/projects/:projectId" element={<WorkspacePage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('ai-core-service')).toBeInTheDocument();
      expect(screen.getByText('main.py')).toBeInTheDocument();
      expect(screen.getByText('No File Open')).toBeInTheDocument();
    });
  });

  it('4. WorkspacePage opens file into tab and tracks dirty state', async () => {
    vi.mocked(apiClient.getProject).mockResolvedValueOnce({
      id: 'proj-123',
      name: 'ai-core-service',
      description: '',
      language: 'python',
      created_at: '2026-11-19T00:00:00Z',
      updated_at: '2026-11-19T00:00:00Z',
      file_count: 1,
    });

    vi.mocked(apiClient.getProjectFiles).mockResolvedValueOnce([
      {
        id: 'file-1',
        path: 'main.py',
        name: 'main.py',
        is_directory: false,
        size: 45,
        extension: '.py',
        children: null,
      },
    ]);

    vi.mocked(apiClient.getFileContent).mockResolvedValueOnce({
      id: 'file-1',
      project_id: 'proj-123',
      path: 'main.py',
      name: 'main.py',
      is_directory: false,
      size: 45,
      extension: '.py',
      content: 'print("initial content")',
      is_binary: false,
      created_at: '2026-11-19T00:00:00Z',
      updated_at: '2026-11-19T00:00:00Z',
    });

    render(
      <MemoryRouter initialEntries={['/projects/proj-123']}>
        <Routes>
          <Route path="/projects/:projectId" element={<WorkspacePage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('main.py')).toBeInTheDocument();
    });

    // Click file in explorer
    fireEvent.click(screen.getByText('main.py'));

    await waitFor(() => {
      expect(screen.getByTestId('monaco-mock-editor')).toHaveValue('print("initial content")');
      expect(screen.getByText('✓ Saved')).toBeInTheDocument();
    });

    // Modify editor content
    fireEvent.change(screen.getByTestId('monaco-mock-editor'), {
      target: { value: 'print("modified content")' },
    });

    await waitFor(() => {
      expect(screen.getByText('● Unsaved')).toBeInTheDocument();
    });
  });

  it('5. WorkspacePage saves file changes on Save action', async () => {
    vi.mocked(apiClient.getProject).mockResolvedValueOnce({
      id: 'proj-123',
      name: 'ai-core-service',
      description: '',
      language: 'python',
      created_at: '2026-11-19T00:00:00Z',
      updated_at: '2026-11-19T00:00:00Z',
      file_count: 1,
    });

    vi.mocked(apiClient.getProjectFiles).mockResolvedValue([
      {
        id: 'file-1',
        path: 'main.py',
        name: 'main.py',
        is_directory: false,
        size: 30,
        extension: '.py',
        children: null,
      },
    ]);

    vi.mocked(apiClient.getFileContent).mockResolvedValueOnce({
      id: 'file-1',
      project_id: 'proj-123',
      path: 'main.py',
      name: 'main.py',
      is_directory: false,
      size: 30,
      extension: '.py',
      content: 'original',
      is_binary: false,
      created_at: '2026-11-19T00:00:00Z',
      updated_at: '2026-11-19T00:00:00Z',
    });

    vi.mocked(apiClient.saveFileContent).mockResolvedValueOnce({
      id: 'file-1',
      project_id: 'proj-123',
      path: 'main.py',
      name: 'main.py',
      is_directory: false,
      size: 35,
      extension: '.py',
      created_at: '2026-11-19T00:00:00Z',
      updated_at: '2026-11-19T00:01:00Z',
    });

    render(
      <MemoryRouter initialEntries={['/projects/proj-123']}>
        <Routes>
          <Route path="/projects/:projectId" element={<WorkspacePage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('main.py')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('main.py'));

    await waitFor(() => {
      expect(screen.getByTestId('monaco-mock-editor')).toBeInTheDocument();
    });

    // Make dirty
    fireEvent.change(screen.getByTestId('monaco-mock-editor'), {
      target: { value: 'updated code' },
    });

    const saveBtn = screen.getByTestId('save-file-button');
    expect(saveBtn).not.toBeDisabled();

    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(apiClient.saveFileContent).toHaveBeenCalledWith('proj-123', 'file-1', 'updated code');
      expect(screen.getByText('✓ Saved')).toBeInTheDocument();
    });
  });
});
