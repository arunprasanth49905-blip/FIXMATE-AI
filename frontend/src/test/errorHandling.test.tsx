import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { WorkspacePage } from '../pages/WorkspacePage';
import { apiClient, parseErrorMessage, ApiClientError } from '../services/apiClient';

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
vi.mock('../services/apiClient', async () => {
  const actual = await vi.importActual<typeof import('../services/apiClient')>('../services/apiClient');
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
      getLatestAnalysis: vi.fn().mockRejectedValue(new Error('no analysis')),
    },
  };
});

describe('FIXMATE AI Phase 2: Error Handling & Security Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('parseErrorMessage utility', () => {
    it('1. Handles FastAPI validation error array with Value error prefix removal', () => {
      const err = {
        detail: [
          {
            loc: ['body', 'path'],
            msg: "Value error, Path traversal ('..') or invalid segments are strictly prohibited",
            type: 'value_error',
          },
        ],
      };
      const result = parseErrorMessage(err);
      expect(result).toBe("Path traversal ('..') or invalid segments are strictly prohibited");
      expect(result).not.toContain('[object Object]');
    });

    it('2. Handles FastAPI detail string', () => {
      const err = { detail: 'Path traversal is not allowed.' };
      expect(parseErrorMessage(err)).toBe('Path traversal is not allowed.');
    });

    it('3. Handles Axios / Fetch error object with message', () => {
      const err = { message: 'Unable to connect to backend' };
      expect(parseErrorMessage(err)).toBe('Unable to connect to backend');
    });

    it('4. Handles nested error object', () => {
      const err = { error: { message: 'Unsupported file extension.' } };
      expect(parseErrorMessage(err)).toBe('Unsupported file extension.');
    });

    it('5. Handles errors array format', () => {
      const err = { errors: [{ msg: 'File already exists.' }] };
      expect(parseErrorMessage(err)).toBe('File already exists.');
    });

    it('6. Handles ApiClientError instance', () => {
      const err = new ApiClientError('File creation failed. Please try again.', 400);
      expect(parseErrorMessage(err)).toBe('File creation failed. Please try again.');
    });

    it('7. Replaces raw [object Object] or empty object with defaultMessage', () => {
      expect(parseErrorMessage({})).toBe('An unexpected error occurred');
      expect(parseErrorMessage('[object Object]')).toBe('An unexpected error occurred');
      expect(parseErrorMessage(null, 'Custom fallback')).toBe('Custom fallback');
      expect(parseErrorMessage(undefined, 'Custom fallback')).toBe('Custom fallback');
    });
  });

  describe('WorkspacePage File Creation Error Display', () => {
    it('8. Displays readable error when malicious path is rejected without [object Object]', async () => {
      vi.mocked(apiClient.getProject).mockResolvedValueOnce({
        id: 'proj-123',
        name: 'test-project',
        description: 'Test project description',
        language: 'python',
        created_at: '2026-11-19T00:00:00Z',
        updated_at: '2026-11-19T00:00:00Z',
        file_count: 0,
      });

      vi.mocked(apiClient.getProjectFiles).mockResolvedValueOnce([]);

      // Mock creation failure with ApiClientError
      vi.mocked(apiClient.createProjectFile).mockRejectedValueOnce(
        new ApiClientError(
          "path: Path traversal ('..') or invalid segments are strictly prohibited",
          422,
          {
            detail: [
              {
                loc: ['body', 'path'],
                msg: "Value error, Path traversal ('..') or invalid segments are strictly prohibited",
              },
            ],
          }
        )
      );

      render(
        <MemoryRouter initialEntries={['/projects/proj-123']}>
          <Routes>
            <Route path="/projects/:projectId" element={<WorkspacePage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('test-project')).toBeInTheDocument();
      });

      // Open new file modal
      const newFileBtn = screen.getByTestId('new-file-button');
      fireEvent.click(newFileBtn);

      await waitFor(() => {
        expect(screen.getByTestId('file-path-input')).toBeInTheDocument();
      });

      // Enter malicious path
      fireEvent.change(screen.getByTestId('file-path-input'), {
        target: { value: '../../outside.py' },
      });

      // Submit
      fireEvent.click(screen.getByTestId('create-file-submit'));

      // Verify readable error is rendered in modal and [object Object] is absent
      await waitFor(() => {
        const errorElement = screen.getByTestId('modal-error');
        expect(errorElement).toBeInTheDocument();
        expect(errorElement.textContent).toContain("Path traversal ('..') or invalid segments are strictly prohibited");
        expect(errorElement.textContent).not.toContain('[object Object]');
      });
    });

    it('9. Regression: normal file creation succeeds for normal_test.py, test.js, and README.md', async () => {
      vi.mocked(apiClient.getProject).mockResolvedValue({
        id: 'proj-123',
        name: 'test-project',
        description: 'Test project',
        language: 'python',
        created_at: '2026-11-19T00:00:00Z',
        updated_at: '2026-11-19T00:00:00Z',
        file_count: 0,
      });

      vi.mocked(apiClient.getProjectFiles).mockResolvedValue([]);

      const testFiles = ['normal_test.py', 'test.js', 'README.md'];

      for (const fileName of testFiles) {
        vi.mocked(apiClient.createProjectFile).mockResolvedValueOnce({
          id: `file-${fileName}`,
          project_id: 'proj-123',
          path: fileName,
          name: fileName,
          is_directory: false,
          size: 0,
          extension: fileName.slice(fileName.lastIndexOf('.')),
          created_at: '2026-11-19T00:00:00Z',
          updated_at: '2026-11-19T00:00:00Z',
        });
      }

      render(
        <MemoryRouter initialEntries={['/projects/proj-123']}>
          <Routes>
            <Route path="/projects/:projectId" element={<WorkspacePage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('test-project')).toBeInTheDocument();
      });

      for (const fileName of testFiles) {
        // Open new file modal
        fireEvent.click(screen.getByTestId('new-file-button'));

        await waitFor(() => {
          expect(screen.getByTestId('file-path-input')).toBeInTheDocument();
        });

        // Enter filename
        fireEvent.change(screen.getByTestId('file-path-input'), {
          target: { value: fileName },
        });

        // Submit
        fireEvent.click(screen.getByTestId('create-file-submit'));

        await waitFor(() => {
          expect(apiClient.createProjectFile).toHaveBeenCalledWith('proj-123', {
            path: fileName,
            content: '',
            is_directory: false,
          });
        });
      }
    });
  });
});
