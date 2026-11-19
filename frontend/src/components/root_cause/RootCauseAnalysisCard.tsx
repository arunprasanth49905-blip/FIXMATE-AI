import React, { useState } from 'react';
import {
  Sparkles,
  AlertTriangle,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  X,
  Copy,
  Check,
  FileCode,
  ArrowRight,
  Flame,
  HelpCircle,
  Wrench,
  CheckCircle2,
  Info,
  Clock,
  Cpu,
} from 'lucide-react';
import { RootCauseAnalysis } from '../../types/api';

interface RootCauseAnalysisCardProps {
  analysis: RootCauseAnalysis;
  onClose?: () => void;
  onNavigateToFile?: (path: string, line: number) => void;
}

export const RootCauseAnalysisCard: React.FC<RootCauseAnalysisCardProps> = ({
  analysis,
  onClose,
  onNavigateToFile,
}) => {
  const [copiedOriginal, setCopiedOriginal] = useState(false);
  const [copiedCorrected, setCopiedCorrected] = useState(false);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

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

  const severity =
    analysis.severity_assessment?.detected_severity ||
    analysis.severity_assessment?.ai_assessed_severity ||
    'medium';
  const confidenceScore = analysis.confidence_assessment?.confidence_score ?? 90;
  const confidenceLevel = analysis.confidence_assessment?.confidence_level ?? 'HIGH';

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

  const getSeverityBadgeColor = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      case 'low':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  };

  const getConfidenceLevelColor = (level: string) => {
    switch (level.toUpperCase()) {
      case 'HIGH':
        return 'bg-emerald-100 text-emerald-800 border-emerald-300';
      case 'MEDIUM':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      default:
        return 'bg-rose-100 text-rose-800 border-rose-300';
    }
  };

  return (
    <div className="bg-white border border-indigo-200 rounded-xl shadow-md overflow-hidden transition-all duration-200 my-3">
      {/* 1. Header & Location Bar */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white px-5 py-3.5">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-indigo-600/50 rounded-lg">
              <Sparkles className="w-4 h-4 text-indigo-300 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-mono text-xs font-semibold px-2 py-0.5 bg-indigo-700/80 rounded text-indigo-200 uppercase">
                  {ruleId}
                </span>
                <h3 className="text-sm font-bold text-white tracking-wide">
                  {analysis.rule_name || 'AI Root Cause Analysis'}
                </h3>
              </div>
              <div className="flex items-center gap-3 text-xs text-indigo-200/80 mt-1">
                <span className="flex items-center gap-1">
                  <Cpu className="w-3.5 h-3.5 text-indigo-400" />
                  {analysis.model || 'Gemini'}
                </span>
                {analysis.duration_ms > 0 && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-indigo-400" />
                    {analysis.duration_ms}ms
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {onClose && (
              <button
                onClick={onClose}
                className="p-1.5 text-slate-300 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                title="Dismiss analysis card"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Prominent Error Location Banner */}
        <div className="mt-3 pt-3 border-t border-indigo-800/60 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-xs font-mono text-indigo-100 bg-indigo-900/60 px-3 py-1.5 rounded-lg border border-indigo-700/50">
            <FileCode className="w-4 h-4 text-indigo-300" />
            <span>
              File: <strong className="text-white">{filePath}</strong>
            </span>
            <span className="text-indigo-400">|</span>
            <span>
              Line: <strong className="text-amber-300 font-bold">{errorLine}</strong>
            </span>
            {analysis.language && (
              <>
                <span className="text-indigo-400">|</span>
                <span className="text-indigo-200 uppercase text-[11px] font-sans font-semibold">
                  {analysis.language}
                </span>
              </>
            )}
          </div>

          {onNavigateToFile && (
            <button
              onClick={() => onNavigateToFile(filePath, errorLine)}
              data-testid="view-in-editor-btn"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors shadow-sm"
              title="Jump directly to error line in Monaco Editor"
            >
              <span>View Error in Editor</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      <div className="p-5 space-y-4">
        {/* 2. Original Buggy Code (Red / Error Context) */}
        {originalCode && (
          <div className="rounded-lg border border-rose-200 bg-rose-50/50 overflow-hidden">
            <div className="flex items-center justify-between px-3.5 py-2 bg-rose-100/70 border-b border-rose-200">
              <div className="flex items-center gap-1.5 text-xs font-bold text-rose-900 uppercase tracking-wide">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                <span>Error Code (Line {errorLine})</span>
              </div>
              <button
                onClick={() => handleCopy(originalCode, true)}
                data-testid="copy-original-btn"
                className="inline-flex items-center gap-1 text-[11px] font-medium text-rose-700 hover:text-rose-900 px-2 py-0.5 rounded bg-white/70 hover:bg-white border border-rose-300 transition-colors"
                title="Copy original buggy code"
              >
                {copiedOriginal ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                <span>{copiedOriginal ? 'Copied' : 'Copy Code'}</span>
              </button>
            </div>
            <pre className="p-3 text-xs font-mono text-rose-950 bg-rose-50/60 overflow-x-auto whitespace-pre-wrap leading-relaxed">
              <code>{originalCode}</code>
            </pre>
          </div>
        )}

        {/* 3. What Went Wrong? (Simple English) */}
        <div className="p-4 rounded-lg bg-amber-50/60 border border-amber-200">
          <h4 className="text-xs font-bold text-amber-950 uppercase tracking-wide flex items-center gap-1.5 mb-1.5">
            <HelpCircle className="w-4 h-4 text-amber-600" />
            What Went Wrong?
          </h4>
          <p className="text-sm text-amber-950 leading-relaxed font-medium">
            {simpleExplanation}
          </p>
        </div>

        {/* 4. Root Cause */}
        <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
          <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide flex items-center gap-1.5 mb-1.5">
            <Wrench className="w-4 h-4 text-indigo-600" />
            Root Cause
          </h4>
          <p className="text-sm text-slate-800 leading-relaxed">
            {rootCause}
          </p>
        </div>

        {/* 5. Corrected Code (Green / Success Context) */}
        {correctedCode ? (
          <div className="rounded-lg border border-emerald-300 bg-emerald-50/40 overflow-hidden shadow-sm">
            <div className="flex items-center justify-between px-3.5 py-2 bg-emerald-100/70 border-b border-emerald-300">
              <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-950 uppercase tracking-wide">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span>Corrected Code</span>
                <span className="text-[10px] font-normal text-emerald-700 font-sans normal-case ml-2 bg-emerald-200/60 px-2 py-0.5 rounded">
                  Suggested Fix (Not Applied)
                </span>
              </div>
              <button
                onClick={() => handleCopy(correctedCode, false)}
                data-testid="copy-corrected-btn"
                className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-800 hover:text-emerald-950 px-2 py-0.5 rounded bg-white hover:bg-emerald-50 border border-emerald-300 transition-colors"
                title="Copy corrected code suggestion"
              >
                {copiedCorrected ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                <span>{copiedCorrected ? 'Copied' : 'Copy Corrected Code'}</span>
              </button>
            </div>
            <pre className="p-3 text-xs font-mono text-emerald-950 bg-emerald-50/70 overflow-x-auto whitespace-pre-wrap leading-relaxed font-semibold">
              <code>{correctedCode}</code>
            </pre>
          </div>
        ) : fixStatus === 'needs_clarification' ? (
          <div className="p-4 rounded-lg bg-amber-50 border border-amber-300 text-amber-900 text-xs flex items-center gap-2">
            <Info className="w-4 h-4 text-amber-600 shrink-0" />
            <span>
              <strong>Clarification Needed:</strong> The AI could not safely generate an automated fix without additional business logic context.
            </span>
          </div>
        ) : null}

        {/* 6. What Changed? */}
        {correctionExplanation && (
          <div className="p-4 rounded-lg bg-indigo-50/40 border border-indigo-100">
            <h4 className="text-xs font-bold text-indigo-950 uppercase tracking-wide flex items-center gap-1.5 mb-1.5">
              <Info className="w-4 h-4 text-indigo-600" />
              What Changed?
            </h4>
            <p className="text-sm text-indigo-950 leading-relaxed">
              {correctionExplanation}
            </p>
          </div>
        )}

        {/* 7. AI Assumptions (Shown only if present) */}
        {assumptions && assumptions.length > 0 && (
          <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200">
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wide mb-1.5 flex items-center gap-1.5">
              <Info className="w-3.5 h-3.5 text-amber-500" />
              AI Assumptions & Inferences
            </h4>
            <ul className="space-y-1 list-disc list-inside text-xs text-slate-600">
              {assumptions.map((item, idx) => (
                <li key={idx} className="leading-relaxed">{item}</li>
              ))}
            </ul>
          </div>
        )}

        {/* 8. Concise Summary Footer Bar (Severity & Confidence) */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-200 text-xs">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-slate-600">
              <Flame className="w-4 h-4 text-slate-400" />
              <span>Severity:</span>
              <span
                className={`font-semibold uppercase px-2 py-0.5 rounded text-xs border ${getSeverityBadgeColor(
                  severity
                )}`}
              >
                {severity}
              </span>
            </div>

            <span className="text-slate-300">•</span>

            <div className="flex items-center gap-1.5 text-slate-600">
              <ShieldCheck className="w-4 h-4 text-slate-400" />
              <span>AI Confidence:</span>
              <span
                className={`font-bold px-2 py-0.5 rounded border text-[11px] ${getConfidenceLevelColor(
                  confidenceLevel
                )}`}
              >
                {confidenceScore}% ({confidenceLevel})
              </span>
            </div>
          </div>

          {/* Toggle for Optional Technical Diagnostics */}
          <button
            onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
            className="text-xs text-slate-500 hover:text-indigo-600 flex items-center gap-1 font-medium transition-colors"
          >
            <span>{showTechnicalDetails ? 'Hide Diagnostics' : 'Detailed Diagnostics'}</span>
            {showTechnicalDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Expandable Technical Diagnostics Details */}
        {showTechnicalDetails && (
          <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-3 text-xs text-slate-700 animate-in fade-in duration-150">
            {analysis.technical_reasoning && (
              <div>
                <strong className="text-slate-800 uppercase text-[10px] tracking-wider block mb-1">
                  Language Semantics
                </strong>
                <p className="leading-relaxed">{analysis.technical_reasoning}</p>
              </div>
            )}
            {analysis.confidence_assessment?.confidence_reason && (
              <div>
                <strong className="text-slate-800 uppercase text-[10px] tracking-wider block mb-1">
                  Confidence Justification
                </strong>
                <p className="leading-relaxed">{analysis.confidence_assessment.confidence_reason}</p>
              </div>
            )}
            {analysis.prevention && (
              <div>
                <strong className="text-slate-800 uppercase text-[10px] tracking-wider block mb-1">
                  Prevention Practice
                </strong>
                <p className="leading-relaxed">{analysis.prevention}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
