import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SandboxConsoleDrawer } from '../components/sandbox/SandboxConsoleDrawer';
import { RepairVerificationCard } from '../components/repair/RepairVerificationCard';
import {
  SandboxExecutionResponse,
  SandboxStatusResponse,
  VerificationReportResponse,
} from '../types/api';

vi.mock('../services/apiClient');

const mockExecutionSuccess: SandboxExecutionResponse = {
  id: 'exec-001',
  project_id: 'proj-123',
  file_path: 'calc.py',
  language: 'python',
  execution_type: 'code',
  sandbox_runtime: 'docker',
  status: 'PASSED',
  exit_code: 0,
  stdout: 'Result: 42\nCalculation complete.',
  stderr: '',
  runtime_error: null,
  timeout: false,
  duration_ms: 154,
  start_time: '2026-11-22T10:00:00Z',
  end_time: '2026-11-22T10:00:00.154Z',
  resource_limits: {
    timeout_seconds: 10,
    memory_mb: 256,
    cpus: 1.0,
    pids: 64,
    max_output_bytes: 1048576,
    network_enabled: false,
  },
  test_summary: null,
  cleanup_status: 'cleaned',
  created_at: '2026-11-22T10:00:00Z',
};

const mockExecutionTestFailure: SandboxExecutionResponse = {
  id: 'exec-002',
  project_id: 'proj-123',
  file_path: 'test_calc.py',
  language: 'python',
  execution_type: 'test',
  sandbox_runtime: 'docker',
  status: 'FAILED',
  exit_code: 1,
  stdout: '================ FAILURES ================\n___ test_divide ___\nE   ZeroDivisionError: division by zero',
  stderr: '1 failed, 2 passed in 0.25s',
  runtime_error: null,
  timeout: false,
  duration_ms: 280,
  start_time: '2026-11-22T10:05:00Z',
  end_time: '2026-11-22T10:05:00.280Z',
  resource_limits: {
    timeout_seconds: 10,
    memory_mb: 256,
    cpus: 1.0,
    pids: 64,
    max_output_bytes: 1048576,
    network_enabled: false,
  },
  test_summary: {
    total: 3,
    passed: 2,
    failed: 1,
    errors: 0,
    skipped: 0,
    framework: 'pytest',
    details: '1 failed, 2 passed in 0.25s',
  },
  cleanup_status: 'cleaned',
  created_at: '2026-11-22T10:05:00Z',
};

const mockExecutionUnavailable: SandboxExecutionResponse = {
  id: 'exec-003',
  project_id: 'proj-123',
  file_path: 'main.py',
  language: 'python',
  execution_type: 'code',
  sandbox_runtime: 'docker',
  status: 'SANDBOX_UNAVAILABLE',
  exit_code: null,
  stdout: '',
  stderr: '',
  runtime_error: 'Docker daemon is not running on the host. Isolated sandbox execution cannot proceed safely.',
  timeout: false,
  duration_ms: 12,
  start_time: '2026-11-22T10:10:00Z',
  end_time: '2026-11-22T10:10:00.012Z',
  resource_limits: null,
  test_summary: null,
  cleanup_status: 'cleaned',
  created_at: '2026-11-22T10:10:00Z',
};

const mockStatusReady: SandboxStatusResponse = {
  available: true,
  runtime: 'docker',
  version: '29.6.2',
  message: 'Docker daemon is active and responsive.',
  supported_languages: ['python', 'javascript', 'typescript'],
  security_features: ['network_isolated', 'read_only_rootfs', 'resource_limits'],
};

const mockStatusUnavailable: SandboxStatusResponse = {
  available: false,
  runtime: 'docker',
  version: null,
  message: 'Docker daemon is not running. Please start Docker Desktop to enable isolated execution.',
  supported_languages: ['python', 'javascript', 'typescript'],
  security_features: ['network_isolated', 'read_only_rootfs', 'resource_limits'],
};

const mockVerifiedReport: VerificationReportResponse = {
  id: 'verif-001',
  proposal_id: 'rep-appl-1',
  project_id: 'proj-123',
  file_path: 'calculator.py',
  overall_status: 'verified',
  syntax_status: 'passed',
  target_bug_status: 'resolved',
  regression_status: 'passed',
  pre_apply_fingerprint: 'pre-apply-hash-123',
  post_apply_fingerprint: 'post-apply-hash-456',
  verified_fingerprint: 'post-apply-hash-456',
  is_stale: false,
  checks: [],
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
  duration_ms: 85,
  created_at: '2026-11-22T10:00:00Z',
};

const mockFailedReport: VerificationReportResponse = {
  ...mockVerifiedReport,
  overall_status: 'failed',
  syntax_status: 'failed',
};

