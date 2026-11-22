import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  ShieldCheck,
  History,
  RefreshCw,
  X,
  Loader2,
  Play,
} from 'lucide-react';
import { VerificationReportResponse } from '../../types/api';
import { apiClient } from '../../services/apiClient';

interface RepairVerificationCardProps {
  report: VerificationReportResponse;
  projectId: string;
  proposalId: string;
  onReverify?: () => void;
  isVerifying?: boolean;
  onClose?: () => void;
  onRunInSandbox?: (filePath: string) => void;
}

export const RepairVerificationCard: React.FC<RepairVerificationCardProps> = ({
  report: initialReport,
  projectId,
  proposalId,
  onReverify,
  isVerifying = false,
  onClose,
  onRunInSandbox,
}) => {
  const [report, setReport] = useState<VerificationReportResponse>(initialReport);
  const [showHistory, setShowHistory] = useState(false);
  const [historyList, setHistoryList] = useState<VerificationReportResponse[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  React.useEffect(() => {
    setReport(initialReport);
  }, [initialReport]);

  const fetchHistory = async () => {
    if (!showHistory) {
      setIsLoadingHistory(true);
      try {
        const res = await apiClient.getRepairVerificationHistory(projectId, proposalId);
        setHistoryList(res.verifications || []);
      } catch (err: unknown) {
        console.error('Failed to load verification history', err);
      } finally {
        setIsLoadingHistory(false);
      }
    }
    setShowHistory(!showHistory);
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'verified':
        return {
          bg: '#ecfdf5',
          border: '#10b981',
          text: '#065f46',
          icon: <CheckCircle2 size={13} style={{ color: '#10b981' }} />,
          label: 'VERIFIED',
        };
      case 'failed':
        return {
          bg: '#fef2f2',
          border: '#ef4444',
          text: '#991b1b',
          icon: <XCircle size={13} style={{ color: '#ef4444' }} />,
          label: 'FAILED',
        };
      case 'partial':
        return {
          bg: '#fffbeb',
          border: '#f59e0b',
          text: '#92400e',
          icon: <AlertTriangle size={13} style={{ color: '#f59e0b' }} />,
          label: 'PARTIAL',
        };
      case 'stale':
        return {
          bg: '#fffbeb',
          border: '#f59e0b',
          text: '#92400e',
          icon: <AlertTriangle size={13} style={{ color: '#f59e0b' }} />,
          label: 'STALE',
        };
      default:
        return {
          bg: '#f5f3ff',
          border: '#8b5cf6',
          text: '#5b21b6',
          icon: <HelpCircle size={13} style={{ color: '#8b5cf6' }} />,
          label: 'INCONCLUSIVE',
        };
    }
  };

  const currentBadge = getStatusBadge(report.overall_status);

  return (
    <div
      data-testid="repair-verification-card"
      style={{
        backgroundColor: '#ffffff',
        border: `1px solid ${currentBadge.border}`,
        borderRadius: '10px',
        overflow: 'hidden',
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
        marginTop: '12px',
        fontFamily: 'var(--font-sans, sans-serif)',
      }}
    >
      {/* =========================================================================
          VERIFICATION HEADER
         ========================================================================= */}
      <div
        style={{
          backgroundColor: '#0f172a',
          color: '#ffffff',
          padding: '12px 16px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ShieldCheck size={16} style={{ color: '#38bdf8' }} />
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '13px', fontWeight: 700, letterSpacing: '0.02em' }}>
                Automated Verification Report
              </span>
              <span
                data-testid="verification-status-badge"
                style={{
                  fontSize: '10.5px',
                  fontWeight: 800,
                  letterSpacing: '0.05em',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  backgroundColor: currentBadge.bg,
                  color: currentBadge.text,
                  border: `1px solid ${currentBadge.border}`,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                {currentBadge.icon}
                <span>{currentBadge.label}</span>
              </span>
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>
              Verified: <code style={{ color: '#38bdf8' }}>{report.file_path}</code> • Duration: {report.duration_ms}ms
            </div>
          </div>
        </div>

        {/* Action Controls: Re-verify & History */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {onRunInSandbox && report.overall_status.toLowerCase() === 'verified' && (
            <button
              onClick={() => onRunInSandbox(report.file_path)}
              data-testid="run-verified-sandbox-btn"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                padding: '5px 10px',
                backgroundColor: 'rgba(56, 189, 248, 0.15)',
                color: '#38bdf8',
                borderRadius: '6px',
                border: '1px solid rgba(56, 189, 248, 0.4)',
                fontSize: '11.5px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
              title="Execute verified repaired file in isolated Docker sandbox"
            >
              <Play size={12} fill="#38bdf8" />
              <span>Run in Sandbox</span>
            </button>
          )}

          {onReverify && (
            <button
              onClick={onReverify}
              disabled={isVerifying}
              data-testid="reverify-btn"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                padding: '5px 10px',
                backgroundColor: 'rgba(255, 255, 255, 0.08)',
                color: '#cbd5e1',
                borderRadius: '6px',
                border: '1px solid rgba(255, 255, 255, 0.15)',
                fontSize: '11.5px',
                fontWeight: 600,
                cursor: isVerifying ? 'not-allowed' : 'pointer',
              }}
              title="Re-run static automated verification"
            >
              <RefreshCw size={12} className={isVerifying ? 'animate-spin' : ''} />
              <span>{isVerifying ? 'Verifying...' : 'Re-verify'}</span>
            </button>
          )}

          <button
            onClick={fetchHistory}
            data-testid="verification-history-btn"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              padding: '5px 10px',
              backgroundColor: 'transparent',
              color: '#94a3b8',
              borderRadius: '6px',
              border: '1px solid rgba(255, 255, 255, 0.15)',
              fontSize: '11.5px',
              fontWeight: 500,
              cursor: 'pointer',
            }}
            title="View verification run history"
          >
            <History size={12} />
            <span>{showHistory ? 'Hide History' : 'History'}</span>
          </button>

          {onClose && (
            <button
              onClick={onClose}
              data-testid="close-verification-card-btn"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '28px',
                height: '28px',
                backgroundColor: 'rgba(255, 255, 255, 0.08)',
                color: '#94a3b8',
                borderRadius: '6px',
                border: 'none',
                cursor: 'pointer',
              }}
              title="Close report view"
            >
              <X size={15} />
            </button>
          )}
        </div>
      </div>

      {/* =========================================================================
          VERIFICATION HISTORY DRAWER (Collapsible)
         ========================================================================= */}
      {showHistory && (
        <div
          data-testid="verification-history-drawer"
          style={{
            backgroundColor: '#1e293b',
            color: '#e2e8f0',
            padding: '10px 16px',
            borderBottom: '1px solid #334155',
            fontSize: '11.5px',
          }}
        >
          <div style={{ fontWeight: 700, color: '#38bdf8', marginBottom: '6px' }}>
            Verification Attempt History ({historyList.length})
          </div>
          {isLoadingHistory ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#94a3b8' }}>
              <Loader2 size={13} className="animate-spin" />
              <span>Loading verification history...</span>
            </div>
          ) : historyList.length === 0 ? (
            <div style={{ fontStyle: 'italic', color: '#64748b' }}>No previous verification runs.</div>
          ) : (
            <div data-testid="verification-history-list" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              {historyList.map((item, idx) => (
                <div
                  key={item.id || idx}
                  data-testid="verification-history-item"
                  onClick={() => setReport(item)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    backgroundColor: item.id === report.id ? '#334155' : 'rgba(255, 255, 255, 0.04)',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontWeight: 700, textTransform: 'uppercase', color: item.overall_status === 'verified' ? '#86efac' : '#fca5a5' }}>
                      Run #{historyList.length - idx} • {item.overall_status}
                    </span>
                    <span style={{ color: '#94a3b8' }}>
                      Target: {item.target_bug_status} • Regressions: {item.comparison?.regression_count ?? (item as any).regression_count ?? 0}
                    </span>
                  </div>
                  <span style={{ color: '#64748b', fontSize: '10.5px' }}>
                    {new Date(item.created_at).toLocaleTimeString()} ({item.duration_ms}ms)
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          BODY: METRICS & CHECKS BREAKDOWN
         ========================================================================= */}
      <div style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {/* Metric Cards Grid */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
            gap: '10px',
          }}
        >
          <div
            style={{
              padding: '10px 12px',
              backgroundColor: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>Before Bugs</div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: '#1e293b' }}>
              {report.comparison.before_count}
            </div>
          </div>

          <div
            style={{
              padding: '10px 12px',
              backgroundColor: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>After Bugs</div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: '#1e293b' }}>
              {report.comparison.after_count}
            </div>
          </div>

          <div
            style={{
              padding: '10px 12px',
              backgroundColor: '#ecfdf5',
              border: '1px solid #a7f3d0',
              borderRadius: '8px',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: '11px', color: '#047857', fontWeight: 600 }}>Resolved</div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: '#065f46' }}>
              {report.comparison.resolved_count}
            </div>
          </div>

          <div
            style={{
              padding: '10px 12px',
              backgroundColor: report.comparison.regression_count > 0 ? '#fef2f2' : '#f8fafc',
              border: report.comparison.regression_count > 0 ? '1px solid #fecaca' : '1px solid #e2e8f0',
              borderRadius: '8px',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: '11px', color: report.comparison.regression_count > 0 ? '#b91c1c' : '#64748b', fontWeight: 600 }}>
              Regressions
            </div>
            <div style={{ fontSize: '18px', fontWeight: 800, color: report.comparison.regression_count > 0 ? '#dc2626' : '#16a34a' }}>
              {report.comparison.regression_count}
            </div>
          </div>
        </div>

        {/* Check Results Checklist */}
        <div style={{ border: '1px solid #e2e8f0', borderRadius: '8px', overflow: 'hidden' }}>
          <div
            style={{
              padding: '8px 14px',
              backgroundColor: '#f8fafc',
              borderBottom: '1px solid #e2e8f0',
              fontSize: '11.5px',
              fontWeight: 700,
              color: '#334155',
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
            }}
          >
            Deterministic Static Checks ({report.checks.length})
          </div>

          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {report.checks.map((check, idx) => {
              const isPass = check.status === 'passed';
              const isFail = check.status === 'failed';
              const isWarn = check.status === 'warning';

              return (
                <div
                  key={idx}
                  style={{
                    padding: '10px 14px',
                    borderBottom: idx < report.checks.length - 1 ? '1px solid #f1f5f9' : 'none',
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between',
                    gap: '12px',
                    backgroundColor: isFail ? '#fff5f5' : isWarn ? '#fffbeb' : '#ffffff',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', flex: 1 }}>
                    {isPass ? (
                      <CheckCircle2 size={15} style={{ color: '#16a34a', flexShrink: 0, marginTop: '2px' }} />
                    ) : isFail ? (
                      <XCircle size={15} style={{ color: '#dc2626', flexShrink: 0, marginTop: '2px' }} />
                    ) : isWarn ? (
                      <AlertTriangle size={15} style={{ color: '#d97706', flexShrink: 0, marginTop: '2px' }} />
                    ) : (
                      <HelpCircle size={15} style={{ color: '#64748b', flexShrink: 0, marginTop: '2px' }} />
                    )}

                    <div>
                      <div style={{ fontSize: '12px', fontWeight: 700, color: '#1e293b' }}>
                        {check.name.replace(/_/g, ' ').toUpperCase()}
                      </div>
                      <div style={{ fontSize: '11.5px', color: '#475569', marginTop: '2px' }}>
                        {check.message}
                      </div>

                      {check.details && (
                        <div
                          style={{
                            marginTop: '6px',
                            padding: '6px 10px',
                            backgroundColor: 'rgba(0,0,0,0.04)',
                            borderRadius: '4px',
                            fontFamily: 'var(--font-mono, monospace)',
                            fontSize: '11px',
                            color: '#334155',
                            whiteSpace: 'pre-wrap',
                          }}
                        >
                          {check.details}
                        </div>
                      )}
                    </div>
                  </div>

                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 800,
                      padding: '2px 6px',
                      borderRadius: '4px',
                      textTransform: 'uppercase',
                      backgroundColor: isPass ? '#ecfdf5' : isFail ? '#fef2f2' : isWarn ? '#fffbeb' : '#f1f5f9',
                      color: isPass ? '#059669' : isFail ? '#dc2626' : isWarn ? '#b45309' : '#64748b',
                      border: `1px solid ${isPass ? '#a7f3d0' : isFail ? '#fecaca' : isWarn ? '#fde68a' : '#cbd5e1'}`,
                      flexShrink: 0,
                    }}
                  >
                    {check.status}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* =========================================================================
            REGRESSION FINDINGS LIST (If new bugs introduced)
           ========================================================================= */}
        {report.comparison.new_findings && report.comparison.new_findings.length > 0 && (
          <div
            data-testid="regression-findings-box"
            style={{
              padding: '12px 14px',
              backgroundColor: '#fef2f2',
              border: '1px solid #fecaca',
              borderRadius: '8px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#991b1b', fontWeight: 700, fontSize: '12px', marginBottom: '8px' }}>
              <AlertTriangle size={15} style={{ color: '#dc2626' }} />
              <span>REGRESSIONS DETECTED ({report.comparison.new_findings.length})</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {report.comparison.new_findings.map((f, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '8px 10px',
                    backgroundColor: '#ffffff',
                    border: '1px solid #fca5a5',
                    borderRadius: '6px',
                    fontSize: '11.5px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', marginBottom: '4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontFamily: 'var(--font-mono, monospace)', fontWeight: 700, color: '#dc2626', backgroundColor: '#fee2e2', padding: '1px 5px', borderRadius: '3px' }}>
                        {f.rule_id}
                      </span>
                      <strong style={{ color: '#1e293b' }}>{f.rule_name}</strong>
                    </div>
                    <span style={{ fontSize: '10.5px', color: '#64748b' }}>Line {f.start_line}</span>
                  </div>

                  <div style={{ color: '#475569', marginBottom: '4px' }}>{f.message}</div>

                  {f.evidence && (
                    <pre
                      style={{
                        margin: 0,
                        padding: '4px 8px',
                        backgroundColor: '#0f172a',
                        color: '#f8fafc',
                        borderRadius: '4px',
                        fontSize: '10.5px',
                        fontFamily: 'var(--font-mono, monospace)',
                      }}
                    >
                      {f.evidence}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer Notice */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '10.5px',
            color: '#94a3b8',
            paddingTop: '6px',
            borderTop: '1px solid #f1f5f9',
            flexWrap: 'wrap',
            gap: '6px',
          }}
        >
          <span>
            Target Bug: <strong style={{ color: '#0f172a' }}>{report.comparison.target_rule_id}</strong> ({report.target_bug_status.toUpperCase()})
          </span>
          <span>
            Phase 8 Static Verification • Zero code executed • Advisory static validation
          </span>
        </div>
      </div>
    </div>
  );
};

