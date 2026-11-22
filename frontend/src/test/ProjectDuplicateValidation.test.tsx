import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ProjectsPage } from '../pages/ProjectsPage';
import { WorkspacePage } from '../pages/WorkspacePage';
import { apiClient } from '../services/apiClient';
import { normalizeProjectName, isProjectNameDuplicate } from '../utils/projectUtils';
import { Project } from '../types/api';

// Mock Monaco Editor for jsdom
vi.mock('@monaco-editor/react', () => ({
  default: () => <textarea data-testid="monaco-mock-editor" />,
}));

vi.mock('../services/apiClient', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/apiClient')>();
  return {
    ...actual,
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
  };
});

const mockExistingProjects: Project[] = [
  {
    id: 'proj-1',
    name: 'PHASE4_BUG_DETECTION_TEST',
    description: 'Python detection test',
    language: 'python',
    file_count: 1,
    is_duplicate: true,
    created_at: '2026-11-20T10:00:00Z',
    updated_at: '2026-11-20T10:00:00Z',
  },
  {
    id: 'proj-2',
    name: 'Phase4_Bug_Detection_Test',
    description: 'General detection test',
    language: 'general',
    file_count: 4,
    is_duplicate: true,
    created_at: '2026-11-21T10:00:00Z',
    updated_at: '2026-11-21T10:00:00Z',
  },
  {
    id: 'proj-3',
    name: 'Unique_Backend_Service',
    description: 'Unique service',
    language: 'typescript',
    file_count: 10,
    is_duplicate: false,
    created_at: '2026-11-22T10:00:00Z',
    updated_at: '2026-11-22T10:00:00Z',
  },
];