describe('Phase 9: SandboxConsoleDrawer & Runtime UI', () => {
  it('renders nothing when isOpen is false', () => {
    const { container } = render(
      <SandboxConsoleDrawer
        isOpen={false}
        onClose={vi.fn()}
        currentExecution={null}
        isLoading={false}
        history={[]}
        onSelectHistoryItem={vi.fn()}
        sandboxStatus={mockStatusReady}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders console drawer with successful execution output', () => {
    render(
      <SandboxConsoleDrawer
        isOpen={true}
        onClose={vi.fn()}
        currentExecution={mockExecutionSuccess}
        isLoading={false}
        history={[mockExecutionSuccess]}
        onSelectHistoryItem={vi.fn()}
        sandboxStatus={mockStatusReady}
      />
    );

    expect(screen.getByText('Sandbox Execution Console')).toBeDefined();
    expect(screen.getByTestId('execution-badge-passed')).toBeDefined();
    expect(screen.getByText(/exit 0/i)).toBeDefined();
    expect(screen.getByText(/Result: 42/)).toBeDefined();
    expect(screen.getByText(/Calculation complete/)).toBeDefined();
  });

  it('displays SANDBOX_UNAVAILABLE warning and runtime error callout', () => {
    render(
      <SandboxConsoleDrawer
        isOpen={true}
        onClose={vi.fn()}
        currentExecution={mockExecutionUnavailable}
        isLoading={false}
        history={[mockExecutionUnavailable]}
        onSelectHistoryItem={vi.fn()}
        sandboxStatus={mockStatusUnavailable}
      />
    );

    expect(screen.getByTestId('execution-badge-unavailable')).toBeDefined();
    expect(screen.getByText(/Docker Container Runtime Unavailable/i)).toBeDefined();
    expect(screen.getByText(/Docker daemon is not running on the host/i)).toBeDefined();
  });

  it('switches to Test Summary tab and displays test metrics', () => {
    render(
      <SandboxConsoleDrawer
        isOpen={true}
        onClose={vi.fn()}
        currentExecution={mockExecutionTestFailure}
        isLoading={false}
        history={[mockExecutionTestFailure]}
        onSelectHistoryItem={vi.fn()}
        sandboxStatus={mockStatusReady}
      />
    );

    const testTabBtn = screen.getByTestId('tab-tests');
    fireEvent.click(testTabBtn);

    expect(screen.getByTestId('test-summary-view')).toBeDefined();
    expect(screen.getByTestId('test-summary-total').textContent).toBe('3');
    expect(screen.getByTestId('test-summary-passed').textContent).toBe('2');
    expect(screen.getByTestId('test-summary-failed').textContent).toBe('1');
    expect(screen.getByText(/1 failed, 2 passed in 0.25s/)).toBeDefined();
  });

  it('switches to Security Profile tab and shows sandbox limits', () => {
    render(
      <SandboxConsoleDrawer
        isOpen={true}
        onClose={vi.fn()}
        currentExecution={mockExecutionSuccess}
        isLoading={false}
        history={[mockExecutionSuccess]}
        onSelectHistoryItem={vi.fn()}
        sandboxStatus={mockStatusReady}
      />
    );

    const secTabBtn = screen.getByTestId('tab-security');
    fireEvent.click(secTabBtn);

    expect(screen.getByTestId('security-profile-view')).toBeDefined();
    expect(screen.getByText(/Active Container Hardening Profile/i)).toBeDefined();
    expect(screen.getByText(/Network Isolation/i)).toBeDefined();
    expect(screen.getByText(/Filesystem Protection/i)).toBeDefined();
    expect(screen.getByText(/RAM: 256MB/i)).toBeDefined();
  });

  it('renders history items and allows selecting an execution record', () => {
    const onSelectMock = vi.fn();
    render(
      <SandboxConsoleDrawer
        isOpen={true}
        onClose={vi.fn()}
        currentExecution={mockExecutionSuccess}
        isLoading={false}
        history={[mockExecutionSuccess, mockExecutionTestFailure]}
        onSelectHistoryItem={onSelectMock}
        sandboxStatus={mockStatusReady}
      />
    );

    const histTabBtn = screen.getByTestId('tab-history');
    fireEvent.click(histTabBtn);

    expect(screen.getByTestId('execution-history-view')).toBeDefined();
    expect(screen.getByText('test_calc.py')).toBeDefined();

    const viewBtn = screen.getByTestId('view-history-exec-002');
    fireEvent.click(viewBtn);
    expect(onSelectMock).toHaveBeenCalledWith(mockExecutionTestFailure);
  });
});

describe('Phase 9: RepairVerificationCard Sandbox Integration', () => {
  it('renders "Run in Sandbox" button when verification is VERIFIED and callback is provided', () => {
    const onRunSandboxMock = vi.fn();
    render(
      <RepairVerificationCard
        report={mockVerifiedReport}
        projectId="proj-123"
        proposalId="rep-appl-1"
        onRunInSandbox={onRunSandboxMock}
      />
    );

    const runBtn = screen.getByTestId('run-verified-sandbox-btn');
    expect(runBtn).toBeDefined();
    expect(runBtn.textContent).toContain('Run in Sandbox');

    fireEvent.click(runBtn);
    expect(onRunSandboxMock).toHaveBeenCalledWith('calculator.py');
  });

  it('does NOT render "Run in Sandbox" button when verification FAILED', () => {
    const onRunSandboxMock = vi.fn();
    render(
      <RepairVerificationCard
        report={mockFailedReport}
        projectId="proj-123"
        proposalId="rep-appl-1"
        onRunInSandbox={onRunSandboxMock}
      />
    );

    expect(screen.queryByTestId('run-verified-sandbox-btn')).toBeNull();
  });
});
