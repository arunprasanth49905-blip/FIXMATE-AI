import React, { useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Copy,
  Check,
  FileCode,
  ArrowRight,
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
} from 'lucide-react';
import { RepairProposal } from '../../types/api';

interface RepairProposalCardProps {
  proposal: RepairProposal;
  onClose?: () => void;
  onNavigateToFile?: (path: string, line: number) => void;
  onRegenerate?: () => void;
  onOpenHistory?: () => void;
  isRegenerating?: boolean;
}

export const RepairProposalCard: React.FC<RepairProposalCardProps> = ({
  proposal,
  onClose,
  onNavigateToFile,
  onRegenerate,
  onOpenHistory,
  isRegenerating = false,
}) => {
  const [activeTab, setActiveTab] = useState<'diff' | 'side-by-side' | 'proposed' | 'original'>('diff');
  const [copiedProposed, setCopiedProposed] = useState(false);
  const [copiedDiff, setCopiedDiff] = useState(false);
  const [showValidationDetails, setShowValidationDetails] = useState(false);
  const [showAssumptions, setShowAssumptions] = useState(true);

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

  const isStale = proposal.is_stale || proposal.repair_status === 'stale_source';
  const isRejected = proposal.validation_status === 'failed' || proposal.repair_status === 'rejected_by_validation';
  const needsClarification = proposal.repair_status === 'needs_clarification';

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
        border: isStale ? '1px solid #fde68a' : '1px solid var(--color-border, #e2e8f0)',
        borderRadius: 'var(--radius-lg, 10px)',
        boxShadow: 'var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.05))',
        overflow: 'hidden',
        margin: '12px 0',
        fontFamily: 'var(--font-sans, sans-serif)',
      }}
    >
      {/* =========================================================================
          SAFETY BANNER (ORIGINAL SOURCE NOT MODIFIED) - ALWAYS VISIBLE
         ========================================================================= */}
      <div
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
              <strong>STALE PROPOSAL — SOURCE HAS CHANGED:</strong> The file on disk was modified after this patch was synthesized.
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
                color: '#22c55e',
                border: '1px solid #15803d',
              }}
            >
              Repair Proposal
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
                  gap: '6px',
                  padding: '5px 11px',
                  backgroundColor: 'var(--color-blue-primary, #2563eb)',
                  color: '#ffffff',
                  borderRadius: 'var(--radius-sm, 6px)',
                  fontSize: '11.5px',
                  fontWeight: 600,
                  border: 'none',
                  cursor: 'pointer',
                }}
                title="Jump to error line in Monaco Editor"
              >
                <span>View Bug in Editor</span>
                <ArrowRight size={13} />
              </button>
            )}

            {onClose && (
              <button
                onClick={onClose}
                data-testid="dismiss-proposal-btn"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  padding: '4px',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
                title="Dismiss repair proposal card"
              >
                <X size={15} />
              </button>
            )}
          </div>
        </div>

        {/* Compact File & Location Sub-bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            marginTop: '8px',
            paddingTop: '8px',
            borderTop: '1px solid rgba(255, 255, 255, 0.08)',
            fontSize: '11.5px',
            color: '#94a3b8',
            fontFamily: 'var(--font-mono, monospace)',
            flexWrap: 'wrap',
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#cbd5e1' }}>
            <FileCode size={13} style={{ color: '#38bdf8' }} />
            <span>File:</span>
            <strong style={{ color: '#ffffff', fontWeight: 600 }}>{proposal.file_path}</strong>
          </span>

          <span style={{ color: '#475569' }}>•</span>

          <span style={{ color: '#cbd5e1' }}>
            <span>Line:</span>{' '}
            <strong style={{ color: '#fde047', fontWeight: 700 }}>{proposal.start_line}</strong>
          </span>

          {proposal.language && (
            <>
              <span style={{ color: '#475569' }}>•</span>
              <span
                style={{
                  fontFamily: 'var(--font-sans, sans-serif)',
                  fontSize: '10.5px',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  color: '#93c5fd',
                  backgroundColor: 'rgba(59, 130, 246, 0.15)',
                  padding: '1px 5px',
                  borderRadius: '3px',
                }}
              >
                {proposal.language}
              </span>
            </>
          )}

          <span style={{ color: '#475569' }}>•</span>

          <span style={{ color: '#94a3b8', fontSize: '11px' }}>
            Fingerprint: <code style={{ color: '#cbd5e1' }}>{proposal.source_fingerprint.slice(0, 10)}...</code>
          </span>
        </div>
      </div>

      <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {/* =========================================================================
            B. REPAIR SUMMARY & METRICS ROW
           ========================================================================= */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
            gap: '10px',
          }}
        >
          {/* Status Metric */}
          <div
            style={{
              padding: '8px 12px',
              backgroundColor: isRejected ? '#fef2f2' : needsClarification ? '#fffbeb' : '#f0fdf4',
              border: `1px solid ${isRejected ? '#fecaca' : needsClarification ? '#fde68a' : '#bbf7d0'}`,
              borderRadius: 'var(--radius-sm, 6px)',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px',
            }}
          >
            <span style={{ fontSize: '10px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
              Repair Status
            </span>
            <span
              style={{
                fontSize: '12px',
                fontWeight: 700,
                color: isRejected ? '#dc2626' : needsClarification ? '#b45309' : '#15803d',
                textTransform: 'uppercase',
              }}
            >
              {proposal.repair_status.replace(/_/g, ' ')}
            </span>
          </div>

          {/* Confidence Metric */}
          <div
            style={{
              padding: '8px 12px',
              backgroundColor: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: 'var(--radius-sm, 6px)',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px',
            }}
          >
            <span style={{ fontSize: '10px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
              AI Confidence
            </span>
            <span style={{ fontSize: '12px', fontWeight: 700, color: '#1e293b' }}>
              {proposal.confidence_score}%
            </span>
          </div>

          {/* Validation Overall Status */}
          <div
            style={{
              padding: '8px 12px',
              backgroundColor: proposal.validation_status === 'passed' ? '#f0fdf4' : '#fef2f2',
              border: `1px solid ${proposal.validation_status === 'passed' ? '#bbf7d0' : '#fecaca'}`,
              borderRadius: 'var(--radius-sm, 6px)',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px',
            }}
          >
            <span style={{ fontSize: '10px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
              Patch Validation
            </span>
            <span
              style={{
                fontSize: '12px',
                fontWeight: 700,
                color: proposal.validation_status === 'passed' ? '#15803d' : '#dc2626',
                textTransform: 'uppercase',
              }}
            >
              {proposal.validation_status}
            </span>
          </div>

          {/* Change Stats */}
          <div
            style={{
              padding: '8px 12px',
              backgroundColor: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: 'var(--radius-sm, 6px)',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px',
            }}
          >
            <span style={{ fontSize: '10px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
              Diff Stats
            </span>
            <span style={{ fontSize: '12px', fontWeight: 600, color: '#334155' }}>
              <span style={{ color: '#16a34a' }}>+{proposal.additions}</span>{' '}
              <span style={{ color: '#dc2626' }}>-{proposal.deletions}</span>
            </span>
          </div>
        </div>

        {/* Repair Summary Note */}
        <div
          style={{
            padding: '12px 14px',
            backgroundColor: '#eff6ff',
            border: '1px solid #bfdbfe',
            borderRadius: 'var(--radius-md, 8px)',
          }}
        >
          <div style={{ fontSize: '12px', fontWeight: 700, color: '#1d4ed8', marginBottom: '4px' }}>
            {proposal.repair_summary}
          </div>
          <div style={{ fontSize: '12.5px', color: '#1e3a8a', lineHeight: 1.5 }}>
            {proposal.repair_explanation}
          </div>
        </div>

        {/* =========================================================================
            E. DIFF & CODE PREVIEW CONTROLS & RENDERER
           ========================================================================= */}
        <div
          style={{
            border: '1px solid var(--color-border, #e2e8f0)',
            borderRadius: 'var(--radius-md, 8px)',
            overflow: 'hidden',
          }}
        >
          {/* View Tab Bar & Copy Actions */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              backgroundColor: '#f1f5f9',
              borderBottom: '1px solid var(--color-border, #e2e8f0)',
              padding: '0 8px',
              flexWrap: 'wrap',
              gap: '8px',
            }}
          >
            {/* View Mode Tabs */}
            <div style={{ display: 'flex', alignItems: 'center' }}>
              {[
                { key: 'diff', label: 'Diff Preview', icon: FileDiff },
                { key: 'proposed', label: 'Proposed Code', icon: CheckCircle2 },
                { key: 'original', label: 'Original Code', icon: AlertTriangle },
              ].map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.key;
                return (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key as any)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                      padding: '8px 12px',
                      fontSize: '11.5px',
                      fontWeight: isActive ? 700 : 500,
                      color: isActive ? '#2563eb' : '#64748b',
                      backgroundColor: isActive ? '#ffffff' : 'transparent',
                      border: 'none',
                      borderBottom: isActive ? '2px solid #2563eb' : '2px solid transparent',
                      cursor: 'pointer',
                    }}
                  >
                    <Icon size={12} />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Copy Actions */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 0' }}>
              {activeTab === 'diff' ? (
                <button
                  onClick={() => handleCopy(proposal.diff, true)}
                  data-testid="copy-diff-btn"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '11px',
                    fontWeight: 600,
                    color: '#334155',
                    backgroundColor: '#ffffff',
                    border: '1px solid #cbd5e1',
                    borderRadius: '4px',
                    padding: '3px 8px',
                    cursor: 'pointer',
                  }}
                  title="Copy unified diff"
                >
                  {copiedDiff ? <Check size={12} color="#16a34a" /> : <Copy size={12} />}
                  <span>{copiedDiff ? 'Copied' : 'Copy Diff'}</span>
                </button>
              ) : (
                <button
                  onClick={() => handleCopy(proposal.proposed_code, false)}
                  data-testid="copy-proposed-btn"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '11px',
                    fontWeight: 600,
                    color: '#166534',
                    backgroundColor: '#ffffff',
                    border: '1px solid #86efac',
                    borderRadius: '4px',
                    padding: '3px 8px',
                    cursor: 'pointer',
                  }}
                  title="Copy proposed code"
                >
                  {copiedProposed ? <Check size={12} color="#16a34a" /> : <Copy size={12} />}
                  <span>{copiedProposed ? 'Copied' : 'Copy Proposed Code'}</span>
                </button>
              )}

              {onRegenerate && (
                <button
                  onClick={onRegenerate}
                  disabled={isRegenerating}
                  data-testid="regenerate-btn"
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '11px',
                    fontWeight: 600,
                    color: '#2563eb',
                    backgroundColor: '#ffffff',
                    border: '1px solid #bfdbfe',
                    borderRadius: '4px',
                    padding: '3px 8px',
                    cursor: isRegenerating ? 'not-allowed' : 'pointer',
                  }}
                  title="Regenerate proposal with Gemini"
                >
                  <RefreshCw size={11} className={isRegenerating ? 'animate-spin' : ''} />
                  <span>{isRegenerating ? 'Regenerating...' : 'Regenerate'}</span>
                </button>
              )}
            </div>
          </div>

          {/* Code Body Area */}
          <div
            style={{
              backgroundColor: '#0f172a',
              padding: '12px',
              overflowX: 'auto',
              maxHeight: '380px',
            }}
          >
            {activeTab === 'diff' && renderDiffLines(proposal.diff)}

            {activeTab === 'proposed' && (
              <pre
                style={{
                  margin: 0,
                  fontFamily: 'var(--font-mono, monospace)',
                  fontSize: '12px',
                  color: '#ecfdf5',
                  lineHeight: 1.5,
                  whiteSpace: 'pre-wrap',
                }}
              >
                <code>{proposal.proposed_code}</code>
              </pre>
            )}

            {activeTab === 'original' && (
              <pre
                style={{
                  margin: 0,
                  fontFamily: 'var(--font-mono, monospace)',
                  fontSize: '12px',
                  color: '#f1f5f9',
                  lineHeight: 1.5,
                  whiteSpace: 'pre-wrap',
                }}
              >
                <code>{proposal.original_code}</code>
              </pre>
            )}
          </div>
        </div>

        {/* =========================================================================
            F. DETERMINISTIC VALIDATION CHECKLIST
           ========================================================================= */}
        <div
          style={{
            backgroundColor: 'var(--color-surface, #ffffff)',
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
              backgroundColor: 'var(--color-surface-subtle, #f8fafc)',
              border: 'none',
              cursor: 'pointer',
              textAlign: 'left',
            }}
          >
            <span
              style={{
                fontSize: '11.5px',
                fontWeight: 700,
                color: 'var(--color-navy-800, #1e293b)',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                textTransform: 'uppercase',
                letterSpacing: '0.03em',
              }}
            >
              <Terminal size={13} style={{ color: '#2563eb' }} />
              <span>Deterministic Patch Validation Details</span>
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  padding: '1px 6px',
                  borderRadius: '10px',
                  backgroundColor: proposal.validation_status === 'passed' ? '#dcfce7' : '#fee2e2',
                  color: proposal.validation_status === 'passed' ? '#15803d' : '#b91c1c',
                }}
              >
                {proposal.validation_status.toUpperCase()}
              </span>
            </span>
            {showValidationDetails ? (
              <ChevronUp size={14} style={{ color: '#64748b' }} />
            ) : (
              <ChevronDown size={14} style={{ color: '#64748b' }} />
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
            G. ASSUMPTIONS (Collapsible, only if available)
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
            H. AI METADATA FOOTER
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

          <span style={{ fontSize: '10.5px', color: '#94a3b8' }}>
            Phase 6 Review Only • No source files written
          </span>
        </div>
      </div>
    </div>
  );
};
