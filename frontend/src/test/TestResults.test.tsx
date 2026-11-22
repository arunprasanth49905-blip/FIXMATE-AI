import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar } from '../components/layout/Sidebar';
import { TestResultsPage } from '../pages/TestResultsPage';
import { apiClient } from '../services/apiClient';
import { VerificationListResponse, ProjectListResponse } from '../types/api';

vi.mock('../services/apiClient', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../services/apiClient')>();
  return {
    ...actual,
    apiClient: {
      getProjects: vi.fn(),
      getVerificationHistoryList: vi.fn(),
    },
  };
});

const mockListResponse: VerificationListResponse = {
  items: [
    {
      id: 'verif-101',
      project_id: 'proj-1',
      project_name: 'Python Calculator',
      proposal_id: 'prop-1',
      rule_id: 'PY-W007',
      rule_name: 'Division by Zero',
      file_path: 'calc.py',
      overall_status: 'verified',
      syntax_status: 'passed',
      target_bug_status: 'resolved',
      regression_status: 'passed',
      pre_apply_fingerprint: 'pre-hash-1',
      post_apply_fingerprint: 'post-hash-1',
      verified_fingerprint: 'post-hash-1',
      is_stale: false,
      checks: [
        {
          name: 'applied_integrity',
          status: 'passed',
          message: 'Patch matches post-apply fingerprint.',
          details: 'Verified',
        },
        {
          name: 'syntax_verification',
          status: 'passed',
          message: 'Syntax validation passed.',
          details: 'Python AST',
        },
        {
          name: 'original_bug_resolution',
          status: 'passed',
          message: 'PY-W007 resolved.',
          details: null,
        },
        {
          name: 'regression_analysis',
          status: 'passed',
          message: '0 new findings detected.',
          details: null,
        },
        {
          name: 'change_scope_validation',
          status: 'passed',
          message: 'In scope.',
          details: null,
        },
      ],
      comparison: {
        target_rule_id: 'PY-W007',
        target_finding_status: 'resolved',
        before_count: 1,
        after_count: 0,
        resolved_count: 1,
        regression_count: 0,
        new_findings: [],
        removed_findings: [],
        unchanged_findings: [],
      },
      error_message: null,
      duration_ms: 14.5,
      created_at: '2026-11-22T08:00:00Z',
    },
    {
      id: 'verif-102',
      project_id: 'proj-2',
      project_name: 'Node Backend',
      proposal_id: 'prop-2',
      rule_id: 'JS-W002',
      rule_name: 'Empty Catch Block',
      file_path: 'server.js',
      overall_status: 'failed',
      syntax_status: 'passed',
      target_bug_status: 'resolved',
      regression_status: 'failed',
      pre_apply_fingerprint: 'pre-hash-2',
      post_apply_fingerprint: 'post-hash-2',
      verified_fingerprint: 'post-hash-2',
      is_stale: false,
      checks: [],
      comparison: {
        target_rule_id: 'JS-W002',
        target_finding_status: 'resolved',
        before_count: 1,
        after_count: 1,
        resolved_count: 1,
        regression_count: 1,
        new_findings: [
          {
            rule_id: 'JS-W009',
            rule_name: 'Undefined Reference',
            severity: 'critical',
            file_path: 'server.js',
            start_line: 10,
            end_line: 10,
            message: 'Unresolved identifier',
          },
        ],
        removed_findings: [],
        unchanged_findings: [],
      },
      error_message: 'Regression detected: 1 new critical bug',
      duration_ms: 22.1,
      created_at: '2026-11-22T08:30:00Z',
    },
  ],
  total: 2,
  page: 1,
  page_size: 15,
  total_pages: 1,
  metrics: {
    total_attempts: 2,
    verified_count: 1,
    failed_count: 1,
    partial_count: 0,
    inconclusive_count: 0,
    stale_count: 0,
  },
};

const mockProjectsResponse: ProjectListResponse = {
  projects: [
    {
      id: 'proj-1',
      name: 'Python Calculator',
      description: 'Test calc',
      language: 'python',
      file_count: 3,
      created_at: '2026-11-22T00:00:00Z',
      updated_at: '2026-11-22T00:00:00Z',
    },
    {
      id: 'proj-2',
      name: 'Node Backend',
      description: 'API server',
      language: 'javascript',
      file_count: 5,
      created_at: '2026-11-22T00:00:00Z',
      updated_at: '2026-11-22T00:00:00Z',
    },
  ],
  total: 2,
};

