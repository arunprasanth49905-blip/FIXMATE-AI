import React, { useState } from 'react';
import {
  Terminal,
  X,
  Maximize2,
  Minimize2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Shield,
  Layers,
  History,
  Copy,
  Check,
  RotateCw,
  Cpu,
  HardDrive,
  WifiOff,
  UserCheck,
  AlertOctagon,
} from 'lucide-react';
import { SandboxExecutionResponse, SandboxStatusResponse } from '../../types/api';

interface SandboxConsoleDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  currentExecution: SandboxExecutionResponse | null;
  isLoading: boolean;
  history: SandboxExecutionResponse[];
  onSelectHistoryItem: (item: SandboxExecutionResponse) => void;
  sandboxStatus: SandboxStatusResponse | null;
  onRerun?: () => void;
}

export const SandboxConsoleDrawer: React.FC<SandboxConsoleDrawerProps> = ({
  isOpen,
  onClose,
  currentExecution,
  isLoading,
  history,
  onSelectHistoryItem,
  sandboxStatus,
  onRerun,
}) => {
  const [activeTab, setActiveTab] = useState<'console' | 'tests' | 'security' | 'history'>('console');
  const [streamFilter, setStreamFilter] = useState<'all' | 'stdout' | 'stderr'>('all');
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleCopy = () => {
    if (!currentExecution) return;
    const text =
      streamFilter === 'stdout'
        ? currentExecution.stdout
        : streamFilter === 'stderr'
        ? currentExecution.stderr
        : `--- STDOUT ---\n${currentExecution.stdout}\n\n--- STDERR ---\n${currentExecution.stderr}`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PASSED':
        return (
          <span
            data-testid="execution-badge-passed"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '2px 8px',
              borderRadius: '12px',
              fontSize: '11px',
              fontWeight: 700,
              backgroundColor: '#ecfdf5',
              color: '#065f46',
              border: '1px solid #10b981',
            }}
          >
            <CheckCircle2 size={12} color="#10b981" /> PASSED
          </span>
        );
      case 'FAILED':
        return (
          <span
            data-testid="execution-badge-failed"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '2px 8px',
              borderRadius: '12px',
              fontSize: '11px',
              fontWeight: 700,
              backgroundColor: '#fef2f2',
              color: '#991b1b',
              border: '1px solid #ef4444',
            }}
          >
            <XCircle size={12} color="#ef4444" /> FAILED
          </span>
        );
      case 'TIMEOUT':
        return (
          <span
            data-testid="execution-badge-timeout"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '2px 8px',
              borderRadius: '12px',
              fontSize: '11px',
              fontWeight: 700,
              backgroundColor: '#fffbeb',
              color: '#92400e',
              border: '1px solid #f59e0b',
            }}
          >
            <Clock size={12} color="#f59e0b" /> TIMEOUT
          </span>
        );
      case 'SANDBOX_UNAVAILABLE':
        return (
          <span
            data-testid="execution-badge-unavailable"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '2px 8px',
              borderRadius: '12px',
              fontSize: '11px',
              fontWeight: 700,
              backgroundColor: '#fdf4ff',
              color: '#86198f',
              border: '1px solid #d946ef',
            }}
          >
            <AlertOctagon size={12} color="#d946ef" /> SANDBOX UNAVAILABLE
          </span>
        );
      default:
        return (
          <span
            data-testid="execution-badge-default"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '2px 8px',
              borderRadius: '12px',
              fontSize: '11px',
              fontWeight: 700,
              backgroundColor: '#f1f5f9',
              color: '#334155',
              border: '1px solid #cbd5e1',
            }}
          >
            <AlertTriangle size={12} color="#64748b" /> {status}
          </span>
        );
    }
  };

  return (
    <div
      data-testid="sandbox-console-drawer"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        height: isExpanded ? '85vh' : '420px',
        backgroundColor: '#0f172a',
        borderTop: '2px solid #334155',
        boxShadow: '0 -10px 25px -5px rgba(0, 0, 0, 0.4)',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        transition: 'height 0.2s ease',
        color: '#f8fafc',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      {/* 1. Drawer Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 16px',
          backgroundColor: '#1e293b',
          borderBottom: '1px solid #334155',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Terminal size={17} style={{ color: '#38bdf8' }} />
          <span style={{ fontSize: '13px', fontWeight: 700, letterSpacing: '-0.01em', color: '#f8fafc' }}>
            Sandbox Execution Console
          </span>

          {isLoading ? (
            <span
              data-testid="sandbox-running-indicator"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                fontSize: '11.5px',
                color: '#38bdf8',
                backgroundColor: 'rgba(56, 189, 248, 0.1)',
                padding: '2px 8px',
                borderRadius: '10px',
                fontWeight: 600,
              }}
            >
              <RotateCw size={12} className="animate-spin" />
              Running in sandbox...
            </span>
          ) : currentExecution ? (
            <>
              {getStatusBadge(currentExecution.status)}
              <span style={{ fontSize: '11.5px', color: '#94a3b8' }}>
                {currentExecution.file_path} ({currentExecution.language})
              </span>
              <span style={{ fontSize: '11px', color: '#64748b' }}>
                {currentExecution.duration_ms}ms
              </span>
              {currentExecution.exit_code !== null && (
                <span
                  style={{
                    fontSize: '10.5px',
                    padding: '1px 5px',
                    borderRadius: '4px',
                    backgroundColor: currentExecution.exit_code === 0 ? '#14532d' : '#7f1d1d',
                    color: currentExecution.exit_code === 0 ? '#86efac' : '#fca5a5',
                    fontFamily: 'monospace',
                  }}
                >
                  exit {currentExecution.exit_code}
                </span>
              )}
            </>
          ) : (
            <span style={{ fontSize: '11.5px', color: '#94a3b8' }}>Ready</span>
          )}
        </div>

        {/* Tab Selection */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <button
            onClick={() => setActiveTab('console')}
            data-testid="tab-console"
            style={{
              padding: '4px 10px',
              fontSize: '12px',
              fontWeight: 600,
              backgroundColor: activeTab === 'console' ? '#0f172a' : 'transparent',
              color: activeTab === 'console' ? '#38bdf8' : '#94a3b8',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <Terminal size={13} />
            Console
          </button>

          {currentExecution?.execution_type === 'test' && (
            <button
              onClick={() => setActiveTab('tests')}
              data-testid="tab-tests"
              style={{
                padding: '4px 10px',
                fontSize: '12px',
                fontWeight: 600,
                backgroundColor: activeTab === 'tests' ? '#0f172a' : 'transparent',
                color: activeTab === 'tests' ? '#38bdf8' : '#94a3b8',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              <Layers size={13} />
              Test Summary
            </button>
          )}

          <button
            onClick={() => setActiveTab('security')}
            data-testid="tab-security"
            style={{
              padding: '4px 10px',
              fontSize: '12px',
              fontWeight: 600,
              backgroundColor: activeTab === 'security' ? '#0f172a' : 'transparent',
              color: activeTab === 'security' ? '#38bdf8' : '#94a3b8',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <Shield size={13} />
            Security Profile
          </button>

          <button
            onClick={() => setActiveTab('history')}
            data-testid="tab-history"
            style={{
              padding: '4px 10px',
              fontSize: '12px',
              fontWeight: 600,
              backgroundColor: activeTab === 'history' ? '#0f172a' : 'transparent',
              color: activeTab === 'history' ? '#38bdf8' : '#94a3b8',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <History size={13} />
            History ({history.length})
          </button>

          <div style={{ width: '1px', height: '16px', backgroundColor: '#334155', margin: '0 4px' }} />

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? 'Minimize drawer' : 'Maximize drawer'}
            data-testid="toggle-expand-btn"
            style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px' }}
          >
            {isExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>

          <button
            onClick={onClose}
            title="Close console drawer"
            data-testid="close-console-btn"
            style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px' }}
          >
            <X size={15} />
          </button>
        </div>
      </div>

      {/* 2. Drawer Body */}
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
        {/* TAB A: CONSOLE OUTPUT */}
        {activeTab === 'console' && (
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {/* Console Toolbar */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 14px',
                backgroundColor: '#0f172a',
                borderBottom: '1px solid #1e293b',
                fontSize: '11.5px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: '#64748b' }}>Filter:</span>
                {(['all', 'stdout', 'stderr'] as const).map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setStreamFilter(filter)}
                    style={{
                      padding: '2px 8px',
                      borderRadius: '4px',
                      border: 'none',
                      fontSize: '11px',
                      fontWeight: streamFilter === filter ? 700 : 500,
                      backgroundColor: streamFilter === filter ? '#334155' : 'transparent',
                      color: streamFilter === filter ? '#f8fafc' : '#94a3b8',
                      cursor: 'pointer',
                      textTransform: 'uppercase',
                    }}
                  >
                    {filter}
                  </button>
                ))}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                {onRerun && !isLoading && (
                  <button
                    onClick={onRerun}
                    data-testid="rerun-execution-btn"
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      background: 'none',
                      border: 'none',
                      color: '#38bdf8',
                      fontSize: '11px',
                      fontWeight: 600,
                      cursor: 'pointer',
                    }}
                  >
                    <RotateCw size={11} /> Re-run
                  </button>
                )}
                <button
                  onClick={handleCopy}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    background: 'none',
                    border: 'none',
                    color: '#94a3b8',
                    fontSize: '11px',
                    cursor: 'pointer',
                  }}
                >
                  {copied ? <Check size={12} color="#10b981" /> : <Copy size={12} />}
                  <span>{copied ? 'Copied' : 'Copy Output'}</span>
                </button>
              </div>
            </div>

            {/* Terminal Screen */}
            <div
              data-testid="sandbox-terminal-output"
              style={{
                flex: 1,
                padding: '14px',
                fontFamily: 'Consolas, "Fira Code", Monaco, monospace',
                fontSize: '12px',
                lineHeight: 1.5,
                overflowY: 'auto',
                backgroundColor: '#090d16',
                color: '#e2e8f0',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}
            >
              {currentExecution?.status === 'SANDBOX_UNAVAILABLE' ? (
                <div
                  data-testid="sandbox-unavailable-warning"
                  style={{
                    padding: '14px',
                    backgroundColor: 'rgba(217, 70, 239, 0.08)',
                    border: '1px solid rgba(217, 70, 239, 0.3)',
                    borderRadius: '8px',
                    color: '#f5d0fe',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 700, fontSize: '13px' }}>
                    <AlertOctagon size={16} color="#d946ef" />
                    Docker Container Runtime Unavailable (Execution Blocked)
                  </div>
                  <p style={{ marginTop: '8px', fontSize: '12px', color: '#e879f9', lineHeight: 1.5 }}>
                    {currentExecution.runtime_error ||
                      'Docker is not running on this host. For critical security, FIXMATE AI strictly refuses to fall back to executing user code directly on the host operating system.'}
                  </p>
                  <div style={{ marginTop: '10px', fontSize: '11.5px', color: '#cbd5e1' }}>
                    <strong>To enable isolated runtime execution:</strong>
                    <ol style={{ paddingLeft: '18px', marginTop: '4px' }}>
                      <li>Start Docker Desktop on your machine.</li>
                      <li>Ensure Linux containers are enabled.</li>
                      <li>Click "Re-run" or trigger execution again once Docker is active.</li>
                    </ol>
                  </div>
                </div>
              ) : currentExecution?.runtime_error && currentExecution.status !== 'PASSED' ? (
                <div
                  data-testid="runtime-error-callout"
                  style={{
                    padding: '10px 12px',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    borderLeft: '3px solid #ef4444',
                    marginBottom: '12px',
                    color: '#fca5a5',
                  }}
                >
                  <strong style={{ color: '#ef4444' }}>Runtime Error: </strong>
                  {currentExecution.runtime_error}
                </div>
              ) : null}

              {/* Render Output Content */}
              {streamFilter === 'stdout' && (currentExecution?.stdout || '(No stdout)')}
              {streamFilter === 'stderr' && (currentExecution?.stderr || '(No stderr)')}
              {streamFilter === 'all' && (
                <>
                  {currentExecution?.stdout && (
                    <div style={{ color: '#86efac' }}>{currentExecution.stdout}</div>
                  )}
                  {currentExecution?.stderr && (
                    <div style={{ color: '#fca5a5', marginTop: currentExecution.stdout ? '8px' : 0 }}>
                      {currentExecution.stderr}
                    </div>
                  )}
                  {!currentExecution?.stdout && !currentExecution?.stderr && !currentExecution?.runtime_error && (
                    <span style={{ color: '#64748b' }}>(Execution produced no output)</span>
                  )}
                </>
              )}
            </div>
          </div>
        )}

        {/* TAB B: TEST SUMMARY */}
        {activeTab === 'tests' && currentExecution?.test_summary && (
          <div data-testid="test-summary-view" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px' }}>
              <div style={{ padding: '12px', backgroundColor: '#1e293b', borderRadius: '6px', border: '1px solid #334155' }}>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}>Total Tests</div>
                <div data-testid="test-summary-total" style={{ fontSize: '20px', fontWeight: 800, color: '#f8fafc', marginTop: '4px' }}>
                  {currentExecution.test_summary.total}
                </div>
              </div>
              <div style={{ padding: '12px', backgroundColor: '#064e3b', borderRadius: '6px', border: '1px solid #059669' }}>
                <div style={{ fontSize: '11px', color: '#a7f3d0' }}>Passed</div>
                <div data-testid="test-summary-passed" style={{ fontSize: '20px', fontWeight: 800, color: '#ecfdf5', marginTop: '4px' }}>
                  {currentExecution.test_summary.passed}
                </div>
              </div>
              <div style={{ padding: '12px', backgroundColor: '#7f1d1d', borderRadius: '6px', border: '1px solid #dc2626' }}>
                <div style={{ fontSize: '11px', color: '#fecaca' }}>Failed</div>
                <div data-testid="test-summary-failed" style={{ fontSize: '20px', fontWeight: 800, color: '#fef2f2', marginTop: '4px' }}>
                  {currentExecution.test_summary.failed}
                </div>
              </div>
              <div style={{ padding: '12px', backgroundColor: '#78350f', borderRadius: '6px', border: '1px solid #d97706' }}>
                <div style={{ fontSize: '11px', color: '#fde68a' }}>Errors / Skipped</div>
                <div data-testid="test-summary-errors" style={{ fontSize: '20px', fontWeight: 800, color: '#fffbeb', marginTop: '4px' }}>
                  {currentExecution.test_summary.errors + currentExecution.test_summary.skipped}
                </div>
              </div>
            </div>

            <div style={{ padding: '12px', backgroundColor: '#1e293b', borderRadius: '6px', fontSize: '12px' }}>
              <div><strong>Framework:</strong> {currentExecution.test_summary.framework}</div>
              {currentExecution.test_summary.details && (
                <div style={{ marginTop: '4px', color: '#94a3b8' }}>{currentExecution.test_summary.details}</div>
              )}
            </div>
          </div>
        )}

        {/* TAB C: SECURITY PROFILE */}
        {activeTab === 'security' && (
          <div data-testid="security-profile-view" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ fontSize: '13px', fontWeight: 700, color: '#38bdf8' }}>
              Active Container Hardening Profile
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px' }}>
              <div style={{ padding: '12px', backgroundColor: '#1e293b', borderRadius: '6px', border: '1px solid #334155' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#38bdf8' }}>
                  <WifiOff size={14} /> Network Isolation
                </div>
                <div style={{ fontSize: '11.5px', color: '#cbd5e1', marginTop: '6px' }}>
                  Disabled (--network none). Zero internet or host LAN access.
                </div>
              </div>

              <div style={{ padding: '12px', backgroundColor: '#1e293b', borderRadius: '6px', border: '1px solid #334155' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#38bdf8' }}>
                  <HardDrive size={14} /> Filesystem Protection
                </div>
                <div style={{ fontSize: '11.5px', color: '#cbd5e1', marginTop: '6px' }}>
                  Read-only root. Ephemeral staging copy mounted :ro. Original project files never mounted writable.
                </div>
              </div>

              <div style={{ padding: '12px', backgroundColor: '#1e293b', borderRadius: '6px', border: '1px solid #334155' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#38bdf8' }}>
                  <UserCheck size={14} /> Non-Root Privileges
                </div>
                <div style={{ fontSize: '11.5px', color: '#cbd5e1', marginTop: '6px' }}>
                  Runs as unprivileged user 1000:1000 with --cap-drop ALL and no-new-privileges.
                </div>
              </div>

              <div style={{ padding: '12px', backgroundColor: '#1e293b', borderRadius: '6px', border: '1px solid #334155' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#38bdf8' }}>
                  <Cpu size={14} /> Quota Enforcements
                </div>
                <div style={{ fontSize: '11.5px', color: '#cbd5e1', marginTop: '6px' }}>
                  RAM: {currentExecution?.resource_limits?.memory_mb || 256}MB | CPU: {currentExecution?.resource_limits?.cpus || 1.0} | PIDs: {currentExecution?.resource_limits?.pids || 64}
                </div>
              </div>
            </div>

            {sandboxStatus && (
              <div style={{ padding: '12px', backgroundColor: '#090d16', borderRadius: '6px', fontSize: '11.5px', color: '#94a3b8' }}>
                <strong>Host Container Runtime:</strong> {sandboxStatus.runtime} ({sandboxStatus.version || 'Version info unavailable'})
                <div style={{ marginTop: '4px' }}>{sandboxStatus.message}</div>
              </div>
            )}
          </div>
        )}

        {/* TAB D: EXECUTION HISTORY */}
        {activeTab === 'history' && (
          <div data-testid="execution-history-view" style={{ padding: '14px', overflowY: 'auto' }}>
            {history.length === 0 ? (
              <div style={{ textAlign: 'center', color: '#64748b', padding: '30px 0' }}>
                No past executions recorded for this project yet.
              </div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8', textAlign: 'left' }}>
                    <th style={{ padding: '8px' }}>Status</th>
                    <th style={{ padding: '8px' }}>Type</th>
                    <th style={{ padding: '8px' }}>File</th>
                    <th style={{ padding: '8px' }}>Duration</th>
                    <th style={{ padding: '8px' }}>Timestamp</th>
                    <th style={{ padding: '8px', textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((h) => (
                    <tr
                      key={h.id}
                      style={{
                        borderBottom: '1px solid #1e293b',
                        backgroundColor: currentExecution?.id === h.id ? '#1e293b' : 'transparent',
                      }}
                    >
                      <td style={{ padding: '8px' }}>{getStatusBadge(h.status)}</td>
                      <td style={{ padding: '8px', textTransform: 'uppercase', fontSize: '11px', color: '#cbd5e1' }}>
                        {h.execution_type}
                      </td>
                      <td style={{ padding: '8px', color: '#f8fafc', fontFamily: 'monospace' }}>
                        {h.file_path}
                      </td>
                      <td style={{ padding: '8px', color: '#94a3b8' }}>{h.duration_ms}ms</td>
                      <td style={{ padding: '8px', color: '#64748b' }}>
                        {new Date(h.created_at).toLocaleTimeString()}
                      </td>
                      <td style={{ padding: '8px', textAlign: 'right' }}>
                        <button
                          onClick={() => {
                            onSelectHistoryItem(h);
                            setActiveTab('console');
                          }}
                          data-testid={`view-history-${h.id}`}
                          style={{
                            padding: '3px 8px',
                            backgroundColor: '#334155',
                            color: '#38bdf8',
                            border: 'none',
                            borderRadius: '4px',
                            fontSize: '11px',
                            cursor: 'pointer',
                          }}
                        >
                          View Output
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
