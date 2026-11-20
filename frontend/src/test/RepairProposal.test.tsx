import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RepairProposalCard } from '../components/repair/RepairProposalCard';
import { RepairHistoryModal } from '../components/repair/RepairHistoryModal';
import { DetectionPanel } from '../components/detection/DetectionPanel';
import { RepairProposal, DetectionRunResponse } from '../types/api';
import { apiClient } from '../services/apiClient';

vi.mock('../services/apiClient');

const mockProposal: RepairProposal = {
  id: 'rep-001',
  project_id: 'proj-123',
  finding_id: 'find-001',
  root_cause_analysis_id: 'rca-001',
  rule_id: 'PY-W007',
  rule_name: 'Division by Zero',
  language: 'python',
  file_path: 'calculator.py',
  start_line: 5,
  end_line: 5,
  source_fingerprint: 'abc123sha256hash',
  is_stale: false,
  repair_status: 'suggested_not_applied',
  repair_summary: 'Replace division by zero literal with 100 percentage divisor',
  repair_explanation: 'The calculation divided by 0 directly. Fixed to divide by 100.',
  original_code: '    return price * discount / 0',
  proposed_code: '    return price * discount / 100',
  diff: '--- a/calculator.py\n+++ b/calculator.py\n@@ -5,1 +5,1 @@\n-    return price * discount / 0\n+    return price * discount / 100',
  additions: 1,
  deletions: 1,
  assumptions: ['The discount variable is a percentage between 0 and 100.'],
  confidence_score: 95.0,
  validation_status: 'passed',
  validation_details: {
    checks: [
      { name: 'source_freshness', status: 'passed', message: 'Source file SHA-256 matches proposal fingerprint.' },
      { name: 'path_security', status: 'passed', message: 'Target file path is safely confined to project root.' },
      { name: 'no_op_check', status: 'passed', message: 'Proposed fix introduces meaningful code changes.' },
      { name: 'patch_reversibility', status: 'passed', message: 'Patch can be cleanly reversed to the original source in memory.' },
      { name: 'syntax_validation', status: 'passed', message: 'Patched source passed Python AST syntax validation successfully.' },
      { name: 'zero_execution_policy', status: 'passed', message: 'Validation executed via static analysis only. Zero user code was executed.' },
    ],
    overall_status: 'passed',
    is_syntactically_valid: true,
    is_reversible: true,
    is_scope_valid: true,
    validation_errors: [],
  },
  model: 'gemini-3.5-flash-lite',
  duration_ms: 240.0,
  created_at: '2026-11-19T17:00:00Z',
  error_message: null,
};

const mockStaleProposal: RepairProposal = {
  ...mockProposal,
  id: 'rep-stale',
  is_stale: true,
  repair_status: 'stale_source',
  validation_status: 'stale_source',
  error_message: 'Source file has been modified on disk since this patch was generated.',
  validation_details: {
    checks: [
      { name: 'source_freshness', status: 'failed', message: 'Source file SHA-256 has changed.' },
    ],
    overall_status: 'failed',
    is_syntactically_valid: true,
    is_reversible: true,
    is_scope_valid: true,
    validation_errors: ['Source file modified since generation'],
  },
};