describe('Project Duplicate Name Validation & UX Protection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('1. Normalization Utility Tests', () => {
    it('normalizes names by trimming whitespace and lowercasing', () => {
      expect(normalizeProjectName('PHASE4_BUG_DETECTION_TEST')).toBe('phase4_bug_detection_test');
      expect(normalizeProjectName('  phase4_bug_detection_test  ')).toBe('phase4_bug_detection_test');
      expect(normalizeProjectName('Phase4_Bug_Detection_Test')).toBe('phase4_bug_detection_test');
      expect(normalizeProjectName('   ')).toBe('');
      expect(normalizeProjectName('')).toBe('');
      expect(normalizeProjectName(null as any)).toBe('');
    });

    it('identifies duplicates regardless of casing, padding, or language', () => {
      expect(isProjectNameDuplicate('phase4_bug_detection_test', mockExistingProjects)).toBe(true);
      expect(isProjectNameDuplicate('  PHASE4_BUG_DETECTION_TEST  ', mockExistingProjects)).toBe(true);
      expect(isProjectNameDuplicate('Phase4_Bug_Detection_Test', mockExistingProjects)).toBe(true);
      expect(isProjectNameDuplicate('Brand_New_Project', mockExistingProjects)).toBe(false);
    });

    it('allows a project to keep its own name during rename via excludeProjectId', () => {
      // proj-1 renaming to its own name should NOT be considered a duplicate of itself
      expect(isProjectNameDuplicate('PHASE4_BUG_DETECTION_TEST', mockExistingProjects, 'proj-1')).toBe(true); // because proj-2 also has that name in mock
      // proj-3 renaming to its own name should NOT be considered a duplicate
      expect(isProjectNameDuplicate('Unique_Backend_Service', mockExistingProjects, 'proj-3')).toBe(false);
      // proj-3 renaming to proj-1's name MUST be blocked as duplicate
      expect(isProjectNameDuplicate('PHASE4_BUG_DETECTION_TEST', mockExistingProjects, 'proj-3')).toBe(true);
    });
  });

  describe('2. ProjectsPage Create & Rename UI Validation', () => {
    it('displays duplicate warning badges for existing duplicate projects in list', async () => {
      vi.mocked(apiClient.getProjects).mockResolvedValueOnce({
        total: 3,
        projects: mockExistingProjects,
      });

      render(
        <MemoryRouter>
          <ProjectsPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('duplicate-warning-proj-1')).toBeInTheDocument();
        expect(screen.getByTestId('duplicate-warning-proj-2')).toBeInTheDocument();
        expect(screen.queryByTestId('duplicate-warning-proj-3')).not.toBeInTheDocument();
      });
    });

    it('renders duplicate name error immediately and disables submit in Create Modal', async () => {
      vi.mocked(apiClient.getProjects).mockResolvedValueOnce({
        total: 3,
        projects: mockExistingProjects,
      });

      render(
        <MemoryRouter>
          <ProjectsPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('create-project-btn')).toBeInTheDocument();
      });

      // Open modal
      fireEvent.click(screen.getByTestId('create-project-btn'));

      const nameInput = screen.getByTestId('create-project-name-input');
      const submitBtn = screen.getByTestId('submit-create-project-btn');

      // Type duplicate name (different casing)
      fireEvent.change(nameInput, { target: { value: 'phase4_bug_detection_test' } });

      // Immediate validation error appears
      expect(screen.getByTestId('create-project-duplicate-error')).toHaveTextContent(
        'Project name already exists. Choose a different project name.'
      );
      // Submit button is disabled
      expect(submitBtn).toBeDisabled();

      // Submit form: apiClient.createProject must NOT be called
      fireEvent.submit(nameInput.closest('form')!);
      expect(apiClient.createProject).not.toHaveBeenCalled();
    });

    it('displays backend duplicate error banner and preserves form inputs when backend rejects', async () => {
      vi.mocked(apiClient.getProjects).mockResolvedValueOnce({
        total: 3,
        projects: mockExistingProjects,
      });

      render(
        <MemoryRouter>
          <ProjectsPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('create-project-btn')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('create-project-btn'));

      const nameInput = screen.getByTestId('create-project-name-input');
      const descInput = screen.getByPlaceholderText(/Brief summary of the codebase/i);

      // Enter unique client name that backend rejects as duplicate (e.g. concurrent creation)
      fireEvent.change(nameInput, { target: { value: 'New_Concurrently_Taken' } });
      fireEvent.change(descInput, { target: { value: 'Preserve this description' } });

      vi.mocked(apiClient.createProject).mockRejectedValueOnce(
        new Error('Project name already exists. Choose a different project name.')
      );

      const submitBtn = screen.getByTestId('submit-create-project-btn');
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(screen.getByTestId('create-project-error-banner')).toHaveTextContent(
          'Project name already exists. Choose a different project name.'
        );
      });

      // Form inputs must remain preserved
      expect(nameInput).toHaveValue('New_Concurrently_Taken');
      expect(descInput).toHaveValue('Preserve this description');
    });

    it('allows successfully creating a unique project', async () => {
      vi.mocked(apiClient.getProjects).mockResolvedValueOnce({
        total: 3,
        projects: mockExistingProjects,
      });

      vi.mocked(apiClient.createProject).mockResolvedValueOnce({
        id: 'new-proj-999',
        name: 'Brand_New_Project',
        description: 'New unique project',
        language: 'python',
        file_count: 0,
        created_at: '2026-11-22T11:00:00Z',
        updated_at: '2026-11-22T11:00:00Z',
      });

      render(
        <MemoryRouter initialEntries={['/projects']}>
          <Routes>
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/projects/:id" element={<div data-testid="workspace-view">Workspace</div>} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('create-project-btn')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('create-project-btn'));

      const nameInput = screen.getByTestId('create-project-name-input');
      fireEvent.change(nameInput, { target: { value: 'Brand_New_Project' } });

      // No validation error
      expect(screen.queryByTestId('create-project-duplicate-error')).not.toBeInTheDocument();

      const submitBtn = screen.getByTestId('submit-create-project-btn');
      expect(submitBtn).not.toBeDisabled();

      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(apiClient.createProject).toHaveBeenCalledWith({
          name: 'Brand_New_Project',
          language: 'python',
          description: undefined,
        });
      });
    });

    it('blocks rename in ProjectsPage when renaming to an existing duplicate name', async () => {
      vi.mocked(apiClient.getProjects).mockResolvedValueOnce({
        total: 3,
        projects: mockExistingProjects,
      });

      render(
        <MemoryRouter>
          <ProjectsPage />
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByTestId('project-card-proj-3')).toBeInTheDocument();
      });

      // Find rename button for proj-3
      const card = screen.getByTestId('project-card-proj-3');
      const renameBtn = card.querySelector('button[title="Rename Project"]')!;
      fireEvent.click(renameBtn);

      const renameInput = screen.getByTestId('rename-project-name-input');
      const renameSubmitBtn = screen.getByTestId('submit-rename-project-btn');

      // Attempt to rename proj-3 to PHASE4_BUG_DETECTION_TEST
      fireEvent.change(renameInput, { target: { value: 'phase4_bug_detection_test' } });

      expect(screen.getByTestId('rename-project-duplicate-error')).toHaveTextContent(
        'Project name already exists. Choose a different project name.'
      );
      expect(renameSubmitBtn).toBeDisabled();

      fireEvent.submit(renameInput.closest('form')!);
      expect(apiClient.updateProject).not.toHaveBeenCalled();
    });
  });

  describe('3. WorkspacePage Rename Duplicate Handling', () => {
    it('displays error banner in WorkspacePage when rename is rejected by backend', async () => {
      vi.mocked(apiClient.getProject).mockResolvedValueOnce(mockExistingProjects[2]);
      vi.mocked(apiClient.getProjectFiles).mockResolvedValueOnce([]);

      render(
        <MemoryRouter initialEntries={['/projects/proj-3']}>
          <Routes>
            <Route path="/projects/:projectId" element={<WorkspacePage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Unique_Backend_Service')).toBeInTheDocument();
      });

      // Click project name in header to open rename modal
      fireEvent.click(screen.getByTitle('Click to rename project'));

      const renameInput = screen.getByTestId('workspace-rename-project-input');
      fireEvent.change(renameInput, { target: { value: 'PHASE4_BUG_DETECTION_TEST' } });

      vi.mocked(apiClient.updateProject).mockRejectedValueOnce(
        new Error('Project name already exists. Choose a different project name.')
      );

      const saveBtn = screen.getByTestId('workspace-rename-project-submit-btn');
      fireEvent.click(saveBtn);

      await waitFor(() => {
        expect(screen.getByTestId('workspace-rename-error-banner')).toHaveTextContent(
          'Project name already exists. Choose a different project name.'
        );
      });
    });
  });
});
