import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RepairProposalCard } from '../components/repair/RepairProposalCard';
import { RepairVerificationCard } from '../components/repair/RepairVerificationCard';
import { RepairProposal, VerificationReportResponse } from '../types/api';
import { apiClient } from '../services/apiClient';

vi.mock('../services/apiClient');

const mockAppliedProposal: RepairProposal = {
  id: 'rep-appl-1',
  project_id: 'proj-123',
  finding_id: 'find-001',
  root_cause_analysis_id: 'rca-001',
  rule_id: 'PY-W007',
  rule_name: 'Division by Zero',
  language: 'python',
  file_path: 'calculator.py',
  start_line: 5,
  end_line: 5,
  source_fingerprint: 'pre-apply-hash-123',
  is_stale: false,
  repair_status: 'applied',
  approval_status: 'approved',
  applied_at: '2026-11-20T11:00:00Z',
  backup_id: 'bak-999',
  backup_path: '.fixmate/backups/calculator.py.bak',
  pre_apply_fingerprint: 'pre-apply-hash-123',
  post_apply_fingerprint: 'post-apply-hash-456',
  repair_summary: 'Fixed division by zero by using 100 as denominator',
  repair_explanation: 'Changed / 0 to / 100',
  original_code: 'return a / 0',
  proposed_code: 'return a / 100',
  diff: '--- a/calc.py\n+++ b/calc.py\n@@ -1,1 +1,1 @@\n-return a / 0\n+return a / 100',
  additions: 1,
  deletions: 1,
  assumptions: ['Denominator is non-zero'],
  confidence_score: 95.0,
  validation_status: 'passed',
  validation_details: {
    checks: [],
    overall_status: 'passed',
    is_syntactically_valid: true,
    is_reversible: true,
    is_scope_valid: true,
    validation_errors: [],
  },
  model: 'gemini-3.5-flash-lite',
  duration_ms: 120,
  created_at: '2026-11-20T10:55:00Z',
  error_message: null,
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
  checks: [
    {
      name: 'applied_integrity',
      status: 'passed',
      message: 'Confirmed file on disk matches the post-apply fingerprint.',
      details: 'Fingerprint match confirmed',
    },
    {
      name: 'syntax_verification',
      status: 'passed',
      message: 'Code parsed cleanly without syntax errors.',
      details: 'Parser: Python AST',
    },
    {
      name: 'original_bug_resolution',
      status: 'passed',
      message: 'Target bug PY-W007 is no longer detected.',
      details: 'PY-W007 resolved',
    },
    {
      name: 'regression_analysis',
      status: 'passed',
      message: 'Static analysis detected 0 new issues.',
      details: '0 regressions found',
    },
    {
      name: 'change_scope_validation',
      status: 'passed',
      message: 'Changes strictly confined within proposal range.',
      details: 'Range lines 5-5',
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
    removed_findings: [
      {
        rule_id: 'PY-W007',
        rule_name: 'Division by Zero',
        severity: 'critical',
        file_path: 'calculator.py',
        start_line: 5,
        end_line: 5,
        evidence: 'return a / 0',
        message: 'ZeroDivisionError will occur at runtime',
      },
    ],
    unchanged_findings: [],
  },
  duration_ms: 45.2,
  error_message: null,
  created_at: '2026-11-20T11:05:00Z',
};

const mockFailedReport: VerificationReportResponse = {
  ...mockVerifiedReport,
  id: 'verif-fail-1',
  overall_status: 'failed',
  regression_status: 'failed',
  error_message: 'Verification failed: 1 new critical/high severity regression introduced.',
  checks: [
    mockVerifiedReport.checks[0],
    mockVerifiedReport.checks[1],
    mockVerifiedReport.checks[2],
    {
      name: 'regression_analysis',
      status: 'failed',
      message: '1 critical regression detected.',
      details: 'Introduced undefined variable reference',
    },
    mockVerifiedReport.checks[4],
  ],
  comparison: {
    ...mockVerifiedReport.comparison,
    regression_count: 1,
    after_count: 1,
    new_findings: [
      {
        rule_id: 'PY-W009',
        rule_name: 'Undefined Variable Reference',
        severity: 'critical',
        file_path: 'calculator.py',
        start_line: 6,
        end_line: 6,
        evidence: 'return unknown_var',
        message: 'NameError: name unknown_var is not defined',
      },
    ],
  },
};

describe('Phase 8 Automated Verification & Repair Validation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders "Verify Repair" button when proposal is applied', () => {
    vi.mocked(apiClient.getRepairVerificationHistory).mockResolvedValueOnce({
      verifications: [],
      total: 0,
      proposal_id: 'rep-appl-1',
      project_id: 'proj-123',
    });

    render(<RepairProposalCard proposal={mockAppliedProposal} projectId="proj-123" />);

    const verifyBtn = screen.getByTestId('verify-repair-btn');
    expect(verifyBtn).toBeInTheDocument();
    expect(verifyBtn).toHaveTextContent(/Verify Repair/i);
  });

  it('does NOT render "Verify Repair" button when proposal is not yet applied', () => {
    const unappliedProposal: RepairProposal = {
      ...mockAppliedProposal,
      repair_status: 'suggested_not_applied',
      approval_status: 'pending',
    };

    render(<RepairProposalCard proposal={unappliedProposal} projectId="proj-123" />);

    expect(screen.queryByTestId('verify-repair-btn')).not.toBeInTheDocument();
  });

  it('triggers verification API call when clicking "Verify Repair" and renders verification report card', async () => {
    vi.mocked(apiClient.getRepairVerificationHistory).mockResolvedValue({
      verifications: [],
      total: 0,
      proposal_id: 'rep-appl-1',
      project_id: 'proj-123',
    });

    vi.mocked(apiClient.verifyRepair).mockResolvedValueOnce(mockVerifiedReport);

    render(<RepairProposalCard proposal={mockAppliedProposal} projectId="proj-123" />);

    const verifyBtn = screen.getByTestId('verify-repair-btn');
    fireEvent.click(verifyBtn);

    expect(apiClient.verifyRepair).toHaveBeenCalledWith('proj-123', 'rep-appl-1');

    await waitFor(() => {
      expect(screen.getByTestId('repair-verification-card')).toBeInTheDocument();
      expect(screen.getByTestId('verification-status-badge')).toHaveTextContent(/VERIFIED/i);
    });
  });

  it('renders all 5 verification checks inside the report', () => {
    render(
      <RepairVerificationCard
        report={mockVerifiedReport}
        projectId="proj-123"
        proposalId="rep-appl-1"
      />
    );

    expect(screen.getByText(/APPLIED INTEGRITY/i)).toBeInTheDocument();
    expect(screen.getByText(/SYNTAX VERIFICATION/i)).toBeInTheDocument();
    expect(screen.getByText(/ORIGINAL BUG RESOLUTION/i)).toBeInTheDocument();
    expect(screen.getByText(/REGRESSION ANALYSIS/i)).toBeInTheDocument();
    expect(screen.getByText(/CHANGE SCOPE VALIDATION/i)).toBeInTheDocument();
  });

  it('displays regression findings clearly when verification detects regressions', () => {
    render(
      <RepairVerificationCard
        report={mockFailedReport}
        projectId="proj-123"
        proposalId="rep-appl-1"
      />
    );

    expect(screen.getByTestId('verification-status-badge')).toHaveTextContent(/FAILED/i);
    expect(screen.getByTestId('regression-findings-box')).toBeInTheDocument();
    expect(screen.getByText(/PY-W009/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Undefined Variable Reference/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/return unknown_var/i)).toBeInTheDocument();
  });

  it('allows re-verification through the re-verify button', () => {
    const handleReverify = vi.fn();
    render(
      <RepairVerificationCard
        report={mockVerifiedReport}
        projectId="proj-123"
        proposalId="rep-appl-1"
        onReverify={handleReverify}
      />
    );

    const reverifyBtn = screen.getByTestId('reverify-btn');
    fireEvent.click(reverifyBtn);

    expect(handleReverify).toHaveBeenCalledTimes(1);
  });

  it('fetches and displays verification history', async () => {
    vi.mocked(apiClient.getRepairVerificationHistory).mockResolvedValueOnce({
      verifications: [mockVerifiedReport, mockFailedReport],
      total: 2,
      proposal_id: 'rep-appl-1',
      project_id: 'proj-123',
    });

    render(
      <RepairVerificationCard
        report={mockVerifiedReport}
        projectId="proj-123"
        proposalId="rep-appl-1"
      />
    );

    const historyBtn = screen.getByTestId('verification-history-btn');
    fireEvent.click(historyBtn);

    expect(apiClient.getRepairVerificationHistory).toHaveBeenCalledWith('proj-123', 'rep-appl-1');

    await waitFor(() => {
      expect(screen.getByTestId('verification-history-list')).toBeInTheDocument();
      expect(screen.getByText(/Run #2/i)).toBeInTheDocument();
      expect(screen.getByText(/Run #1/i)).toBeInTheDocument();
    });
  });
});