describe('RepairProposalCard Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockImplementation(() => Promise.resolve()),
      },
    });
  });

  it('renders safety banner prominently indicating original source is not modified', () => {
    render(<RepairProposalCard proposal={mockProposal} />);

    expect(screen.getByText(/PROPOSED PATCH — ORIGINAL SOURCE NOT MODIFIED/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Phase 6 Review Only/i).length).toBeGreaterThan(0);
  });

  it('renders repair summary, explanation, and metadata', () => {
    render(<RepairProposalCard proposal={mockProposal} />);

    expect(screen.getByText(mockProposal.repair_summary)).toBeInTheDocument();
    expect(screen.getByText(mockProposal.repair_explanation)).toBeInTheDocument();
    expect(screen.getByText(/gemini-3.5-flash-lite/i)).toBeInTheDocument();
    expect(screen.getByText(/240ms/i)).toBeInTheDocument();
    expect(screen.getByText('+1')).toBeInTheDocument();
    expect(screen.getByText('-1')).toBeInTheDocument();
  });

  it('renders unified diff view with added and removed line indicators', () => {
    render(<RepairProposalCard proposal={mockProposal} />);

    // In diff preview mode by default
    expect(screen.getByText(/return price \* discount \/ 0/)).toBeInTheDocument();
    expect(screen.getByText(/return price \* discount \/ 100/)).toBeInTheDocument();
  });

  it('switches between Diff Preview, Proposed Code, and Original Code tabs', () => {
    render(<RepairProposalCard proposal={mockProposal} />);

    // Click Proposed Code tab
    fireEvent.click(screen.getByRole('button', { name: /Proposed Code/i }));
    expect(screen.getByText(mockProposal.proposed_code.trim())).toBeInTheDocument();

    // Click Original Code tab
    fireEvent.click(screen.getByRole('button', { name: /Original Code/i }));
    expect(screen.getByText(mockProposal.original_code.trim())).toBeInTheDocument();

    // Switch back to Diff Preview
    fireEvent.click(screen.getByRole('button', { name: /Diff Preview/i }));
    expect(screen.getByText(/return price \* discount \/ 0/)).toBeInTheDocument();
  });

  it('allows copying proposed code and diff to clipboard', async () => {
    render(<RepairProposalCard proposal={mockProposal} />);

    // Copy diff when on diff tab
    const copyDiffBtn = screen.getByTestId('copy-diff-btn');
    fireEvent.click(copyDiffBtn);
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(mockProposal.diff);

    // Switch to proposed code tab and copy proposed code
    fireEvent.click(screen.getByRole('button', { name: /Proposed Code/i }));
    const copyCodeBtn = screen.getByTestId('copy-proposed-btn');
    fireEvent.click(copyCodeBtn);
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(mockProposal.proposed_code);
  });

  it('displays STALE PROPOSAL warning banner when source has changed', () => {
    render(<RepairProposalCard proposal={mockStaleProposal} />);

    expect(screen.getByTestId('stale-source-warning')).toBeInTheDocument();
    expect(screen.getByText(/STALE PROPOSAL — SOURCE HAS CHANGED/i)).toBeInTheDocument();
  });

  it('triggers onRegenerate and onNavigateToFile callbacks', () => {
    const handleRegenerate = vi.fn();
    const handleNavigate = vi.fn();

    render(
      <RepairProposalCard
        proposal={mockProposal}
        onRegenerate={handleRegenerate}
        onNavigateToFile={handleNavigate}
      />
    );

    // Click Regenerate button
    const regenerateBtn = screen.getByTestId('regenerate-proposal-btn');
    fireEvent.click(regenerateBtn);
    expect(handleRegenerate).toHaveBeenCalledTimes(1);

    // Click View in Editor button
    const viewEditorBtn = screen.getByTestId('view-bug-in-editor-btn');
    fireEvent.click(viewEditorBtn);
    expect(handleNavigate).toHaveBeenCalledWith('calculator.py', 5);
  });

  it('toggles validation details checklist showing each layer check', () => {
    render(<RepairProposalCard proposal={mockProposal} />);

    // Toggle validation details
    const validationToggle = screen.getByTestId('toggle-validation-btn');
    fireEvent.click(validationToggle);

    expect(screen.getByText(/source_freshness/i)).toBeInTheDocument();
    expect(screen.getByText(/path_security/i)).toBeInTheDocument();
    expect(screen.getByText(/patch_reversibility/i)).toBeInTheDocument();
    expect(screen.getByText(/syntax_validation/i)).toBeInTheDocument();
    expect(screen.getByText(/zero_execution_policy/i)).toBeInTheDocument();
  });
});

describe('RepairHistoryModal Component', () => {
  it('loads and displays repair history proposals', async () => {
    vi.mocked(apiClient.getRepairHistory).mockResolvedValueOnce({
      project_id: 'proj-123',
      total: 1,
      proposals: [mockProposal],
    });

    const handleSelect = vi.fn();
    const handleClose = vi.fn();

    render(
      <RepairHistoryModal
        isOpen={true}
        projectId="proj-123"
        onSelectProposal={handleSelect}
        onClose={handleClose}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(mockProposal.repair_summary)).toBeInTheDocument();
    });

    // Click on the proposal card
    fireEvent.click(screen.getByText(mockProposal.repair_summary));
    expect(handleSelect).toHaveBeenCalledWith(mockProposal);
  });
});

