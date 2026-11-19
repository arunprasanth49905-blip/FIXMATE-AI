import React, { useState, useMemo } from 'react';
import {
  X,
  Play,
  RotateCw,
  Bug,
  Search,
  ArrowRight,
  FileCode,
  CheckCircle2,
  Clock,
  Sparkles,
  ChevronDown,
  ChevronRight,
  History,
  Loader2,
  MessageSquare,
  AlertCircle,
  ShieldCheck,
} from 'lucide-react';
import { DetectionRunResponse, FindingSeverity, RootCauseAnalysis, RepairProposal } from '../../types/api';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';
import { apiClient } from '../../services/apiClient';
import { RootCauseAnalysisCard } from '../root_cause/RootCauseAnalysisCard';
import { RootCauseHistoryModal } from '../root_cause/RootCauseHistoryModal';
import { RepairProposalCard } from '../repair/RepairProposalCard';
import { RepairHistoryModal } from '../repair/RepairHistoryModal';

interface DetectionPanelProps {
  projectId: string;
  detection: DetectionRunResponse | null;
  isDetecting: boolean;
  onRunDetection: () => void;
  onClose: () => void;
  onNavigateToSource: (filePath: string, line: number, column: number) => void;
}

export const DetectionPanel: React.FC<DetectionPanelProps> = ({
  projectId,
  detection,
  isDetecting,
  onRunDetection,
  onClose,
  onNavigateToSource,
}) => {
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [selectedLanguage, setSelectedLanguage] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [expandedFindingId, setExpandedFindingId] = useState<string | null>(null);

  // Root Cause State
  const [analyzingFindingId, setAnalyzingFindingId] = useState<string | null>(null);
  const [analysesMap, setAnalysesMap] = useState<Record<string, RootCauseAnalysis>>({});
  const [showNotesFindingId, setShowNotesFindingId] = useState<string | null>(null);
  const [userNotes, setUserNotes] = useState<Record<string, string>>({});
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);

  // Phase 6 Safe Repair State
  const [repairsMap, setRepairsMap] = useState<Record<string, RepairProposal>>({});
  const [generatingRepairId, setGeneratingRepairId] = useState<string | null>(null);
  const [repairError, setRepairError] = useState<string | null>(null);
  const [isRepairHistoryModalOpen, setIsRepairHistoryModalOpen] = useState(false);

  const findings = detection?.findings || [];
  const severityCounts = detection?.severity_counts || { critical: 0, high: 0, medium: 0, low: 0, info: 0 };

  const filteredFindings = useMemo(() => {
    return findings.filter((f) => {
      if (selectedSeverity !== 'all' && f.severity !== selectedSeverity) {
        return false;
      }
      if (selectedLanguage !== 'all' && f.language !== selectedLanguage) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matches =
          f.message.toLowerCase().includes(q) ||
          f.rule_id.toLowerCase().includes(q) ||
          f.rule_name.toLowerCase().includes(q) ||
          f.file_path.toLowerCase().includes(q) ||
          f.explanation.toLowerCase().includes(q);
        if (!matches) return false;
      }
      return true;
    });
  }, [findings, selectedSeverity, selectedLanguage, searchQuery]);

  const getSeverityBadgeVariant = (severity: FindingSeverity): 'danger' | 'warning' | 'blue' | 'neutral' => {
    switch (severity) {
      case 'critical':
      case 'high':
        return 'danger';
      case 'medium':
        return 'warning';
      case 'low':
        return 'blue';
      case 'info':
      default:
        return 'neutral';
    }
  };

  const handleAnalyzeFinding = async (findingId: string) => {
    // If already analyzed, toggle expand to view
    if (analysesMap[findingId]) {
      setExpandedFindingId(findingId);
      return;
    }

    try {
      setAnalyzingFindingId(findingId);
      setAnalysisError(null);
      setExpandedFindingId(findingId);

      const notes = userNotes[findingId] || undefined;
      const res = await apiClient.analyzeFinding(projectId, {
        finding_id: findingId,
        include_surrounding_context: true,
        custom_user_notes: notes,
      });

      setAnalysesMap((prev) => ({
        ...prev,
        [findingId]: res,
      }));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Root cause analysis failed';
      setAnalysisError(msg);
    } finally {
      setAnalyzingFindingId(null);
    }
  };

  const handleSelectFromHistory = (analysis: RootCauseAnalysis) => {
    setAnalysesMap((prev) => ({
      ...prev,
      [analysis.finding_id]: analysis,
    }));
    setExpandedFindingId(analysis.finding_id);
  };

  const handleGenerateRepair = async (findingId: string) => {
    try {
      setGeneratingRepairId(findingId);
      setRepairError(null);
      setExpandedFindingId(findingId);

      const res = await apiClient.generateRepair(projectId, {
        finding_id: findingId,
      });

      setRepairsMap((prev) => ({
        ...prev,
        [findingId]: res,
      }));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Safe patch generation failed';
      setRepairError(msg);
    } finally {
      setGeneratingRepairId(null);
    }
  };

  const handleSelectRepairFromHistory = (proposal: RepairProposal) => {
    setRepairsMap((prev) => ({
      ...prev,
      [proposal.finding_id]: proposal,
    }));
    setExpandedFindingId(proposal.finding_id);
    setIsRepairHistoryModalOpen(false);
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: 'var(--color-surface)',
        borderLeft: '1px solid var(--color-border)',
      }}
    >
      {/* Top Header */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Bug size={18} style={{ color: 'var(--color-red-danger)' }} />
          <div>
            <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--color-navy-900)' }}>
              Deterministic Bug Detection
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
              <Badge variant="blue">STATIC ENGINE</Badge>
              {detection && (
                <span style={{ fontSize: '11px', color: 'var(--color-navy-500)', display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                  <Clock size={10} /> {detection.duration_ms} ms
                </span>
              )}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Button
            variant="secondary"
            onClick={() => setIsRepairHistoryModalOpen(true)}
            title="Browse Generated Repair Patches & Diffs"
            style={{ padding: '4px 8px', fontSize: '12px' }}
          >
            <ShieldCheck size={12} style={{ color: '#16a34a' }} />
            <span>Patches</span>
          </Button>

          <Button
            variant="secondary"
            onClick={() => setIsHistoryModalOpen(true)}
            title="Browse Root Cause Analysis History"
            style={{ padding: '4px 8px', fontSize: '12px' }}
          >
            <History size={12} />
            <span>RCA History</span>
          </Button>

          <Button
            variant="primary"
            onClick={onRunDetection}
            disabled={isDetecting}
            isLoading={isDetecting}
            title="Scan Workspace for Static Bugs"
            style={{ padding: '4px 10px', fontSize: '12px' }}
          >
            <RotateCw size={12} />
            <span>{isDetecting ? 'Scanning...' : 'Run Detection'}</span>
          </Button>

          <button
            onClick={onClose}
            className="btn btn-secondary btn-sm"
            style={{ padding: '6px', borderRadius: '4px' }}
            title="Close Panel"
          >
            <X size={15} />
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {analysisError && (
          <div
            style={{
              padding: '10px 12px',
              backgroundColor: 'var(--color-red-subtle)',
              border: '1px solid var(--color-red-danger)',
              borderRadius: '6px',
              fontSize: '12px',
              color: 'var(--color-red-danger)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <AlertCircle size={14} style={{ flexShrink: 0 }} />
            <span style={{ flex: 1 }}>{analysisError}</span>
            <button
              onClick={() => setAnalysisError(null)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}
            >
              <X size={12} />
            </button>
          </div>
        )}

        {repairError && (
          <div
            style={{
              padding: '10px 12px',
              backgroundColor: '#fef2f2',
              border: '1px solid #f87171',
              borderRadius: '6px',
              fontSize: '12px',
              color: '#991b1b',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <AlertCircle size={14} style={{ flexShrink: 0 }} />
            <span style={{ flex: 1 }}>{repairError}</span>
            <button
              onClick={() => setRepairError(null)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}
            >
              <X size={12} />
            </button>
          </div>
        )}

        {/* Empty State if No Detection Ran Yet */}
        {!detection && !isDetecting && (
          <div
            style={{
              padding: '40px 16px',
              textAlign: 'center',
              backgroundColor: 'var(--color-surface-subtle)',
              borderRadius: '8px',
              border: '1px dashed var(--color-border)',
            }}
          >
            <Bug size={32} style={{ color: 'var(--color-navy-400)', margin: '0 auto 10px' }} />
            <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--color-navy-800)', marginBottom: '4px' }}>
              No Bug Detection Runs Yet
            </div>
            <div style={{ fontSize: '12px', color: 'var(--color-navy-500)', maxWidth: '280px', margin: '0 auto 14px' }}>
              Execute deterministic AST rules to detect dangerous patterns, undefined symbols, unreachable code, and security risks.
            </div>
            <Button variant="primary" onClick={onRunDetection} style={{ margin: '0 auto', fontSize: '12px' }}>
              <Play size={12} />
              <span>Run Detection Now</span>
            </Button>
          </div>
        )}

        {/* Severity Metrics Cards */}
        {detection && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '6px' }}>
            {[
              { id: 'all', label: 'ALL', count: detection.total_findings, color: 'var(--color-navy-700)', bg: 'var(--color-surface-subtle)' },
              { id: 'critical', label: 'CRIT', count: severityCounts.critical, color: 'var(--color-red-danger)', bg: 'var(--color-red-subtle)' },
              { id: 'high', label: 'HIGH', count: severityCounts.high, color: 'var(--color-red-danger)', bg: 'var(--color-red-subtle)' },
              { id: 'medium', label: 'MED', count: severityCounts.medium, color: 'var(--color-amber-warning)', bg: 'var(--color-amber-subtle)' },
              { id: 'low', label: 'LOW', count: severityCounts.low, color: 'var(--color-blue-primary)', bg: 'var(--color-blue-subtle)' },
            ].map((chip) => {
              const isSelected = selectedSeverity === chip.id;
              return (
                <div
                  key={chip.id}
                  data-testid={`sev-chip-${chip.id}`}
                  onClick={() => setSelectedSeverity(chip.id)}
                  style={{
                    padding: '8px 4px',
                    borderRadius: '6px',
                    textAlign: 'center',
                    cursor: 'pointer',
                    backgroundColor: chip.bg,
                    border: isSelected ? `2px solid ${chip.color}` : '1px solid var(--color-border)',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ fontSize: '10px', fontWeight: 700, color: chip.color }}>{chip.label}</div>
                  <div style={{ fontSize: '15px', fontWeight: 800, color: 'var(--color-navy-900)' }}>{chip.count}</div>
                </div>
              );
            })}
          </div>
        )}

        {/* Filter Controls */}
        {detection && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              <div style={{ flex: 1, position: 'relative' }}>
                <Search size={13} style={{ position: 'absolute', left: '8px', top: '9px', color: 'var(--color-navy-400)' }} />
                <input
                  type="text"
                  placeholder="Filter findings by keyword or rule..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="form-input"
                  style={{ paddingLeft: '28px', fontSize: '12px', width: '100%', height: '32px' }}
                />
              </div>

              <select
                value={selectedLanguage}
                onChange={(e) => setSelectedLanguage(e.target.value)}
                className="form-input"
                style={{ fontSize: '12px', padding: '4px 8px', width: '110px', height: '32px' }}
              >
                <option value="all">All Langs</option>
                <option value="Python">Python</option>
                <option value="JavaScript">JavaScript</option>
                <option value="TypeScript">TypeScript</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px', color: 'var(--color-navy-500)' }}>
              <span>
                Showing <strong>{filteredFindings.length}</strong> of {findings.length} finding(s)
              </span>
              {selectedSeverity !== 'all' && (
                <span
                  onClick={() => setSelectedSeverity('all')}
                  style={{ color: 'var(--color-blue-primary)', cursor: 'pointer', fontWeight: 600 }}
                >
                  Clear severity filter
                </span>
              )}
            </div>
          </div>
        )}

        {/* Findings List */}
        {detection && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {filteredFindings.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '30px 10px', color: 'var(--color-navy-500)', fontSize: '12px' }}>
                <CheckCircle2 size={24} style={{ color: 'var(--color-green-success)', margin: '0 auto 8px' }} />
                {findings.length === 0 ? 'No deterministic bugs detected!' : 'No findings match current filters.'}
              </div>
            ) : (
              filteredFindings.map((finding) => {
                const isExpanded = expandedFindingId === finding.id;
                const isAnalyzing = analyzingFindingId === finding.id;
                const analysis = analysesMap[finding.id];
                const repair = repairsMap[finding.id];
                const isGeneratingRepair = generatingRepairId === finding.id;
                const showNotes = showNotesFindingId === finding.id;

                return (
                  <div
                    key={finding.id}
                    style={{
                      border: analysis ? '1px solid #c7d2fe' : '1px solid var(--color-border)',
                      borderRadius: '8px',
                      backgroundColor: 'var(--color-surface)',
                      overflow: 'hidden',
                      transition: 'border-color 0.15s ease',
                      boxShadow: analysis ? '0 2px 8px rgba(99, 102, 241, 0.08)' : 'none',
                    }}
                  >
                    {/* Finding Summary Bar */}
                    <div
                      data-testid={`finding-row-${finding.id}`}
                      onClick={() => setExpandedFindingId(isExpanded ? null : finding.id)}
                      style={{
                        padding: '10px 12px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'flex-start',
                        justifyContent: 'space-between',
                        gap: '8px',
                        backgroundColor: isExpanded ? 'var(--color-surface-subtle)' : 'transparent',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', flex: 1 }}>
                        <div style={{ marginTop: '2px' }}>
                          {isExpanded ? <ChevronDown size={14} color="var(--color-navy-500)" /> : <ChevronRight size={14} color="var(--color-navy-500)" />}
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', marginBottom: '4px' }}>
                            <Badge variant={getSeverityBadgeVariant(finding.severity)}>
                              {finding.severity.toUpperCase()}
                            </Badge>
                            <span style={{ fontSize: '11px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-navy-700)' }}>
                              {finding.rule_id}
                            </span>
                            <span style={{ fontSize: '11px', color: 'var(--color-navy-400)' }}>
                              ({Math.round(finding.confidence * 100)}% conf)
                            </span>
                            {analysis && (
                              <span
                                style={{
                                  fontSize: '10px',
                                  fontWeight: 700,
                                  backgroundColor: '#e0e7ff',
                                  color: '#3730a3',
                                  padding: '1px 6px',
                                  borderRadius: '4px',
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '3px',
                                }}
                              >
                                <Sparkles size={10} /> AI Analyzed ({analysis.confidence_assessment.confidence_score}%)
                              </span>
                            )}
                            {repair && (
                              <span
                                style={{
                                  fontSize: '10px',
                                  fontWeight: 700,
                                  backgroundColor: '#dcfce7',
                                  color: '#166534',
                                  padding: '1px 6px',
                                  borderRadius: '4px',
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '3px',
                                }}
                              >
                                <ShieldCheck size={10} /> Patch Proposed
                              </span>
                            )}
                          </div>

                          <div style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--color-navy-900)', lineHeight: '1.4' }}>
                            {finding.message}
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '4px', fontSize: '11px', color: 'var(--color-navy-500)', fontFamily: 'var(--font-mono)' }}>
                            <FileCode size={11} />
                            <span>
                              {finding.file_path}:{finding.start_line}:{finding.start_column}
                            </span>
                          </div>
                        </div>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        {/* Phase 6 Safe Repair Button */}
                        <Button
                          variant={repair ? 'secondary' : 'secondary'}
                          data-testid={`repair-btn-${finding.id}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            if (repair) {
                              setExpandedFindingId(finding.id);
                            } else {
                              handleGenerateRepair(finding.id);
                            }
                          }}
                          disabled={isGeneratingRepair}
                          isLoading={isGeneratingRepair}
                          title={repair ? 'View Generated Patch Proposal' : 'Synthesize Safe Patch Proposal with Gemini'}
                          style={{
                            padding: '4px 8px',
                            fontSize: '11px',
                            backgroundColor: repair ? '#f0fdf4' : undefined,
                            borderColor: repair ? '#bbf7d0' : undefined,
                            color: repair ? '#166534' : undefined,
                          }}
                        >
                          <ShieldCheck size={11} />
                          <span>{isGeneratingRepair ? 'Fixing...' : repair ? 'View Patch' : 'Fix with AI'}</span>
                        </Button>

                        {/* Root Cause Action Button */}
                        <Button
                          variant={analysis ? 'secondary' : 'primary'}
                          data-testid={`analyze-btn-${finding.id}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAnalyzeFinding(finding.id);
                          }}
                          disabled={isAnalyzing}
                          isLoading={isAnalyzing}
                          title={analysis ? 'View AI Root Cause Analysis' : 'Investigate Root Cause with Google Gemini'}
                          style={{
                            padding: '4px 8px',
                            fontSize: '11px',
                            backgroundColor: analysis ? '#eef2ff' : undefined,
                            borderColor: analysis ? '#c7d2fe' : undefined,
                            color: analysis ? '#4338ca' : undefined,
                          }}
                        >
                          <Sparkles size={11} />
                          <span>{isAnalyzing ? 'Investigating...' : analysis ? 'View RCA' : 'Analyze RCA'}</span>
                        </Button>

                        <Button
                          variant="secondary"
                          data-testid={`jump-btn-${finding.id}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            onNavigateToSource(finding.file_path, finding.start_line, finding.start_column);
                          }}
                          title="Jump to code in editor"
                          style={{ padding: '4px 8px', fontSize: '11px' }}
                        >
                          <span>Jump</span>
                          <ArrowRight size={11} />
                        </Button>
                      </div>
                    </div>

                    {/* Expanded Finding Detail (Evidence, Remediation & RCA Card) */}
                    {isExpanded && (
                      <div style={{ padding: '12px 14px', borderTop: '1px solid var(--color-border)', backgroundColor: 'var(--color-surface)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {/* Explanation */}
                        <div>
                          <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-navy-600)', marginBottom: '3px' }}>
                            Explanation
                          </div>
                          <div style={{ fontSize: '12px', color: 'var(--color-navy-700)', lineHeight: '1.5' }}>
                            {finding.explanation}
                          </div>
                        </div>

                        {/* Evidence Box */}
                        {finding.evidence && (
                          <div>
                            <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', color: 'var(--color-navy-600)', marginBottom: '3px' }}>
                              Code Evidence (Line {finding.start_line})
                            </div>
                            <pre
                              style={{
                                margin: 0,
                                padding: '8px 10px',
                                backgroundColor: 'var(--color-navy-900)',
                                color: '#e2e8f0',
                                borderRadius: '4px',
                                fontSize: '11.5px',
                                fontFamily: 'var(--font-mono)',
                                overflowX: 'auto',
                                lineHeight: '1.4',
                              }}
                            >
                              {finding.evidence}
                            </pre>
                          </div>
                        )}

                        {/* Remediation Guide */}
                        <div style={{ padding: '8px 10px', borderRadius: '4px', backgroundColor: 'var(--color-blue-subtle)', border: '1px solid var(--color-blue-border)' }}>
                          <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--color-blue-primary)', marginBottom: '2px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Sparkles size={12} /> Suggested Remediation
                          </div>
                          <div style={{ fontSize: '12px', color: 'var(--color-navy-900)', lineHeight: '1.4' }}>
                            {finding.remediation}
                          </div>
                        </div>

                        {/* Optional Developer Notes Bar (before AI analysis) */}
                        {!analysis && (
                          <div style={{ borderTop: '1px dashed var(--color-border)', paddingTop: '8px' }}>
                            <button
                              onClick={() => setShowNotesFindingId(showNotes ? null : finding.id)}
                              style={{
                                background: 'none',
                                border: 'none',
                                padding: 0,
                                cursor: 'pointer',
                                fontSize: '11px',
                                color: 'var(--color-blue-primary)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px',
                                fontWeight: 500,
                              }}
                            >
                              <MessageSquare size={11} />
                              <span>{showNotes ? 'Hide developer observations' : 'Add developer observations for AI...'}</span>
                            </button>

                            {showNotes && (
                              <div style={{ marginTop: '6px' }}>
                                <textarea
                                  placeholder="e.g. Occurs when user session expires, or during high concurrency load..."
                                  value={userNotes[finding.id] || ''}
                                  onChange={(e) =>
                                    setUserNotes((prev) => ({
                                      ...prev,
                                      [finding.id]: e.target.value,
                                    }))
                                  }
                                  className="form-input"
                                  style={{ width: '100%', fontSize: '11.5px', height: '60px', padding: '6px' }}
                                />
                              </div>
                            )}
                          </div>
                        )}

                        {/* AI Loading State */}
                        {isAnalyzing && (
                          <div
                            style={{
                              padding: '24px 16px',
                              textAlign: 'center',
                              backgroundColor: '#f8fafc',
                              borderRadius: '8px',
                              border: '1px solid #e2e8f0',
                            }}
                          >
                            <Loader2 size={24} className="animate-spin" style={{ color: '#4f46e5', margin: '0 auto 8px' }} />
                            <div style={{ fontSize: '13px', fontWeight: 600, color: '#1e293b' }}>
                              Investigating Root Cause with Gemini...
                            </div>
                            <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>
                              Extracting local AST context, analyzing language semantics, and evaluating impact
                            </div>
                          </div>
                        )}

                        {/* Render AI Root Cause Analysis Card */}
                        {analysis && (
                          <div style={{ marginTop: '4px' }}>
                            <RootCauseAnalysisCard
                              analysis={analysis}
                              onClose={() =>
                                setAnalysesMap((prev) => {
                                  const copy = { ...prev };
                                  delete copy[finding.id];
                                  return copy;
                                })
                              }
                              onNavigateToFile={(path, line) => onNavigateToSource(path, line, 1)}
                              onGenerateRepair={() => handleGenerateRepair(finding.id)}
                              isGeneratingRepair={isGeneratingRepair}
                              hasRepairProposal={Boolean(repair)}
                            />
                          </div>
                        )}

                        {/* Phase 6 Safe Patch Synthesizer Loading State */}
                        {isGeneratingRepair && (
                          <div
                            style={{
                              padding: '24px 16px',
                              textAlign: 'center',
                              backgroundColor: '#f0fdf4',
                              borderRadius: '8px',
                              border: '1px solid #bbf7d0',
                              marginTop: '8px',
                            }}
                          >
                            <Loader2 size={24} className="animate-spin" style={{ color: '#16a34a', margin: '0 auto 8px' }} />
                            <div style={{ fontSize: '13px', fontWeight: 600, color: '#14532d' }}>
                              Synthesizing Safe Patch with Gemini 3.5 Flash Lite...
                            </div>
                            <div style={{ fontSize: '11px', color: '#166534', marginTop: '2px' }}>
                              Constructing targeted diff, verifying reversibility, running syntax AST validation
                            </div>
                          </div>
                        )}

                        {/* Phase 6 Render Safe Repair Proposal Card */}
                        {repair && (
                          <div style={{ marginTop: '8px' }}>
                            <RepairProposalCard
                              proposal={repair}
                              onClose={() =>
                                setRepairsMap((prev) => {
                                  const copy = { ...prev };
                                  delete copy[finding.id];
                                  return copy;
                                })
                              }
                              onNavigateToFile={(path, line) => onNavigateToSource(path, line, 1)}
                              onRegenerate={() => handleGenerateRepair(finding.id)}
                              onOpenHistory={() => setIsRepairHistoryModalOpen(true)}
                              isRegenerating={isGeneratingRepair}
                            />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>

      {/* RCA History Modal */}
      <RootCauseHistoryModal
        isOpen={isHistoryModalOpen}
        projectId={projectId}
        onClose={() => setIsHistoryModalOpen(false)}
        onSelectAnalysis={handleSelectFromHistory}
      />

      {/* Phase 6 Safe Repair History Modal */}
      <RepairHistoryModal
        isOpen={isRepairHistoryModalOpen}
        projectId={projectId}
        onClose={() => setIsRepairHistoryModalOpen(false)}
        onSelectProposal={handleSelectRepairFromHistory}
      />
    </div>
  );
};