describe('Phase 8 UI: Test Results Sidebar Navigation & Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.getProjects).mockResolvedValue(mockProjectsResponse);
    vi.mocked(apiClient.getVerificationHistoryList).mockResolvedValue(mockListResponse);
  });

  it('renders "Test Results" in Sidebar without "Soon" badge and with active navigation', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Sidebar />
      </MemoryRouter>
    );

    const testResultsLink = screen.getByRole('link', { name: /Test Results/i });
    expect(testResultsLink).toBeInTheDocument();
    expect(testResultsLink).toHaveAttribute('href', '/test-results');

    // Confirm "Soon" badge is NOT rendered for Test Results
    const soonBadges = screen.getAllByText(/Soon/i);
    // Other items like Code Repairs, Analytics, History, Settings still have Soon
    expect(soonBadges.length).toBe(4);
    expect(testResultsLink).not.toHaveTextContent(/Soon/i);
  });

  it('renders Test Results page with overview metrics and records table', async () => {
    render(
      <MemoryRouter initialEntries={['/test-results']}>
        <TestResultsPage />
      </MemoryRouter>
    );

    // Header
    expect(screen.getByText(/Test Results & Verification Reports/i)).toBeInTheDocument();

    // Wait for metrics to load
    await waitFor(() => {
      expect(screen.getByTestId('metric-total-attempts')).toHaveTextContent('2');
      expect(screen.getByTestId('metric-verified-count')).toHaveTextContent('1');
      expect(screen.getByTestId('metric-failed-count')).toHaveTextContent('1');
    });

    // Records table rendered
    expect(screen.getByTestId('test-results-table-container')).toBeInTheDocument();
    expect(screen.getAllByText('Python Calculator').length).toBeGreaterThan(0);
    expect(screen.getByText('calc.py')).toBeInTheDocument();
    expect(screen.getAllByText('Node Backend').length).toBeGreaterThan(0);
    expect(screen.getByText('server.js')).toBeInTheDocument();
  });

  it('allows filtering by project and status', async () => {
    render(
      <MemoryRouter initialEntries={['/test-results']}>
        <TestResultsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('project-filter-select')).toBeInTheDocument();
    });

    // Select project-1
    const projectSelect = screen.getByTestId('project-filter-select');
    fireEvent.change(projectSelect, { target: { value: 'proj-1' } });

    await waitFor(() => {
      expect(apiClient.getVerificationHistoryList).toHaveBeenCalledWith(
        expect.objectContaining({
          projectId: 'proj-1',
        })
      );
    });

    // Select status 'verified'
    const statusSelect = screen.getByTestId('status-filter-select');
    fireEvent.change(statusSelect, { target: { value: 'verified' } });

    await waitFor(() => {
      expect(apiClient.getVerificationHistoryList).toHaveBeenCalledWith(
        expect.objectContaining({
          projectId: 'proj-1',
          status: 'verified',
        })
      );
    });
  });

  it('supports search by keyword or file path', async () => {
    render(
      <MemoryRouter initialEntries={['/test-results']}>
        <TestResultsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('verification-search-input')).toBeInTheDocument();
    });

    const searchInput = screen.getByTestId('verification-search-input');
    fireEvent.change(searchInput, { target: { value: 'calc.py' } });
    fireEvent.submit(searchInput.closest('form')!);

    await waitFor(() => {
      expect(apiClient.getVerificationHistoryList).toHaveBeenCalledWith(
        expect.objectContaining({
          search: 'calc.py',
        })
      );
    });
  });

  it('opens detailed verification report modal when clicking a row or "View Report"', async () => {
    render(
      <MemoryRouter initialEntries={['/test-results']}>
        <TestResultsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('view-report-btn-verif-101')).toBeInTheDocument();
    });

    // Click "View Report" button
    fireEvent.click(screen.getByTestId('view-report-btn-verif-101'));

    await waitFor(() => {
      // Modal opened
      expect(screen.getByText(/Verification Report: calc.py/i)).toBeInTheDocument();
      expect(screen.getByTestId('repair-verification-card')).toBeInTheDocument();
    });
  });

  it('renders clean empty state when no verification records exist in database', async () => {
    vi.mocked(apiClient.getVerificationHistoryList).mockResolvedValueOnce({
      items: [],
      total: 0,
      page: 1,
      page_size: 15,
      total_pages: 1,
      metrics: {
        total_attempts: 0,
        verified_count: 0,
        failed_count: 0,
        partial_count: 0,
        inconclusive_count: 0,
        stale_count: 0,
      },
    });

    render(
      <MemoryRouter initialEntries={['/test-results']}>
        <TestResultsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('test-results-empty-state')).toBeInTheDocument();
      expect(screen.getByText(/No Verification Records Yet/i)).toBeInTheDocument();
      expect(screen.getByTestId('go-to-projects-btn')).toBeInTheDocument();
      expect(screen.getByTestId('new-analysis-btn')).toBeInTheDocument();
    });
  });

  it('handles API errors gracefully with error banner and retry button', async () => {
    vi.mocked(apiClient.getVerificationHistoryList).mockRejectedValueOnce(
      new Error('Database connection failed')
    );

    render(
      <MemoryRouter initialEntries={['/test-results']}>
        <TestResultsPage />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('test-results-error-banner')).toBeInTheDocument();
      expect(screen.getByText(/Database connection failed/i)).toBeInTheDocument();
    });
  });
});