describe('DetectionPanel Phase 6 Integration', () => {
  const mockDetectionRun: DetectionRunResponse = {
    run_id: 'run-1',
    project_id: 'proj-123',
    status: 'completed_with_findings',
    engine_version: '1.0.0',
    files_scanned: 1,
    total_findings: 1,
    duration_ms: 15.0,
    created_at: '2026-11-19T10:00:00Z',
    severity_counts: { critical: 0, high: 1, medium: 0, low: 0, info: 0 },
    findings_by_category: { correctness: 1 },
    warnings: [],
    findings: [
      {
        id: 'find-001',
        project_id: 'proj-123',
        run_id: 'run-1',
        rule_id: 'PY-W007',
        rule_name: 'Division by Zero',
        severity: 'high',
        category: 'correctness',
        file_path: 'calculator.py',
        start_line: 5,
        start_column: 4,
        end_line: 5,
        end_column: 32,
        language: 'python',
        message: 'Potential division by zero detected',
        explanation: 'Direct division by literal 0',
        remediation: 'Ensure denominator is non-zero',
        evidence: 'return price * discount / 0',
        confidence: 0.98,
      },
    ],
  };

  it('triggers safe repair generation when clicking "Fix with AI"', async () => {
    vi.mocked(apiClient.generateRepair).mockResolvedValueOnce(mockProposal);

    render(
      <DetectionPanel
        projectId="proj-123"
        detection={mockDetectionRun}
        isDetecting={false}
        onRunDetection={vi.fn()}
        onClose={vi.fn()}
        onNavigateToSource={vi.fn()}
      />
    );

    const fixBtn = screen.getByTestId('repair-btn-find-001');
    expect(fixBtn).toBeInTheDocument();

    fireEvent.click(fixBtn);

    expect(apiClient.generateRepair).toHaveBeenCalledWith('proj-123', {
      finding_id: 'find-001',
    });

    await waitFor(() => {
      expect(screen.getByText(/PROPOSED PATCH — ORIGINAL SOURCE NOT MODIFIED/i)).toBeInTheDocument();
      expect(screen.getByText(mockProposal.repair_summary)).toBeInTheDocument();
    });
  });
});

