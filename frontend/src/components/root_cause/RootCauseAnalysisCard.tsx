import React, { useState } from 'react';
import {
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  X,
  Copy,
  Check,
  FileCode,
  ArrowRight,
  CheckCircle2,
  Info,
  Clock,
  Cpu,
  Terminal,
  ShieldCheck,
  FileDiff,
  RotateCw,
} from 'lucide-react';
import { RootCauseAnalysis } from '../../types/api';

interface RootCauseAnalysisCardProps {
  analysis: RootCauseAnalysis;
  onClose?: () => void;
  onNavigateToFile?: (path: string, line: number) => void;
  onGenerateRepair?: () => void;
  isGeneratingRepair?: boolean;
  hasRepairProposal?: boolean;
}

export const RootCauseAnalysisCard: React.FC<RootCauseAnalysisCardProps> = ({
  analysis,
  onClose,
  onNavigateToFile,
  onGenerateRepair,
  isGeneratingRepair = false,
  hasRepairProposal = false,
}) => {
  const [copiedOriginal, setCopiedOriginal] = useState(false);
  const [copiedCorrected, setCopiedCorrected] = useState(false);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const [showAssumptions, setShowAssumptions] = useState(true);

  // Resolve fields with clean fallbacks
  const filePath = analysis.bug_location?.file || analysis.file_path || 'Unknown file';
  const errorLine = analysis.bug_location?.line ?? analysis.start_line ?? 1;
  const ruleId = analysis.bug_location?.rule_id || analysis.rule_id;
  const originalCode = analysis.original_code || analysis.evidence || '';
  const simpleExplanation =
    analysis.simple_explanation || analysis.bug_explanation || analysis.summary || 'No explanation provided.';
  const rootCause = analysis.root_cause || 'Root cause undetermined.';
  const correctedCode = analysis.corrected_code || '';
  const correctionExplanation =
    analysis.correction_explanation || analysis.recommended_approach || 'No correction details provided.';
  const assumptions = analysis.assumptions || [];
  const fixStatus = analysis.fix_status || 'suggested_not_applied';

  const severity = (
    analysis.severity_assessment?.detected_severity ||
    analysis.severity_assessment?.ai_assessed_severity ||
    'medium'
  ).toLowerCase();

  const confidenceScore = analysis.confidence_assessment?.confidence_score ?? 90;
  const confidenceLevel = analysis.confidence_assessment?.confidence_level ?? 'HIGH';
  const category = (analysis as unknown as { category?: string }).category;

  const handleCopy = (text: string, isOriginal: boolean) => {
    navigator.clipboard.writeText(text);
    if (isOriginal) {
      setCopiedOriginal(true);
      setTimeout(() => setCopiedOriginal(false), 2000);
    } else {
      setCopiedCorrected(true);
      setTimeout(() => setCopiedCorrected(false), 2000);
    }
  };

  const getSeverityStyle = (sev: string) => {
    switch (sev) {
      case 'critical':
        return { bg: '#fef2f2', border: '#fecaca', text: '#dc2626' };
      case 'high':
        return { bg: '#fff7ed', border: '#ffedd5', text: '#c2410c' };
      case 'medium':
        return { bg: '#fffbeb', border: '#fde68a', text: '#b45309' };
      case 'low':
        return { bg: '#eff6ff', border: '#bfdbfe', text: '#1d4ed8' };
      default:
        return { bg: '#f1f5f9', border: '#e2e8f0', text: '#475569' };
    }
  };

  const sevStyle = getSeverityStyle(severity);

  return (
    <div
      style={{
        backgroundColor: 'var(--color-surface, #ffffff)',
        border: '1px solid var(--color-border, #e2e8f0)',
        borderRadius: 'var(--radius-lg, 10px)',
        boxShadow: 'var(--shadow-sm, 0 1px 3px rgba(0,0,0,0.05))',
        overflow: 'hidden',
        margin: '12px 0',
        fontFamily: 'var(--font-sans, sans-serif)',
      }}
    >
      {/* =========================================================================
          1. RCA HEADER (Compact Metadata Layout, Professional Developer Theme)
         ========================================================================= */}
      <div
        style={{
          backgroundColor: '#0f172a',
          color: '#ffffff',
          padding: '12px 16px',
          borderBottom: '1px solid #1e293b',
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
                backgroundColor: '#1e293b',
                color: '#38bdf8',
                border: '1px solid #334155',
              }}
            >
              Root Cause Analysis
            </span>
            <span
              style={{
                fontFamily: 'var(--font-mono, monospace)',
                fontSize: '11px',
                fontWeight: 700,
                padding: '2px 7px',
                borderRadius: '4px',
                backgroundColor: '#1d4ed8',
                color: '#eff6ff',
              }}
            >
              {ruleId}
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
              {analysis.rule_name || 'AI Root Cause Analysis'}
            </h3>
          </div>

          {/* Right: View in Editor Action & Dismiss */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {onNavigateToFile && (
              <button
                onClick={() => onNavigateToFile(filePath, errorLine)}
                data-testid="view-in-editor-btn"
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
                  transition: 'background-color 0.15s ease',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#1d4ed8')}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#2563eb')}
                title="Jump directly to error line in Monaco Editor"
              >
                <span>View Error in Editor</span>
                <ArrowRight size={13} />
              </button>
            )}

            {onClose && (
              <button
                onClick={onClose}
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
                onMouseEnter={(e) => (e.currentTarget.style.color = '#ffffff')}
                onMouseLeave={(e) => (e.currentTarget.style.color = '#94a3b8')}
                title="Dismiss analysis card"
              >
                <X size={15} />
              </button>
            )}
          </div>
        </div>

        {/* Compact File & Coordinate Bar */}
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
            <strong style={{ color: '#ffffff', fontWeight: 600 }}>{filePath}</strong>
          </span>

          <span style={{ color: '#475569' }}>•</span>

          <span style={{ color: '#cbd5e1' }}>
            <span>Line:</span>{' '}
            <strong style={{ color: '#fde047', fontWeight: 700 }}>{errorLine}</strong>
          </span>

          {analysis.language && (
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
                {analysis.language}
              </span>
            </>
          )}
        </div>
      </div>

      <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        {/* =========================================================================
            2. BUG SUMMARY / METADATA ROW
           ========================================================================= */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
            gap: '10px',
          }}
        >
          {/* Metric 1: Severity */}
          <div
            style={{
              padding: '8px 12px',
              backgroundColor: sevStyle.bg,
              border: `1px solid ${sevStyle.border}`,
              borderRadius: 'var(--radius-sm, 6px)',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px',
            }}
          >
            <span
              style={{
                fontSize: '10px',
                fontWeight: 700,
                color: 'var(--color-navy-500, #64748b)',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}
            >
              Severity
            </span>
            <span
              style={{
                fontSize: '12px',
                fontWeight: 700,
                color: sevStyle.text,
                textTransform: 'uppercase',
              }}
            >
              {severity}
            </span>
          </div>

          {/* Metric 2: Confidence */}
          <div
            style={{
              padding: '8px 12px',
              backgroundColor: '#f0fdf4',
              border: '1px solid #bbf7d0',
              borderRadius: 'var(--radius-sm, 6px)',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px',
            }}
          >
            <span
              style={{
                fontSize: '10px',
                fontWeight: 700,
                color: 'var(--color-navy-500, #64748b)',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}
            >
              AI Confidence
            </span>
            <span
              style={{
                fontSize: '12px',
                fontWeight: 700,
                color: '#15803d',
              }}
            >
              {confidenceScore}% ({confidenceLevel})
            </span>
          </div>

          {/* Metric 3: Category (only rendered if actually present in response) */}
          {category && (
            <div
              style={{
                padding: '8px 12px',
                backgroundColor: 'var(--color-surface-subtle, #f1f5f9)',
                border: '1px solid var(--color-border, #e2e8f0)',
                borderRadius: 'var(--radius-sm, 6px)',
                display: 'flex',
                flexDirection: 'column',
                gap: '2px',
              }}
            >
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  color: 'var(--color-navy-500, #64748b)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                }}
              >
                Category
              </span>
              <span
                style={{
                  fontSize: '12px',
                  fontWeight: 600,
                  color: 'var(--color-navy-800, #1e293b)',
                  textTransform: 'capitalize',
                }}
              >
                {category}
              </span>
            </div>
          )}

          {/* Metric 4: Status */}
          <div
            style={{
              padding: '8px 12px',
              backgroundColor: '#eff6ff',
              border: '1px solid #bfdbfe',
              borderRadius: 'var(--radius-sm, 6px)',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px',
            }}
          >
            <span
              style={{
                fontSize: '10px',
                fontWeight: 700,
                color: 'var(--color-navy-500, #64748b)',
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
              }}
            >
              Status
            </span>
            <span
              style={{
                fontSize: '11.5px',
                fontWeight: 600,
                color: '#1d4ed8',
              }}
            >
              {fixStatus === 'needs_clarification' ? 'Needs Clarification' : 'Suggested Fix — Not Applied'}
            </span>
          </div>
        </div>

        {/* =========================================================================
            3. ORIGINAL CODE SECTION (Error line indicated, copy button, developer code block)
           ========================================================================= */}
        {originalCode && (
          <div
            style={{
              border: '1px solid #fecaca',
              borderRadius: 'var(--radius-md, 8px)',
              backgroundColor: '#fff5f5',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 12px',
                backgroundColor: '#fee2e2',
                borderBottom: '1px solid #fecaca',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '12px', fontWeight: 700, color: '#991b1b' }}>
                  Original Code
                </span>
                <span
                  style={{
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono, monospace)',
                    fontWeight: 600,
                    padding: '2px 6px',
                    borderRadius: '4px',
                    backgroundColor: '#ffffff',
                    color: '#b91c1c',
                    border: '1px solid #fca5a5',
                  }}
                >
                  Error Code (Line {errorLine})
                </span>
              </div>
              <button
                onClick={() => handleCopy(originalCode, true)}
                data-testid="copy-original-btn"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  fontSize: '11px',
                  fontWeight: 600,
                  color: '#991b1b',
                  backgroundColor: '#ffffff',
                  border: '1px solid #fca5a5',
                  borderRadius: '4px',
                  padding: '3px 8px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#fff1f2')}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#ffffff')}
                title="Copy original code"
              >
                {copiedOriginal ? <Check size={12} color="#16a34a" /> : <Copy size={12} />}
                <span>{copiedOriginal ? 'Copied' : 'Copy Code'}</span>
              </button>
            </div>
            <pre
              style={{
                margin: 0,
                padding: '12px 14px',
                fontSize: '12px',
                fontFamily: 'var(--font-mono, monospace)',
                color: '#f8fafc',
                backgroundColor: '#0f172a',
                borderLeft: '3px solid #ef4444',
                overflowX: 'auto',
                lineHeight: 1.5,
              }}
            >
              <code>{originalCode}</code>
            </pre>
          </div>
        )}

        {/* =========================================================================
            4. WHAT WENT WRONG (Observable Behavior in Simple English)
           ========================================================================= */}
        <div
          style={{
            padding: '12px 14px',
            backgroundColor: '#fffbeb',
            border: '1px solid #fde68a',
            borderRadius: 'var(--radius-md, 8px)',
          }}
        >
          <h4
            style={{
              margin: '0 0 6px 0',
              fontSize: '12px',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              color: '#92400e',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <AlertTriangle size={14} style={{ color: '#d97706' }} />
            <span>What Went Wrong?</span>
          </h4>
          <p
            style={{
              margin: 0,
              fontSize: '13px',
              color: '#78350f',
              lineHeight: 1.5,
              fontWeight: 500,
            }}
          >
            {simpleExplanation}
          </p>
        </div>

        {/* =========================================================================
            5. ROOT CAUSE (Specific Underlying Programming Mistake)
           ========================================================================= */}
        <div
          style={{
            padding: '12px 14px',
            backgroundColor: 'var(--color-surface, #ffffff)',
            border: '1px solid var(--color-border, #e2e8f0)',
            borderRadius: 'var(--radius-md, 8px)',
          }}
        >
          <h4
            style={{
              margin: '0 0 6px 0',
              fontSize: '12px',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.04em',
              color: 'var(--color-navy-800, #1e293b)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <Terminal size={14} style={{ color: '#2563eb' }} />
            <span>Root Cause</span>
          </h4>
          <p
            style={{
              margin: 0,
              fontSize: '13px',
              color: 'var(--color-navy-700, #334155)',
              lineHeight: 1.5,
            }}
          >
            {rootCause}
          </p>
        </div>

        {/* =========================================================================
            6. AI SUGGESTED FIX (Suggested Fix — Not Applied, Never Automatically Applied)
           ========================================================================= */}
        {correctedCode ? (
          <div
            style={{
              border: '1px solid #bbf7d0',
              borderRadius: 'var(--radius-md, 8px)',
              backgroundColor: '#f0fdf4',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 12px',
                backgroundColor: '#dcfce7',
                borderBottom: '1px solid #bbf7d0',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '12px', fontWeight: 700, color: '#166534' }}>
                  AI Suggested Fix
                </span>
                <span
                  style={{
                    fontSize: '11px',
                    fontFamily: 'var(--font-mono, monospace)',
                    fontWeight: 600,
                    padding: '2px 6px',
                    borderRadius: '4px',
                    backgroundColor: '#ffffff',
                    color: '#15803d',
                    border: '1px solid #86efac',
                  }}
                >
                  Corrected Code
                </span>
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 500,
                    padding: '2px 6px',
                    borderRadius: '4px',
                    backgroundColor: 'rgba(22, 101, 52, 0.1)',
                    color: '#166534',
                  }}
                >
                  Suggested Fix (Not Applied)
                </span>
              </div>
              <button
                onClick={() => handleCopy(correctedCode, false)}
                data-testid="copy-corrected-btn"
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
                  transition: 'all 0.15s ease',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f0fdf4')}
                onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#ffffff')}
                title="Copy suggested fix"
              >
                {copiedCorrected ? <Check size={12} color="#16a34a" /> : <Copy size={12} />}
                <span>{copiedCorrected ? 'Copied' : 'Copy Corrected Code'}</span>
              </button>
            </div>
            <pre
              style={{
                margin: 0,
                padding: '12px 14px',
                fontSize: '12px',
                fontFamily: 'var(--font-mono, monospace)',
                color: '#ecfdf5',
                backgroundColor: '#0f172a',
                borderLeft: '3px solid #10b981',
                overflowX: 'auto',
                lineHeight: 1.5,
                fontWeight: 500,
              }}
            >
              <code>{correctedCode}</code>
            </pre>
          </div>
        ) : fixStatus === 'needs_clarification' ? (
          <div
            style={{
              padding: '12px 14px',
              backgroundColor: '#fffbeb',
              border: '1px solid #fde68a',
              borderRadius: 'var(--radius-md, 8px)',
              fontSize: '12px',
              color: '#92400e',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <Info size={16} style={{ color: '#d97706', flexShrink: 0 }} />
            <span>
              <strong>Clarification Needed:</strong> The AI could not safely determine an automated fix without additional business logic context.
            </span>
          </div>
        ) : null}

        {/* =========================================================================
            7. WHY THE FIX WORKS (Explanation of Why the Correction Resolves the Bug)
           ========================================================================= */}
        {correctionExplanation && (
          <div
            style={{
              padding: '12px 14px',
              backgroundColor: 'var(--color-surface, #ffffff)',
              border: '1px solid var(--color-border, #e2e8f0)',
              borderRadius: 'var(--radius-md, 8px)',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '6px',
              }}
            >
              <h4
                style={{
                  margin: 0,
                  fontSize: '12px',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                  color: 'var(--color-navy-800, #1e293b)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <CheckCircle2 size={14} style={{ color: '#16a34a' }} />
                <span>Why the Fix Works</span>
              </h4>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  color: 'var(--color-blue-primary, #2563eb)',
                }}
              >
                What Changed?
              </span>
            </div>
            <p
              style={{
                margin: 0,
                fontSize: '13px',
                color: 'var(--color-navy-700, #334155)',
                lineHeight: 1.5,
              }}
            >
              {correctionExplanation}
            </p>
          </div>
        )}

        {/* Phase 6 Safe Patch Generation CTA */}
        {onGenerateRepair && (
          <div
            style={{
              padding: '12px 14px',
              backgroundColor: '#f0fdf4',
              border: '1px solid #bbf7d0',
              borderRadius: 'var(--radius-md, 8px)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px',
              flexWrap: 'wrap',
            }}
          >
            <div>
              <div
                style={{
                  fontSize: '12px',
                  fontWeight: 700,
                  color: '#166534',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <ShieldCheck size={15} />
                <span>Phase 6: Safe Patch & Diff Engine</span>
              </div>
              <div style={{ fontSize: '11px', color: '#15803d', marginTop: '2px' }}>
                Generate an in-memory unified diff and syntax-validated patch without modifying disk files.
              </div>
            </div>
            <button
              onClick={onGenerateRepair}
              disabled={isGeneratingRepair}
              data-testid="generate-patch-btn"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '7px 14px',
                backgroundColor: hasRepairProposal ? '#15803d' : '#16a34a',
                color: '#ffffff',
                border: 'none',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: isGeneratingRepair ? 'not-allowed' : 'pointer',
                opacity: isGeneratingRepair ? 0.7 : 1,
                boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                whiteSpace: 'nowrap',
              }}
            >
              {isGeneratingRepair ? (
                <>
                  <RotateCw size={13} className="animate-spin" />
                  <span>Generating Patch...</span>
                </>
              ) : (
                <>
                  <FileDiff size={13} />
                  <span>{hasRepairProposal ? 'Regenerate Patch' : 'Generate Safe Patch'}</span>
                </>
              )}
            </button>
          </div>
        )}

        {/* =========================================================================
            8. ASSUMPTIONS & ADDITIONAL DETAILS (Collapsible, Only if Available)
           ========================================================================= */}
        {assumptions && assumptions.length > 0 && (
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
                <span>AI Assumptions & Inferences</span>
                <span
                  style={{
                    fontSize: '10.5px',
                    fontWeight: 600,
                    color: 'var(--color-navy-500, #64748b)',
                    backgroundColor: '#e2e8f0',
                    padding: '1px 5px',
                    borderRadius: '10px',
                  }}
                >
                  {assumptions.length}
                </span>
              </span>
              {showAssumptions ? (
                <ChevronUp size={14} style={{ color: '#64748b' }} />
              ) : (
                <ChevronDown size={14} style={{ color: '#64748b' }} />
              )}
            </button>

            {showAssumptions && (
              <div
                style={{
                  padding: '0 14px 12px 14px',
                  borderTop: '1px solid var(--color-border, #e2e8f0)',
                  paddingTop: '8px',
                }}
              >
                <ul
                  style={{
                    margin: 0,
                    paddingLeft: '18px',
                    fontSize: '12px',
                    color: 'var(--color-navy-600, #475569)',
                    lineHeight: 1.5,
                  }}
                >
                  {assumptions.map((item, idx) => (
                    <li key={idx} style={{ marginBottom: '4px' }}>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Optional Technical Diagnostics Toggle */}
        {(analysis.technical_reasoning ||
          analysis.confidence_assessment?.confidence_reason ||
          analysis.prevention) && (
          <div>
            <button
              onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
              style={{
                background: 'none',
                border: 'none',
                padding: '4px 0',
                cursor: 'pointer',
                fontSize: '11.5px',
                color: 'var(--color-navy-500, #64748b)',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontWeight: 600,
                transition: 'color 0.15s ease',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--color-blue-primary, #2563eb)')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--color-navy-500, #64748b)')}
            >
              <span>{showTechnicalDetails ? 'Hide Diagnostics' : 'Detailed Diagnostics'}</span>
              {showTechnicalDetails ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>

            {showTechnicalDetails && (
              <div
                style={{
                  marginTop: '8px',
                  padding: '12px 14px',
                  backgroundColor: 'var(--color-surface-subtle, #f8fafc)',
                  border: '1px solid var(--color-border, #e2e8f0)',
                  borderRadius: 'var(--radius-md, 8px)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                  fontSize: '12px',
                  color: 'var(--color-navy-700, #334155)',
                }}
              >
                {analysis.technical_reasoning && (
                  <div>
                    <strong
                      style={{
                        fontSize: '10.5px',
                        color: 'var(--color-navy-800, #1e293b)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                        display: 'block',
                        marginBottom: '2px',
                      }}
                    >
                      Language Semantics
                    </strong>
                    <p style={{ margin: 0, lineHeight: 1.5 }}>{analysis.technical_reasoning}</p>
                  </div>
                )}
                {analysis.confidence_assessment?.confidence_reason && (
                  <div>
                    <strong
                      style={{
                        fontSize: '10.5px',
                        color: 'var(--color-navy-800, #1e293b)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                        display: 'block',
                        marginBottom: '2px',
                      }}
                    >
                      Confidence Rationale
                    </strong>
                    <p style={{ margin: 0, lineHeight: 1.5 }}>
                      {analysis.confidence_assessment.confidence_reason}
                    </p>
                  </div>
                )}
                {analysis.prevention && (
                  <div>
                    <strong
                      style={{
                        fontSize: '10.5px',
                        color: 'var(--color-navy-800, #1e293b)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                        display: 'block',
                        marginBottom: '2px',
                      }}
                    >
                      Prevention Recommendation
                    </strong>
                    <p style={{ margin: 0, lineHeight: 1.5 }}>{analysis.prevention}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* =========================================================================
            9. AI METADATA & FOOTER (Compact, Non-Competing with Bug Content)
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
                {analysis.model || 'gemini-3.5-flash-lite'}
              </strong>
            </span>

            {analysis.duration_ms > 0 && (
              <>
                <span>•</span>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  <Clock size={12} style={{ color: '#64748b' }} />
                  <span>Latency:</span>
                  <strong style={{ color: 'var(--color-navy-700, #334155)', fontWeight: 600 }}>
                    {analysis.duration_ms}ms
                  </strong>
                </span>
              </>
            )}
          </div>

          <span style={{ fontSize: '10.5px', color: 'var(--color-navy-400, #94a3b8)' }}>
            Suggestion Only • No automated file changes
          </span>
        </div>
      </div>
    </div>
  );
};
