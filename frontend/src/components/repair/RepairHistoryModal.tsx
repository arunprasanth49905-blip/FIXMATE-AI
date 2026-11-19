import React, { useState, useEffect } from 'react';
import { History, X, Clock, FileCode, ArrowRight } from 'lucide-react';
import { RepairProposal } from '../../types/api';
import { apiClient } from '../../services/apiClient';

interface RepairHistoryModalProps {
  isOpen?: boolean;
  projectId: string;
  findingId?: string;
  onSelectProposal: (proposal: RepairProposal) => void;
  onClose: () => void;
}

export const RepairHistoryModal: React.FC<RepairHistoryModalProps> = ({
  isOpen = true,
  projectId,
  findingId,
  onSelectProposal,
  onClose,
}) => {
  const [proposals, setProposals] = useState<RepairProposal[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    let isMounted = true;
    const fetchHistory = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const res = await apiClient.getRepairHistory(projectId, findingId, 30);
        if (isMounted) {
          setProposals(res.proposals || []);
        }
      } catch (err: unknown) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Failed to load repair history');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchHistory();
    return () => {
      isMounted = false;
    };
  }, [projectId, findingId, isOpen]);

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(3px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '680px',
          maxHeight: '80vh',
          backgroundColor: '#ffffff',
          borderRadius: '12px',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            backgroundColor: '#0f172a',
            color: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <History size={16} style={{ color: '#38bdf8' }} />
            <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600 }}>
              Repair Proposal History
            </h3>
            {proposals.length > 0 && (
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  backgroundColor: '#1e293b',
                  color: '#93c5fd',
                  padding: '2px 8px',
                  borderRadius: '10px',
                }}
              >
                {proposals.length}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: '4px',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Content Body */}
        <div style={{ padding: '16px', overflowY: 'auto', flex: 1 }}>
          {isLoading && (
            <div style={{ padding: '40px 20px', textAlign: 'center', color: '#64748b' }}>
              Loading repair history...
            </div>
          )}

          {error && (
            <div style={{ padding: '16px', backgroundColor: '#fef2f2', color: '#b91c1c', borderRadius: '8px', fontSize: '13px' }}>
              {error}
            </div>
          )}

          {!isLoading && !error && proposals.length === 0 && (
            <div style={{ padding: '40px 20px', textAlign: 'center', color: '#64748b' }}>
              No previous repair proposals found for this finding.
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {proposals.map((item) => (
              <div
                key={item.id}
                onClick={() => {
                  onSelectProposal(item);
                  onClose();
                }}
                style={{
                  padding: '12px 14px',
                  borderRadius: '8px',
                  border: '1px solid #e2e8f0',
                  backgroundColor: '#ffffff',
                  cursor: 'pointer',
                  transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '12px',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#2563eb';
                  e.currentTarget.style.boxShadow = '0 2px 4px rgba(37, 99, 235, 0.08)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '#e2e8f0';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono, monospace)',
                        fontSize: '11px',
                        fontWeight: 700,
                        padding: '1px 5px',
                        borderRadius: '3px',
                        backgroundColor: '#eff6ff',
                        color: '#1d4ed8',
                        border: '1px solid #bfdbfe',
                      }}
                    >
                      {item.rule_id}
                    </span>
                    <strong style={{ fontSize: '13px', color: '#0f172a' }}>
                      {item.repair_summary}
                    </strong>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '11.5px', color: '#64748b' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                      <FileCode size={12} />
                      <span>{item.file_path}:{item.start_line}</span>
                    </span>
                    <span>•</span>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                      <Clock size={12} />
                      <span>{item.created_at ? new Date(item.created_at).toLocaleTimeString() : 'N/A'}</span>
                    </span>
                    <span>•</span>
                    <span>
                      <span style={{ color: '#16a34a', fontWeight: 600 }}>+{item.additions}</span>{' '}
                      <span style={{ color: '#dc2626', fontWeight: 600 }}>-{item.deletions}</span>
                    </span>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      fontSize: '10.5px',
                      fontWeight: 600,
                      padding: '2px 7px',
                      borderRadius: '4px',
                      backgroundColor: item.validation_status === 'passed' ? '#dcfce7' : '#fee2e2',
                      color: item.validation_status === 'passed' ? '#15803d' : '#b91c1c',
                      textTransform: 'uppercase',
                    }}
                  >
                    {item.validation_status}
                  </span>
                  <ArrowRight size={14} style={{ color: '#94a3b8' }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