describe('Phase 7 Human Approval & Controlled Patch Application Engine', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders Approve and Reject buttons for a proposed patch', () => {
    render(<RepairProposalCard proposal={mockProposal} projectId="proj-123" />);

    expect(screen.getByTestId('approve-repair-btn')).toBeInTheDocument();
    expect(screen.getByTestId('reject-repair-btn')).toBeInTheDocument();
  });

  it('approves repair proposal and transitions to approved state', async () => {
    vi.mocked(apiClient.approveRepair).mockResolvedValueOnce({
      proposal_id: 'rep-001',
      project_id: 'proj-123',
      status: 'approved',
      approved_at: '2026-11-20T10:00:00Z',
      source_fingerprint: 'abc123sha256hash',
      message: 'Repair proposal successfully approved.',
    });

    const handleUpdated = vi.fn();
    render(
      <RepairProposalCard
        proposal={mockProposal}
        projectId="proj-123"
        onProposalUpdated={handleUpdated}
      />
    );

    const approveBtn = screen.getByTestId('approve-repair-btn');
    fireEvent.click(approveBtn);

    expect(apiClient.approveRepair).toHaveBeenCalledWith('proj-123', 'rep-001');

    await waitFor(() => {
      expect(screen.getByTestId('approved-status-banner')).toBeInTheDocument();
      expect(screen.getByTestId('apply-repair-btn')).toBeInTheDocument();
      expect(handleUpdated).toHaveBeenCalledWith(
        expect.objectContaining({
          approval_status: 'approved',
          repair_status: 'approved',
        })
      );
    });
  });

  it('rejects repair proposal and displays rejected status', async () => {
    vi.mocked(apiClient.rejectRepair).mockResolvedValueOnce({
      proposal_id: 'rep-001',
      project_id: 'proj-123',
      status: 'rejected',
      rejected_at: '2026-11-20T10:00:00Z',
      message: 'Repair proposal rejected.',
    });

    const handleUpdated = vi.fn();
    render(
      <RepairProposalCard
        proposal={mockProposal}
        projectId="proj-123"
        onProposalUpdated={handleUpdated}
      />
    );

    const rejectBtn = screen.getByTestId('reject-repair-btn');
    fireEvent.click(rejectBtn);

    expect(apiClient.rejectRepair).toHaveBeenCalledWith('proj-123', 'rep-001');

    await waitFor(() => {
      expect(screen.getByTestId('rejected-status-banner')).toBeInTheDocument();
      expect(handleUpdated).toHaveBeenCalledWith(
        expect.objectContaining({
          approval_status: 'rejected',
          repair_status: 'rejected',
        })
      );
    });
  });

  it('disables Approve button and shows warning if proposal is stale', () => {
    render(<RepairProposalCard proposal={mockStaleProposal} projectId="proj-123" />);

    const approveBtn = screen.getByTestId('approve-repair-btn');
    expect(approveBtn).toBeDisabled();
    expect(screen.getByTestId('stale-source-warning')).toBeInTheDocument();
  });

  it('opens confirmation modal and applies approved repair to disk', async () => {
    const approvedProposal: RepairProposal = {
      ...mockProposal,
      approval_status: 'approved',
      repair_status: 'approved',
      approved_at: '2026-11-20T10:00:00Z',
    };

    vi.mocked(apiClient.applyRepair).mockResolvedValueOnce({
      proposal_id: 'rep-001',
      project_id: 'proj-123',
      file_path: 'calculator.py',
      status: 'applied',
      applied_at: '2026-11-20T10:05:00Z',
      backup_id: 'bak_20261120_calculator_py_001',
      backup_path: '.fixmate/backups/calculator.py.bak_001',
      pre_apply_fingerprint: 'abc123sha256hash',
      post_apply_fingerprint: 'def456sha256hash',
      syntax_validation_passed: true,
      additions: 1,
      deletions: 1,
      message: 'Repair successfully applied to calculator.py',
    });

    const handleModified = vi.fn();
    const handleUpdated = vi.fn();

    render(
      <RepairProposalCard
        proposal={approvedProposal}
        projectId="proj-123"
        onFileModified={handleModified}
        onProposalUpdated={handleUpdated}
      />
    );

    // Click Apply Approved Repair button
    const applyBtn = screen.getByTestId('apply-repair-btn');
    fireEvent.click(applyBtn);

    // Confirmation dialog should be displayed
    expect(screen.getByTestId('apply-confirmation-dialog')).toBeInTheDocument();
    expect(screen.getByText(/Confirm Patch Application/i)).toBeInTheDocument();
    expect(screen.getByText(/Automatic byte-for-byte pre-application backup/i)).toBeInTheDocument();

    // Confirm application
    const confirmBtn = screen.getByTestId('confirm-apply-btn');
    fireEvent.click(confirmBtn);

    expect(apiClient.applyRepair).toHaveBeenCalledWith('proj-123', 'rep-001', {
      confirm_application: true,
    });

    await waitFor(() => {
      expect(screen.getByTestId('applied-status-banner')).toBeInTheDocument();
      expect(screen.getAllByText(/bak_20261120_calculator_py_001/i).length).toBeGreaterThan(0);
      expect(screen.getByTestId('rollback-repair-btn')).toBeInTheDocument();
      expect(handleModified).toHaveBeenCalledWith('calculator.py');
      expect(handleUpdated).toHaveBeenCalledWith(
        expect.objectContaining({
          repair_status: 'applied',
          backup_id: 'bak_20261120_calculator_py_001',
        })
      );
    });
  });

  it('cancelling confirmation modal dismisses without applying', () => {
    const approvedProposal: RepairProposal = {
      ...mockProposal,
      approval_status: 'approved',
      repair_status: 'approved',
    };

    render(<RepairProposalCard proposal={approvedProposal} projectId="proj-123" />);

    fireEvent.click(screen.getByTestId('apply-repair-btn'));
    expect(screen.getByTestId('apply-confirmation-dialog')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('cancel-apply-modal-btn'));
    expect(screen.queryByTestId('apply-confirmation-dialog')).not.toBeInTheDocument();
    expect(apiClient.applyRepair).not.toHaveBeenCalled();
  });

  it('opens rollback modal and reverts applied patch to pre-apply backup', async () => {
    const appliedProposal: RepairProposal = {
      ...mockProposal,
      approval_status: 'approved',
      repair_status: 'applied',
      applied_at: '2026-11-20T10:05:00Z',
      backup_id: 'bak_20261120_calculator_py_001',
      pre_apply_fingerprint: 'abc123sha256hash',
      post_apply_fingerprint: 'def456sha256hash',
    };

    vi.mocked(apiClient.rollbackRepair).mockResolvedValueOnce({
      proposal_id: 'rep-001',
      project_id: 'proj-123',
      file_path: 'calculator.py',
      status: 'rolled_back',
      rollback_at: '2026-11-20T10:10:00Z',
      restored_fingerprint: 'abc123sha256hash',
      message: 'Repair rolled back successfully.',
    });

    const handleModified = vi.fn();
    const handleUpdated = vi.fn();

    render(
      <RepairProposalCard
        proposal={appliedProposal}
        projectId="proj-123"
        onFileModified={handleModified}
        onProposalUpdated={handleUpdated}
      />
    );

    // Rollback button should be visible
    const rollbackBtn = screen.getByTestId('rollback-repair-btn');
    fireEvent.click(rollbackBtn);

    // Confirmation dialog
    expect(screen.getByTestId('rollback-confirmation-dialog')).toBeInTheDocument();
    expect(screen.getByText(/Confirm Repair Rollback/i)).toBeInTheDocument();

    // Confirm rollback
    const confirmRollbackBtn = screen.getByTestId('confirm-rollback-btn');
    fireEvent.click(confirmRollbackBtn);

    expect(apiClient.rollbackRepair).toHaveBeenCalledWith('proj-123', 'rep-001');

    await waitFor(() => {
      expect(screen.getByTestId('rolled-back-status-banner')).toBeInTheDocument();
      expect(handleModified).toHaveBeenCalledWith('calculator.py');
      expect(handleUpdated).toHaveBeenCalledWith(
        expect.objectContaining({
          repair_status: 'rolled_back',
          rollback_status: 'rolled_back',
        })
      );
    });
  });

  it('toggles and displays immutable audit trail', async () => {
    vi.mocked(apiClient.getRepairAuditLog).mockResolvedValueOnce({
      proposal_id: 'rep-001',
      project_id: 'proj-123',
      total_events: 2,
      events: [
        {
          id: 'aud-1',
          proposal_id: 'rep-001',
          event_type: 'proposal_generated',
          target_file: 'calculator.py',
          source_fingerprint: 'abc123sha256hash',
          details: { model: 'gemini-3.5-flash-lite' },
          created_at: '2026-11-20T10:00:00Z',
        },
        {
          id: 'aud-2',
          proposal_id: 'rep-001',
          event_type: 'proposal_approved',
          target_file: 'calculator.py',
          source_fingerprint: 'abc123sha256hash',
          details: { approved_by: 'human_user' },
          created_at: '2026-11-20T10:02:00Z',
        },
      ],
    });

    render(<RepairProposalCard proposal={mockProposal} projectId="proj-123" />);

    const auditBtn = screen.getByTestId('toggle-audit-btn');
    fireEvent.click(auditBtn);

    expect(apiClient.getRepairAuditLog).toHaveBeenCalledWith('proj-123', 'rep-001');

    await waitFor(() => {
      expect(screen.getByTestId('audit-trail-container')).toBeInTheDocument();
      expect(screen.getByText(/proposal_generated/i)).toBeInTheDocument();
      expect(screen.getByText(/proposal_approved/i)).toBeInTheDocument();
    });
  });
});

