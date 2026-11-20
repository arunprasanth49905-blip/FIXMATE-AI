import React, { useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Copy,
  Check,
  FileCode,
  X,
  RefreshCw,
  Terminal,
  FileDiff,
  ChevronDown,
  ChevronUp,
  Cpu,
  Clock,
  Info,
  History,
  CheckSquare,
  RotateCcw,
  AlertOctagon,
  FileText,
  Loader2,
  Lock,
} from 'lucide-react';
import { RepairProposal, AuditLogEntry } from '../../types/api';
import { apiClient, parseErrorMessage } from '../../services/apiClient';

interface RepairProposalCardProps {
  proposal: RepairProposal;
  projectId?: string;
  onClose?: () => void;
  onNavigateToFile?: (path: string, line: number) => void;
  onRegenerate?: () => void;
  onOpenHistory?: () => void;
  isRegenerating?: boolean;
  onProposalUpdated?: (updated: RepairProposal) => void;
  onFileModified?: (filePath: string) => void;
}

export const RepairProposalCard: React.FC<RepairProposalCardProps> = ({
  proposal: initialProposal,
  projectId: propProjectId,
  onClose,
  onNavigateToFile,
  onRegenerate,
  onOpenHistory,
  isRegenerating = false,
  onProposalUpdated,
  onFileModified,
}) => {
  const [proposal, setProposal] = useState<RepairProposal>(initialProposal);
  const [activeTab, setActiveTab] = useState<'diff' | 'side-by-side' | 'proposed' | 'original'>('diff');
  const [copiedProposed, setCopiedProposed] = useState(false);
  const [copiedDiff, setCopiedDiff] = useState(false);
  const [showValidationDetails, setShowValidationDetails] = useState(false);
  const [showAssumptions, setShowAssumptions] = useState(true);

  // Phase 7 Action States
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [isRollingBack, setIsRollingBack] = useState(false);

  // Phase 7 Confirmation Modals
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [showRollbackModal, setShowRollbackModal] = useState(false);
  const [applyComment, setApplyComment] = useState('');

  // Phase 7 Audit Trail View
  const [showAuditTrail, setShowAuditTrail] = useState(false);
  const [auditEvents, setAuditEvents] = useState<AuditLogEntry[]>([]);
  const [isLoadingAudit, setIsLoadingAudit] = useState(false);

  // Status and Error Messages
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Sync state if initialProposal prop updates externally
  React.useEffect(() => {
    setProposal(initialProposal);
  }, [initialProposal]);

  const effectiveProjectId = propProjectId || proposal.project_id;

  const isStale = proposal.is_stale || proposal.repair_status === 'stale' || proposal.repair_status === 'stale_source';
  const isApproved = proposal.approval_status === 'approved' || proposal.repair_status === 'approved';
  const isRejected = proposal.approval_status === 'rejected' || proposal.repair_status === 'rejected';
  const isApplied = proposal.repair_status === 'applied';
  const isRolledBack = proposal.repair_status === 'rolled_back' || proposal.rollback_status === 'rolled_back';
  const isFailed = proposal.repair_status === 'failed';

  const handleCopy = (text: string, isDiff: boolean) => {
    navigator.clipboard.writeText(text);
    if (isDiff) {
      setCopiedDiff(true);
      setTimeout(() => setCopiedDiff(false), 2000);
    } else {
      setCopiedProposed(true);
      setTimeout(() => setCopiedProposed(false), 2000);
    }
  };

  // Phase 7: Approve Handler
  const handleApprove = async () => {
    if (!effectiveProjectId) return;
    setIsApproving(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await apiClient.approveRepair(effectiveProjectId, proposal.id);
      const updated: RepairProposal = {
        ...proposal,
        approval_status: 'approved',
        repair_status: 'approved',
        approved_at: res.approved_at,
      };
      setProposal(updated);
      setActionSuccess('Repair proposal successfully approved. Ready to apply to source file.');
      onProposalUpdated?.(updated);
    } catch (err: unknown) {
      setActionError(parseErrorMessage(err, 'Failed to approve repair proposal.'));
    } finally {
      setIsApproving(false);
    }
  };

  // Phase 7: Reject Handler
  const handleReject = async () => {
    if (!effectiveProjectId) return;
    setIsRejecting(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await apiClient.rejectRepair(effectiveProjectId, proposal.id);
      const updated: RepairProposal = {
        ...proposal,
        approval_status: 'rejected',
        repair_status: 'rejected',
        rejected_at: res.rejected_at,
      };
      setProposal(updated);
      setActionSuccess('Repair proposal has been rejected.');
      onProposalUpdated?.(updated);
    } catch (err: unknown) {
      setActionError(parseErrorMessage(err, 'Failed to reject repair proposal.'));
    } finally {
      setIsRejecting(false);
    }
  };

  // Phase 7: Confirm & Apply Patch Handler
  const handleConfirmApply = async () => {
    if (!effectiveProjectId) return;
    setIsApplying(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await apiClient.applyRepair(effectiveProjectId, proposal.id, {
        confirm_application: true,
        comment: applyComment.trim() || undefined,
      });

      const updated: RepairProposal = {
        ...proposal,
        repair_status: res.status as any,
        applied_at: res.applied_at || new Date().toISOString(),
        backup_id: res.backup_id,
        backup_path: res.backup_path,
        pre_apply_fingerprint: res.pre_apply_fingerprint,
        post_apply_fingerprint: res.post_apply_fingerprint,
        additions: res.additions,
        deletions: res.deletions,
      };

      setProposal(updated);
      setShowApplyModal(false);
      setApplyComment('');

      if (res.status === 'applied') {
        setActionSuccess(`Patch successfully applied to ${proposal.file_path}. Backup created (${res.backup_id}). Syntax validated.`);
        onProposalUpdated?.(updated);
        onFileModified?.(proposal.file_path);
      } else {
        setActionError(`Patch application failed: ${res.error || 'Unknown error'}. Recovery status: ${res.recovery_succeeded ? 'Original file restored' : 'Manual inspection required'}.`);
      }
    } catch (err: unknown) {
      setActionError(parseErrorMessage(err, 'Failed to apply repair patch.'));
    } finally {
      setIsApplying(false);
    }
  };

  // Phase 7: Confirm & Rollback Patch Handler
  const handleConfirmRollback = async () => {
    if (!effectiveProjectId) return;
    setIsRollingBack(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const res = await apiClient.rollbackRepair(effectiveProjectId, proposal.id);
      const updated: RepairProposal = {
        ...proposal,
        repair_status: 'rolled_back',
        rollback_status: 'rolled_back',
        rollback_at: res.rollback_at,
      };
      setProposal(updated);
      setShowRollbackModal(false);
      setActionSuccess(`Repair rolled back successfully. Restored ${proposal.file_path} to original state.`);
      onProposalUpdated?.(updated);
      onFileModified?.(proposal.file_path);
    } catch (err: unknown) {
      setActionError(parseErrorMessage(err, 'Failed to rollback repair patch.'));
    } finally {
      setIsRollingBack(false);
    }
  };

  // Phase 7: Fetch and Toggle Audit Trail
  const handleToggleAuditTrail = async () => {
    if (!showAuditTrail && effectiveProjectId) {
      setIsLoadingAudit(true);
      try {
        const historyRes = await apiClient.getRepairAuditLog(effectiveProjectId, proposal.id);
        setAuditEvents(historyRes.events || []);
      } catch (err: unknown) {
        setActionError(parseErrorMessage(err, 'Failed to fetch audit log trail.'));
      } finally {
        setIsLoadingAudit(false);
      }
    }
    setShowAuditTrail(!showAuditTrail);
  };

  const renderDiffLines = (diffText: string) => {
    if (!diffText || !diffText.trim()) {
      return (
        <div style={{ padding: '16px', color: '#94a3b8', fontStyle: 'italic', textAlign: 'center' }}>
          No diff lines available for this proposal.
        </div>
      );
    }

    const lines = diffText.split('\n');
    return (
      <div style={{ fontFamily: 'var(--font-mono, monospace)', fontSize: '11.5px', lineHeight: 1.5 }}>
        {lines.map((line, idx) => {
          let bg = 'transparent';
          let color = '#cbd5e1';
          let borderLeft = '3px solid transparent';

          if (line.startsWith('+++') || line.startsWith('---')) {
            color = '#94a3b8';
            bg = 'rgba(255, 255, 255, 0.03)';
          } else if (line.startsWith('@@')) {
            color = '#38bdf8';
            bg = 'rgba(56, 189, 248, 0.08)';
            borderLeft = '3px solid #38bdf8';
          } else if (line.startsWith('+')) {
            color = '#86efac';
            bg = 'rgba(34, 197, 94, 0.15)';
            borderLeft = '3px solid #22c55e';
          } else if (line.startsWith('-')) {
            color = '#fca5a5';
            bg = 'rgba(239, 68, 68, 0.15)';
            borderLeft = '3px solid #ef4444';
          }

          return (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                backgroundColor: bg,
                color: color,
                borderLeft: borderLeft,
                padding: '1px 8px',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}
            >
              <span
                style={{
                  width: '32px',
                  color: '#64748b',
                  userSelect: 'none',
                  flexShrink: 0,
                  fontSize: '10px',
                  textAlign: 'right',
                  paddingRight: '8px',
                }}
              >
                {idx + 1}
              </span>
              <span style={{ flex: 1 }}>{line}</span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--color-surface, #ffffff)',
        border: isApplied
          ? '1px solid #10b981'
          : isStale
          ? '1px solid #fde68a'
          : isApproved
          ? '1px solid #3b82f6'
          : '1px solid var(--color-border, #e2e8f0)',
        borderRadius: 'var(--radius-lg, 10px)',
        boxShadow: isApplied ? '0 2px 8px rgba(16, 185, 129, 0.15)' : 'var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.05))',
        overflow: 'hidden',
        margin: '12px 0',
        fontFamily: 'var(--font-sans, sans-serif)',
      }}
    >
      {/* =========================================================================
          TOP BANNER: LIFECYCLE & SAFETY STATE
         ========================================================================= */}
      {isApplied ? (
        <div
          data-testid="applied-status-banner"
          style={{
            backgroundColor: '#064e3b',
            color: '#a7f3d0',
            padding: '7px 16px',
            fontSize: '11px',
            fontWeight: 700,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #047857',
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <ShieldCheck size={14} style={{ color: '#34d399' }} />
            <span>REPAIR APPLIED TO SOURCE FILE — VERIFIED VIA AST</span>
          </span>
          <span style={{ color: '#6ee7b7', fontSize: '10px', fontWeight: 600 }}>
            Phase 7 Applied
          </span>
        </div>
      ) : isRolledBack ? (
        <div
          data-testid="rolled-back-status-banner"
          style={{
            backgroundColor: '#312e81',
            color: '#c7d2fe',
            padding: '7px 16px',
            fontSize: '11px',
            fontWeight: 700,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #4338ca',
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <RotateCcw size={14} style={{ color: '#818cf8' }} />
            <span>REPAIR ROLLED BACK — ORIGINAL SOURCE RESTORED</span>
          </span>
          <span style={{ color: '#a5b4fc', fontSize: '10px', fontWeight: 600 }}>
            Phase 7 Rolled Back
          </span>
        </div>
      ) : isFailed ? (
        <div
          data-testid="failed-status-banner"
          style={{
            backgroundColor: '#7f1d1d',
            color: '#fecaca',
            padding: '7px 16px',
            fontSize: '11px',
            fontWeight: 700,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #991b1b',
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <AlertOctagon size={14} style={{ color: '#f87171' }} />
            <span>PATCH APPLICATION FAILED — RECOVERY RESTORED ORIGINAL SOURCE</span>
          </span>
          <span style={{ color: '#fca5a5', fontSize: '10px', fontWeight: 600 }}>
            Phase 7 Failure Recovery
          </span>
        </div>
      ) : isApproved ? (
        <div
          data-testid="approved-status-banner"
          style={{
            backgroundColor: '#1e3a5f',
            color: '#93c5fd',
            padding: '7px 16px',
            fontSize: '11px',
            fontWeight: 700,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #2563eb',
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <CheckSquare size={14} style={{ color: '#60a5fa' }} />
            <span>HUMAN APPROVED • READY TO APPLY TO SOURCE FILE</span>
          </span>
          <span style={{ color: '#bfdbfe', fontSize: '10px', fontWeight: 600 }}>
            Phase 7 Approved
          </span>
        </div>
      ) : isRejected ? (
        <div
          data-testid="rejected-status-banner"
          style={{
            backgroundColor: '#334155',
            color: '#cbd5e1',
            padding: '7px 16px',
            fontSize: '11px',
            fontWeight: 700,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #475569',
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <X size={14} style={{ color: '#f87171' }} />
            <span>PROPOSAL REJECTED BY USER</span>
          </span>
          <span style={{ color: '#94a3b8', fontSize: '10px', fontWeight: 600 }}>
            Phase 7 Rejected
          </span>
        </div>
      ) : (
        <div
          data-testid="proposed-status-banner"
          style={{
            backgroundColor: '#0f172a',
            color: '#38bdf8',
            padding: '6px 16px',
            fontSize: '10.5px',
            fontWeight: 700,
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #1e293b',
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
            <ShieldCheck size={13} style={{ color: '#22c55e' }} />
            <span>PROPOSED PATCH — ORIGINAL SOURCE NOT MODIFIED</span>
          </span>
          <span style={{ color: '#94a3b8', fontSize: '10px', fontWeight: 600 }}>
            Phase 6 Review Only
          </span>
        </div>
      )}

      {/* =========================================================================
          CRITICAL STALE SOURCE WARNING BANNER (If disk source has changed)
         ========================================================================= */}
      {isStale && (
        <div
          data-testid="stale-source-warning"
          style={{
            backgroundColor: '#fffbeb',
            borderBottom: '1px solid #fde68a',
            padding: '10px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            color: '#92400e',
            fontSize: '12px',
            fontWeight: 600,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={16} style={{ color: '#d97706', flexShrink: 0 }} />
            <span>
              <strong>STALE PROPOSAL — SOURCE HAS CHANGED:</strong> The file on disk was modified after this patch was synthesized. Approve and Apply are disabled.
            </span>
          </div>
          {onRegenerate && (
            <button
              onClick={onRegenerate}
              disabled={isRegenerating}
              data-testid="regenerate-stale-btn"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 10px',
                backgroundColor: '#d97706',
                color: '#ffffff',
                border: 'none',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: isRegenerating ? 'not-allowed' : 'pointer',
                flexShrink: 0,
              }}
            >
              <RefreshCw size={12} className={isRegenerating ? 'animate-spin' : ''} />
              <span>{isRegenerating ? 'Regenerating...' : 'Regenerate Against Current Source'}</span>
            </button>
          )}
        </div>
      )}

      {/* =========================================================================
          ACTION MESSAGES (Alerts/Toasts)
         ========================================================================= */}
      {actionError && (
        <div
          data-testid="action-error-banner"
          style={{
            backgroundColor: '#fef2f2',
            borderBottom: '1px solid #fecaca',
            color: '#991b1b',
            padding: '8px 16px',
            fontSize: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <AlertTriangle size={14} style={{ color: '#dc2626' }} />
            <span>{actionError}</span>
          </div>
          <button
            onClick={() => setActionError(null)}
            style={{ background: 'none', border: 'none', color: '#991b1b', cursor: 'pointer', padding: 0 }}
          >
            <X size={13} />
          </button>
        </div>
      )}

      {actionSuccess && (
        <div
          data-testid="action-success-banner"
          style={{
            backgroundColor: '#f0fdf4',
            borderBottom: '1px solid #bbf7d0',
            color: '#166534',
            padding: '8px 16px',
            fontSize: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <CheckCircle2 size={14} style={{ color: '#16a34a' }} />
            <span>{actionSuccess}</span>
          </div>
          <button
            onClick={() => setActionSuccess(null)}
            style={{ background: 'none', border: 'none', color: '#166534', cursor: 'pointer', padding: 0 }}
          >
            <X size={13} />
          </button>
        </div>
      )}

      {/* =========================================================================
          A. REPAIR HEADER (Rule ID, File, Line, Actions)
         ========================================================================= */}
      <div
        style={{
          backgroundColor: '#1e293b',
          color: '#ffffff',
          padding: '12px 16px',
          borderBottom: '1px solid #334155',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            flexWrap: 'wrap',
          }}
        >
          {/* Left: Tag + Rule ID + Bug Title */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span
              style={{
                fontSize: '10px',
                fontWeight: 700,
                letterSpacing: '0.06em',
                textTransform: 'uppercase',
                padding: '2px 6px',
                borderRadius: '4px',
                backgroundColor: '#0f172a',
                color: isApplied ? '#34d399' : '#22c55e',
                border: isApplied ? '1px solid #059669' : '1px solid #15803d',
              }}
            >
              {isApplied ? 'Applied Repair' : 'Repair Proposal'}
            </span>
            <span
              style={{
                fontFamily: 'var(--font-mono, monospace)',
                fontSize: '11px',
                fontWeight: 700,
                padding: '2px 7px',
                borderRadius: '4px',
                backgroundColor: '#2563eb',
                color: '#eff6ff',
              }}
            >
              {proposal.rule_id}
            </span>
            <h3
              style={{
                margin: 0,
                fontSize: '14px',
                fontWeight: 600,
                color: '#f8fafc',
                letterSpacing: '-0.01em',
              }}
            >
              {proposal.rule_name || 'Code Repair Proposal'}
            </h3>
          </div>

          {/* Right: Actions (Regenerate, View in Editor, History, Close) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {onRegenerate && (
              <button
                onClick={onRegenerate}
                disabled={isRegenerating}
                data-testid="regenerate-proposal-btn"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '5px 9px',
                  backgroundColor: 'rgba(255, 255, 255, 0.08)',
                  color: '#cbd5e1',
                  borderRadius: 'var(--radius-sm, 6px)',
                  fontSize: '11.5px',
                  fontWeight: 500,
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  cursor: isRegenerating ? 'not-allowed' : 'pointer',
                }}
                title="Regenerate patch proposal with AI"
              >
                <RefreshCw size={12} className={isRegenerating ? 'animate-spin' : ''} />
                <span>{isRegenerating ? 'Regenerating...' : 'Regenerate'}</span>
              </button>
            )}

            {onOpenHistory && (
              <button
                onClick={onOpenHistory}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '5px 9px',
                  backgroundColor: 'rgba(255, 255, 255, 0.08)',
                  color: '#cbd5e1',
                  borderRadius: 'var(--radius-sm, 6px)',
                  fontSize: '11.5px',
                  fontWeight: 500,
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  cursor: 'pointer',
                }}
                title="View previous repair proposals"
              >
                <History size={12} />
                <span>History</span>
              </button>
            )}

            {onNavigateToFile && (
              <button
                onClick={() => onNavigateToFile(proposal.file_path, proposal.start_line)}
                data-testid="view-bug-in-editor-btn"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '5px 9px',
                  backgroundColor: '#3b82f6',
                  color: '#ffffff',
                  borderRadius: 'var(--radius-sm, 6px)',
                  fontSize: '11.5px',
                  fontWeight: 600,
                  border: 'none',
                  cursor: 'pointer',
                }}
                title="Jump to bug line in Monaco Editor"
              >
                <FileCode size={12} />
                <span>View in Editor</span>
              </button>
            )}

            {onClose && (
              <button
                onClick={onClose}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '24px',
                  height: '24px',
                  backgroundColor: 'transparent',
                  color: '#94a3b8',
                  borderRadius: '4px',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                <X size={15} />
              </button>
            )}
          </div>
        </div>

        {/* Location Subline: Path, Language, Line Range */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            marginTop: '8px',
            fontSize: '11.5px',
            color: '#94a3b8',
            flexWrap: 'wrap',
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#cbd5e1' }}>
            <FileCode size={13} style={{ color: '#38bdf8' }} />
            <strong style={{ color: '#f1f5f9' }}>{proposal.file_path}</strong>
          </span>
          <span>•</span>
          <span>
            Lines: <strong>{proposal.start_line}</strong>
            {proposal.end_line && proposal.end_line !== proposal.start_line && ` - ${proposal.end_line}`}
          </span>
          <span>•</span>
          <span style={{ textTransform: 'uppercase', color: '#e2e8f0', fontWeight: 600 }}>
            {proposal.language}
          </span>
          <span>•</span>
          <span style={{ color: '#86efac' }}>+{proposal.additions}</span>
          <span style={{ color: '#fca5a5' }}>-{proposal.deletions}</span>

          {proposal.confidence_score > 0 && (
            <>
              <span>•</span>
              <span style={{ color: '#38bdf8' }}>
                Confidence: <strong>{proposal.confidence_score}%</strong>
              </span>
            </>
          )}
        </div>
      </div>

      <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {/* =========================================================================
            B. PHASE 7 HUMAN APPROVAL & CONTROLLED APPLICATION ACTIONS BAR
           ========================================================================= */}
        <div
          style={{
            padding: '12px 14px',
            borderRadius: '8px',
            backgroundColor: isApplied
              ? '#f0fdf4'
              : isApproved
              ? '#eff6ff'
              : isRejected
              ? '#f8fafc'
              : '#f8fafc',
            border: isApplied
              ? '1px solid #bbf7d0'
              : isApproved
              ? '1px solid #bfdbfe'
              : '1px solid var(--color-border, #e2e8f0)',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Lock size={15} style={{ color: isApplied ? '#16a34a' : isApproved ? '#2563eb' : '#64748b' }} />
              <div>
                <div style={{ fontSize: '12px', fontWeight: 700, color: '#1e293b' }}>
                  {isApplied
                    ? 'Patch Applied & Verified'
                    : isRolledBack
                    ? 'Patch Rolled Back'
                    : isApproved
                    ? 'Patch Approved • Ready for Application'
                    : isRejected
                    ? 'Patch Rejected'
                    : 'Human Approval Required'}
                </div>
                <div style={{ fontSize: '11px', color: '#64748b' }}>
                  {isApplied
                    ? `Applied at ${new Date(proposal.applied_at || '').toLocaleTimeString()} • Backup ID: ${proposal.backup_id || 'saved'}`
                    : isRolledBack
                    ? `Restored at ${new Date(proposal.rollback_at || '').toLocaleTimeString()} byte-for-byte`
                    : isApproved
                    ? 'Review confirmed diff below, then click Apply to atomically write to disk.'
                    : isRejected
                    ? 'This proposal was declined. You may regenerate or create a new proposal.'
                    : 'Inspect the unified diff and AST validation before approving this patch.'}
                </div>
              </div>
            </div>

            {/* Action Buttons based on lifecycle */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
              {/* Proposal State: Proposed / Pending */}
              {!isApproved && !isApplied && !isRolledBack && !isRejected && (
                <>
                  <button
                    onClick={handleApprove}
                    disabled={isApproving || isStale}
                    data-testid="approve-repair-btn"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '6px 14px',
                      backgroundColor: isStale ? '#94a3b8' : '#16a34a',
                      color: '#ffffff',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: 600,
                      border: 'none',
                      cursor: isApproving || isStale ? 'not-allowed' : 'pointer',
                      boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                    }}
                    title={isStale ? 'Proposal is stale. Regenerate first.' : 'Approve patch for application'}
                  >
                    {isApproving ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
                    <span>{isApproving ? 'Approving...' : 'Approve Repair'}</span>
                  </button>

                  <button
                    onClick={handleReject}
                    disabled={isRejecting}
                    data-testid="reject-repair-btn"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '6px 12px',
                      backgroundColor: '#ffffff',
                      color: '#dc2626',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: 500,
                      border: '1px solid #fca5a5',
                      cursor: isRejecting ? 'not-allowed' : 'pointer',
                    }}
                    title="Reject this proposal"
                  >
                    {isRejecting ? <Loader2 size={13} className="animate-spin" /> : <X size={13} />}
                    <span>Reject</span>
                  </button>
                </>
              )}

              {/* State: Approved (Ready to Apply) */}
              {isApproved && !isApplied && !isRolledBack && (
                <>
                  <button
                    onClick={() => setShowApplyModal(true)}
                    disabled={isApplying || isStale}
                    data-testid="apply-repair-btn"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '7px 16px',
                      backgroundColor: isStale ? '#94a3b8' : '#22c55e',
                      color: '#ffffff',
                      borderRadius: '6px',
                      fontSize: '12.5px',
                      fontWeight: 700,
                      border: 'none',
                      cursor: isApplying || isStale ? 'not-allowed' : 'pointer',
                      boxShadow: '0 2px 4px rgba(34, 197, 94, 0.3)',
                    }}
                    title={isStale ? 'Cannot apply: source file has changed' : 'Apply patch to disk with atomic write and backup'}
                  >
                    {isApplying ? <Loader2 size={14} className="animate-spin" /> : <ShieldCheck size={14} />}
                    <span>{isApplying ? 'Applying Patch...' : 'Apply Approved Repair'}</span>
                  </button>

                  <button
                    onClick={handleReject}
                    disabled={isRejecting}
                    data-testid="reject-repair-btn"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '6px 12px',
                      backgroundColor: '#ffffff',
                      color: '#64748b',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: 500,
                      border: '1px solid #cbd5e1',
                      cursor: isRejecting ? 'not-allowed' : 'pointer',
                    }}
                  >
                    <span>Reject</span>
                  </button>
                </>
              )}

              {/* State: Applied */}
              {isApplied && (
                <>
                  <button
                    onClick={() => setShowRollbackModal(true)}
                    disabled={isRollingBack}
                    data-testid="rollback-repair-btn"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      padding: '6px 14px',
                      backgroundColor: '#ffffff',
                      color: '#b45309',
                      borderRadius: '6px',
                      fontSize: '12px',
                      fontWeight: 600,
                      border: '1px solid #fde68a',
                      cursor: isRollingBack ? 'not-allowed' : 'pointer',
                      boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                    }}
                    title="Revert source file to pre-apply state"
                  >
                    {isRollingBack ? <Loader2 size={13} className="animate-spin" /> : <RotateCcw size={13} />}
                    <span>{isRollingBack ? 'Rolling back...' : 'Rollback Repair'}</span>
                  </button>

                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      color: '#059669',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '4px 8px',
                      backgroundColor: '#ecfdf5',
                      borderRadius: '4px',
                    }}
                  >
                    <CheckCircle2 size={12} />
                    <span>Applied to disk</span>
                  </span>
                </>
              )}

              {/* State: Rolled Back */}
              {isRolledBack && (
                <span
                  style={{
                    fontSize: '11.5px',
                    fontWeight: 600,
                    color: '#4338ca',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '4px 8px',
                    backgroundColor: '#e0e7ff',
                    borderRadius: '4px',
                  }}
                >
                  <RotateCcw size={12} />
                  <span>Rolled back</span>
                </span>
              )}

              {/* Audit Trail Button */}
              <button
                onClick={handleToggleAuditTrail}
                data-testid="toggle-audit-btn"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '6px 10px',
                  backgroundColor: 'transparent',
                  color: '#475569',
                  borderRadius: '6px',
                  fontSize: '11.5px',
                  fontWeight: 500,
                  border: '1px solid #cbd5e1',
                  cursor: 'pointer',
                }}
                title="View full audit history for this proposal"
              >
                <FileText size={12} />
                <span>{showAuditTrail ? 'Hide Audit' : 'Audit Trail'}</span>
              </button>
            </div>
          </div>

          {/* Applied Details (Post-Apply Fingerprint & Backup Details) */}
          {isApplied && proposal.backup_id && (
            <div
              style={{
                fontSize: '11px',
                color: '#065f46',
                fontFamily: 'var(--font-mono, monospace)',
                backgroundColor: 'rgba(16, 185, 129, 0.08)',
                padding: '6px 10px',
                borderRadius: '4px',
                display: 'flex',
                flexWrap: 'wrap',
                gap: '12px',
              }}
            >
              <span>Backup ID: <strong>{proposal.backup_id}</strong></span>
              {proposal.post_apply_fingerprint && (
                <span>SHA-256: <strong>{proposal.post_apply_fingerprint.slice(0, 16)}...</strong></span>
              )}
              <span>Syntax: <strong>AST Validated</strong></span>
            </div>
          )}
        </div>

        {/* =========================================================================
            AUDIT TRAIL VIEW (Collapsible)
           ========================================================================= */}
        {showAuditTrail && (
          <div
            data-testid="audit-trail-container"
            style={{
              padding: '12px 14px',
              backgroundColor: '#0f172a',
              borderRadius: '8px',
              color: '#cbd5e1',
              fontSize: '11.5px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase', fontSize: '11px', letterSpacing: '0.04em' }}>
                Immutable Audit Trail ({auditEvents.length} events)
              </span>
              {isLoadingAudit && <Loader2 size={12} className="animate-spin" style={{ color: '#38bdf8' }} />}
            </div>

            {auditEvents.length === 0 && !isLoadingAudit ? (
              <div style={{ fontStyle: 'italic', color: '#64748b' }}>No audit events logged yet.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {auditEvents.map((ev, idx) => (
                  <div
                    key={ev.id || idx}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      justifyContent: 'space-between',
                      padding: '4px 8px',
                      backgroundColor: 'rgba(255, 255, 255, 0.04)',
                      borderRadius: '4px',
                      gap: '8px',
                    }}
                  >
                    <div>
                      <span style={{ fontWeight: 700, color: '#f8fafc', marginRight: '6px' }}>
                        {ev.event_type}
                      </span>
                      <span style={{ color: '#94a3b8' }}>
                        {ev.details && typeof ev.details === 'object' ? JSON.stringify(ev.details) : ''}
                      </span>
                    </div>
                    <span style={{ color: '#64748b', fontSize: '10px', flexShrink: 0 }}>
                      {new Date(ev.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* =========================================================================
            C. REPAIR SUMMARY & EXPLANATION
           ========================================================================= */}
        <div
          style={{
            backgroundColor: 'var(--color-surface-subtle, #f8fafc)',
            border: '1px solid var(--color-border, #e2e8f0)',
            borderRadius: 'var(--radius-md, 8px)',
            padding: '12px 14px',
          }}
        >
          <div
            style={{
              fontSize: '13px',
              fontWeight: 700,
              color: 'var(--color-navy-900, #0f172a)',
              marginBottom: '4px',
            }}
          >
            {proposal.repair_summary}
          </div>
          <div
            style={{
              fontSize: '12px',
              color: 'var(--color-navy-700, #334155)',
              lineHeight: 1.5,
            }}
          >
            {proposal.repair_explanation}
          </div>
        </div>

        {/* =========================================================================
            D. CODE VIEW TABS (Diff Preview, Proposed Code, Original Code)
           ========================================================================= */}
        <div
          style={{
            borderRadius: 'var(--radius-md, 8px)',
            border: '1px solid #1e293b',
            overflow: 'hidden',
            backgroundColor: '#0f172a',
          }}
        >
          {/* Tab Navigation Toolbar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              backgroundColor: '#1e293b',
              padding: '6px 12px',
              borderBottom: '1px solid #334155',
              flexWrap: 'wrap',
              gap: '6px',
            }}
          >
            {/* Left: Tab Switchers */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <button
                onClick={() => setActiveTab('diff')}
                style={{
                  padding: '4px 10px',
                  fontSize: '11.5px',
                  fontWeight: 600,
                  borderRadius: '4px',
                  border: 'none',
                  cursor: 'pointer',
                  backgroundColor: activeTab === 'diff' ? '#0f172a' : 'transparent',
                  color: activeTab === 'diff' ? '#38bdf8' : '#94a3b8',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <FileDiff size={12} />
                <span>Diff Preview</span>
              </button>

              <button
                onClick={() => setActiveTab('proposed')}
                style={{
                  padding: '4px 10px',
                  fontSize: '11.5px',
                  fontWeight: 600,
                  borderRadius: '4px',
                  border: 'none',
                  cursor: 'pointer',
                  backgroundColor: activeTab === 'proposed' ? '#0f172a' : 'transparent',
                  color: activeTab === 'proposed' ? '#86efac' : '#94a3b8',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <CheckCircle2 size={12} />
                <span>Proposed Code</span>
              </button>

              <button
                onClick={() => setActiveTab('original')}
                style={{
                  padding: '4px 10px',
                  fontSize: '11.5px',
                  fontWeight: 600,
                  borderRadius: '4px',
                  border: 'none',
                  cursor: 'pointer',
                  backgroundColor: activeTab === 'original' ? '#0f172a' : 'transparent',
                  color: activeTab === 'original' ? '#fca5a5' : '#94a3b8',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <Terminal size={12} />
                <span>Original Code</span>
              </button>
            </div>

            {/* Right: Copy to Clipboard */}
            <div>
              {activeTab === 'diff' && (
                <button
                  onClick={() => handleCopy(proposal.diff, true)}
                  data-testid="copy-diff-btn"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '3px 8px',
                    fontSize: '11px',
                    backgroundColor: 'rgba(255, 255, 255, 0.08)',
                    color: copiedDiff ? '#86efac' : '#cbd5e1',
                    borderRadius: '4px',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    cursor: 'pointer',
                  }}
                  title="Copy git patch diff to clipboard"
                >
                  {copiedDiff ? <Check size={11} /> : <Copy size={11} />}
                  <span>{copiedDiff ? 'Copied' : 'Copy Diff'}</span>
                </button>
              )}

              {activeTab === 'proposed' && (
                <button
                  onClick={() => handleCopy(proposal.proposed_code, false)}
                  data-testid="copy-proposed-btn"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    padding: '3px 8px',
                    fontSize: '11px',
                    backgroundColor: 'rgba(255, 255, 255, 0.08)',
                    color: copiedProposed ? '#86efac' : '#cbd5e1',
                    borderRadius: '4px',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    cursor: 'pointer',
                  }}
                  title="Copy proposed replacement snippet"
                >
                  {copiedProposed ? <Check size={11} /> : <Copy size={11} />}
                  <span>{copiedProposed ? 'Copied' : 'Copy Code'}</span>
                </button>
              )}
            </div>
          </div>

          {/* Code Body */}
          <div style={{ maxHeight: '280px', overflowY: 'auto', padding: '8px 0' }}>
            {activeTab === 'diff' && renderDiffLines(proposal.diff)}

            {activeTab === 'proposed' && (
              <pre
                style={{
                  margin: 0,
                  padding: '8px 16px',
                  fontFamily: 'var(--font-mono, monospace)',
                  fontSize: '11.5px',
                  lineHeight: 1.5,
                  color: '#86efac',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {proposal.proposed_code}
              </pre>
            )}

            {activeTab === 'original' && (
              <pre
                style={{
                  margin: 0,
                  padding: '8px 16px',
                  fontFamily: 'var(--font-mono, monospace)',
                  fontSize: '11.5px',
                  lineHeight: 1.5,
                  color: '#fca5a5',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {proposal.original_code}
              </pre>
            )}
          </div>
        </div>

        {/* =========================================================================
            E. VALIDATION CHECKLIST (COLLAPSIBLE MULTI-LAYER INTEGRITY CHECK)
           ========================================================================= */}
        <div
          style={{
            backgroundColor: 'var(--color-surface-subtle, #f8fafc)',
            border: '1px solid var(--color-border, #e2e8f0)',
            borderRadius: 'var(--radius-md, 8px)',
            overflow: 'hidden',
          }}
        >
          <button
            onClick={() => setShowValidationDetails(!showValidationDetails)}
            data-testid="toggle-validation-btn"
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '10px 14px',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              textAlign: 'left',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldCheck size={16} style={{ color: '#16a34a' }} />
              <span
                style={{
                  fontSize: '12px',
                  fontWeight: 700,
                  color: 'var(--color-navy-800, #1e293b)',
                  letterSpacing: '0.02em',
                }}
              >
                Pre-Application Validation Status:
              </span>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  color: proposal.validation_status === 'passed' ? '#16a34a' : '#dc2626',
                  textTransform: 'uppercase',
                }}
              >
                {proposal.validation_status === 'passed' ? 'Passed (All Checks Verified)' : proposal.validation_status}
              </span>
            </div>
            {showValidationDetails ? (
              <ChevronUp size={15} color="#64748b" />
            ) : (
              <ChevronDown size={15} color="#64748b" />
            )}
          </button>

          {showValidationDetails && (
            <div
              style={{
                padding: '12px 14px',
                borderTop: '1px solid var(--color-border, #e2e8f0)',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              {proposal.validation_details?.checks?.map((check, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '8px',
                    fontSize: '11.5px',
                    color: '#334155',
                  }}
                >
                  {check.status === 'passed' ? (
                    <CheckCircle2 size={14} style={{ color: '#16a34a', flexShrink: 0, marginTop: '2px' }} />
                  ) : check.status === 'warning' ? (
                    <AlertTriangle size={14} style={{ color: '#d97706', flexShrink: 0, marginTop: '2px' }} />
                  ) : (
                    <ShieldAlert size={14} style={{ color: '#dc2626', flexShrink: 0, marginTop: '2px' }} />
                  )}
                  <div>
                    <strong style={{ color: '#1e293b' }}>{check.name}:</strong>{' '}
                    <span>{check.message}</span>
                    {check.details && (
                      <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                        {check.details}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* =========================================================================
            F. ASSUMPTIONS (Collapsible, only if available)
           ========================================================================= */}
        {proposal.assumptions && proposal.assumptions.length > 0 && (
          <div
            style={{
              backgroundColor: 'var(--color-surface-subtle, #f8fafc)',
              border: '1px solid var(--color-border, #e2e8f0)',
              borderRadius: 'var(--radius-md, 8px)',
              overflow: 'hidden',
            }}
          >
            <button
              onClick={() => setShowAssumptions(!showAssumptions)}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                textAlign: 'left',
              }}
            >
              <span
                style={{
                  fontSize: '11.5px',
                  fontWeight: 700,
                  color: 'var(--color-navy-700, #334155)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.03em',
                }}
              >
                <Info size={13} style={{ color: '#d97706' }} />
                <span>AI Repair Assumptions</span>
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: 600,
                    color: '#64748b',
                    backgroundColor: '#e2e8f0',
                    padding: '1px 5px',
                    borderRadius: '10px',
                  }}
                >
                  {proposal.assumptions.length}
                </span>
              </span>
              {showAssumptions ? <ChevronUp size={14} color="#64748b" /> : <ChevronDown size={14} color="#64748b" />}
            </button>

            {showAssumptions && (
              <div
                style={{
                  padding: '0 14px 12px 14px',
                  borderTop: '1px solid var(--color-border, #e2e8f0)',
                  paddingTop: '8px',
                }}
              >
                <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '12px', color: '#475569', lineHeight: 1.5 }}>
                  {proposal.assumptions.map((item, idx) => (
                    <li key={idx} style={{ marginBottom: '4px' }}>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* =========================================================================
            G. AI METADATA FOOTER
           ========================================================================= */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            paddingTop: '10px',
            borderTop: '1px solid var(--color-border, #e2e8f0)',
            fontSize: '11px',
            color: 'var(--color-navy-400, #94a3b8)',
            flexWrap: 'wrap',
            gap: '8px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
              <Cpu size={12} style={{ color: '#64748b' }} />
              <span>Model:</span>
              <strong style={{ color: 'var(--color-navy-700, #334155)', fontWeight: 600 }}>
                {proposal.model || 'gemini-3.5-flash-lite'}
              </strong>
            </span>

            {proposal.duration_ms > 0 && (
              <>
                <span>•</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  <Clock size={12} style={{ color: '#64748b' }} />
                  <span>Latency:</span>
                  <strong style={{ color: 'var(--color-navy-700, #334155)', fontWeight: 600 }}>
                    {proposal.duration_ms}ms
                  </strong>
                </span>
              </>
            )}

            <span>•</span>
            <span style={{ color: '#64748b' }}>Proposal: {proposal.id.slice(0, 8)}...</span>
          </div>

          <span style={{ fontSize: '10.5px', color: isApplied ? '#059669' : '#94a3b8' }}>
            {isApplied
              ? `Applied safely with backup • SHA: ${proposal.post_apply_fingerprint?.slice(0, 8) || 'verified'}`
              : 'Phase 7 Human-in-the-Loop • Explicit confirmation required'}
          </span>
        </div>
      </div>

      {/* =========================================================================
          CONFIRMATION MODAL: APPLY REPAIR
         ========================================================================= */}
      {showApplyModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.7)',
            backdropFilter: 'blur(3px)',
            zIndex: 9999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px',
          }}
          onClick={() => !isApplying && setShowApplyModal(false)}
        >
          <div
            data-testid="apply-confirmation-dialog"
            style={{
              width: '100%',
              maxWidth: '520px',
              backgroundColor: '#ffffff',
              borderRadius: '12px',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.3)',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div
              style={{
                backgroundColor: '#0f172a',
                color: '#ffffff',
                padding: '14px 20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck size={18} style={{ color: '#22c55e' }} />
                <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600 }}>
                  Confirm Patch Application
                </h3>
              </div>
              {!isApplying && (
                <button
                  onClick={() => setShowApplyModal(false)}
                  style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: 0 }}
                >
                  <X size={16} />
                </button>
              )}
            </div>

            {/* Modal Body */}
            <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ fontSize: '13px', color: '#334155', lineHeight: 1.5 }}>
                You are about to apply an AI-generated repair patch to your actual project source file on disk.
              </div>

              <div
                style={{
                  backgroundColor: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  padding: '12px',
                  fontSize: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                }}
              >
                <div>
                  <strong style={{ color: '#0f172a' }}>Target File:</strong>{' '}
                  <span style={{ fontFamily: 'var(--font-mono, monospace)', color: '#2563eb' }}>
                    {proposal.file_path}
                  </span>
                </div>
                <div>
                  <strong style={{ color: '#0f172a' }}>Line Range:</strong> Lines {proposal.start_line} to {proposal.end_line}
                </div>
                <div>
                  <strong style={{ color: '#0f172a' }}>Modifications:</strong>{' '}
                  <span style={{ color: '#16a34a', fontWeight: 600 }}>+{proposal.additions} lines</span>,{' '}
                  <span style={{ color: '#dc2626', fontWeight: 600 }}>-{proposal.deletions} lines</span>
                </div>
              </div>

              {/* Safety Guarantees Notice */}
              <div
                style={{
                  backgroundColor: '#f0fdf4',
                  border: '1px solid #bbf7d0',
                  borderRadius: '6px',
                  padding: '10px 12px',
                  fontSize: '11.5px',
                  color: '#166534',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                }}
              >
                <div style={{ fontWeight: 700 }}>FIXMATE AI Safety Guarantees:</div>
                <div>• Automatic byte-for-byte pre-application backup in <code>.fixmate/backups/</code></div>
                <div>• Atomic write via temporary file swap avoids file corruption</div>
                <div>• Concrete AST syntax validation (Python AST / Tree-sitter) executed immediately after write</div>
                <div>• Automatic rollback if post-write syntax validation fails</div>
              </div>

              {/* Optional Comment */}
              <div>
                <label style={{ display: 'block', fontSize: '11.5px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>
                  Optional Application Note / Reason (for audit trail):
                </label>
                <input
                  type="text"
                  placeholder="e.g. Approved fix for production crash"
                  value={applyComment}
                  onChange={(e) => setApplyComment(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    fontSize: '12px',
                    border: '1px solid #cbd5e1',
                    borderRadius: '6px',
                    boxSizing: 'border-box',
                  }}
                  disabled={isApplying}
                />
              </div>
            </div>

            {/* Modal Footer */}
            <div
              style={{
                backgroundColor: '#f8fafc',
                borderTop: '1px solid #e2e8f0',
                padding: '12px 20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-end',
                gap: '10px',
              }}
            >
              <button
                onClick={() => setShowApplyModal(false)}
                disabled={isApplying}
                data-testid="cancel-apply-modal-btn"
                style={{
                  padding: '7px 14px',
                  backgroundColor: '#ffffff',
                  color: '#475569',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 500,
                  cursor: isApplying ? 'not-allowed' : 'pointer',
                }}
              >
                Cancel
              </button>

              <button
                onClick={handleConfirmApply}
                disabled={isApplying}
                data-testid="confirm-apply-btn"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '7px 16px',
                  backgroundColor: '#16a34a',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: isApplying ? 'not-allowed' : 'pointer',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                }}
              >
                {isApplying ? <Loader2 size={13} className="animate-spin" /> : <ShieldCheck size={13} />}
                <span>{isApplying ? 'Applying & Validating...' : 'Confirm & Apply Repair'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          CONFIRMATION MODAL: ROLLBACK REPAIR
         ========================================================================= */}
      {showRollbackModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.7)',
            backdropFilter: 'blur(3px)',
            zIndex: 9999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px',
          }}
          onClick={() => !isRollingBack && setShowRollbackModal(false)}
        >
          <div
            data-testid="rollback-confirmation-dialog"
            style={{
              width: '100%',
              maxWidth: '480px',
              backgroundColor: '#ffffff',
              borderRadius: '12px',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.3)',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div
              style={{
                backgroundColor: '#7c2d12',
                color: '#ffffff',
                padding: '14px 20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <RotateCcw size={18} style={{ color: '#fdba74' }} />
                <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600 }}>
                  Confirm Repair Rollback
                </h3>
              </div>
              {!isRollingBack && (
                <button
                  onClick={() => setShowRollbackModal(false)}
                  style={{ background: 'none', border: 'none', color: '#fed7aa', cursor: 'pointer', padding: 0 }}
                >
                  <X size={16} />
                </button>
              )}
            </div>

            {/* Modal Body */}
            <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ fontSize: '13px', color: '#334155', lineHeight: 1.5 }}>
                This action will revert <strong>{proposal.file_path}</strong> back to its exact pre-application state using backup <code>{proposal.backup_id}</code>.
              </div>

              <div
                style={{
                  backgroundColor: '#fffbeb',
                  border: '1px solid #fde68a',
                  borderRadius: '6px',
                  padding: '10px 12px',
                  fontSize: '11.5px',
                  color: '#92400e',
                  lineHeight: 1.4,
                }}
              >
                <strong>Safety Notice:</strong> If the file has been manually edited on disk since this patch was applied, rollback will be safely aborted to protect your newer edits.
              </div>
            </div>

            {/* Modal Footer */}
            <div
              style={{
                backgroundColor: '#f8fafc',
                borderTop: '1px solid #e2e8f0',
                padding: '12px 20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-end',
                gap: '10px',
              }}
            >
              <button
                onClick={() => setShowRollbackModal(false)}
                disabled={isRollingBack}
                data-testid="cancel-rollback-modal-btn"
                style={{
                  padding: '7px 14px',
                  backgroundColor: '#ffffff',
                  color: '#475569',
                  border: '1px solid #cbd5e1',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 500,
                  cursor: isRollingBack ? 'not-allowed' : 'pointer',
                }}
              >
                Cancel
              </button>

              <button
                onClick={handleConfirmRollback}
                disabled={isRollingBack}
                data-testid="confirm-rollback-btn"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '7px 16px',
                  backgroundColor: '#c2410c',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '12px',
                  fontWeight: 700,
                  cursor: isRollingBack ? 'not-allowed' : 'pointer',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                }}
              >
                {isRollingBack ? <Loader2 size={13} className="animate-spin" /> : <RotateCcw size={13} />}
                <span>{isRollingBack ? 'Rolling back...' : 'Confirm & Rollback'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
