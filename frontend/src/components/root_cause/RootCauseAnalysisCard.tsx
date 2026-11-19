import React, { useState } from 'react';
import {
  Sparkles,
  AlertTriangle,
  ShieldCheck,
  Clock,
  Cpu,
  ChevronDown,
  ChevronUp,
  X,
  Copy,
  Check,
  Info,
  Layers,
  Activity,
  Flame,
  CheckCircle2,
  FileCode,
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
  const [copied, setCopied] = useState(false);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(true);
  const [showLimitations, setShowLimitations] = useState(false);

  const handleCopySummary = () => {
    const textToCopy = `[FIXMATE AI Root Cause Analysis]
Rule: ${analysis.rule_id} (${analysis.rule_name})
File: ${analysis.file_path}:${analysis.start_line}
Summary: ${analysis.summary}
Root Cause: ${analysis.root_cause}
Recommended Approach: ${analysis.recommended_approach}`;

    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getSeverityBadgeColor = (severity: string) => {
    switch (severity.toLowerCase()) {
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

  const getConfidenceLevelBadge = (level: string) => {
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
    <div className="bg-white border border-indigo-100 rounded-xl shadow-lg overflow-hidden transition-all duration-200 my-4">
      {/* Top Header Bar */}
      <div className="bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 text-white px-5 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-indigo-700/60 rounded-lg shadow-inner">
              <Sparkles className="w-5 h-5 text-indigo-300 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-mono text-xs font-semibold px-2 py-0.5 bg-indigo-700 rounded text-indigo-200 uppercase">
                  {analysis.rule_id}
                </span>
                <h3 className="text-base font-bold text-white tracking-wide">
                  {analysis.rule_name}
                </h3>
              </div>
              <p className="text-xs text-indigo-200/80 mt-0.5 flex items-center gap-2">
                <span
                  onClick={() => onNavigateToFile?.(analysis.file_path, analysis.start_line)}
                  className={`inline-flex items-center gap-1 font-mono text-xs ${
                    onNavigateToFile
                      ? 'cursor-pointer underline hover:text-white transition-colors'
                      : ''
                  }`}
                  title="Jump to code coordinate"
                >
                  <FileCode className="w-3.5 h-3.5" />
                  {analysis.file_path}:{analysis.start_line}
                </span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Cpu className="w-3.5 h-3.5" />
                  {analysis.model}
                </span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  {analysis.duration_ms}ms
                </span>
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleCopySummary}
              className="p-1.5 text-indigo-200 hover:text-white hover:bg-indigo-700/50 rounded-lg text-xs flex items-center gap-1.5 transition-colors border border-indigo-600/40"
              title="Copy analysis summary to clipboard"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </button>
            {onClose && (
              <button
                onClick={onClose}
                className="p-1.5 text-indigo-300 hover:text-white hover:bg-indigo-700/50 rounded-lg transition-colors"
                title="Dismiss analysis card"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="p-5 space-y-5">
        {/* Dual Severity & Confidence Metrics Bar */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-50 border border-slate-200/80 rounded-lg p-3.5">
          {/* Dual Severity Comparison */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                <Flame className="w-3.5 h-3.5 text-slate-400" />
                Severity Evaluation
              </span>
              {analysis.severity_assessment.severity_changed ? (
                <span className="text-[11px] font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                  AI Assesses Differently
                </span>
              ) : (
                <span className="text-[11px] font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" />
                  Aligned
                </span>
              )}
            </div>
            <div className="flex items-center gap-3">
              <div className="text-xs text-slate-600">
                Static Engine:{' '}
                <span
                  className={`inline-block font-semibold uppercase px-2 py-0.5 rounded text-xs border ${getSeverityBadgeColor(
                    analysis.severity_assessment.detected_severity
                  )}`}
                >
                  {analysis.severity_assessment.detected_severity}
                </span>
              </div>
              <span className="text-slate-300">→</span>
              <div className="text-xs text-slate-600">
                AI Assessment:{' '}
                <span
                  className={`inline-block font-semibold uppercase px-2 py-0.5 rounded text-xs border ${getSeverityBadgeColor(
                    analysis.severity_assessment.ai_assessed_severity
                  )}`}
                >
                  {analysis.severity_assessment.ai_assessed_severity}
                </span>
              </div>
            </div>
            <p className="text-xs text-slate-600 mt-2 italic leading-relaxed">
              "{analysis.severity_assessment.severity_reasoning}"
            </p>
          </div>

          {/* Calibrated Confidence Breakdown */}
          <div className="border-t md:border-t-0 md:border-l border-slate-200 pt-3 md:pt-0 md:pl-4">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
                Analysis Confidence
              </span>
              <span
                className={`text-[11px] font-bold px-2 py-0.5 rounded border ${getConfidenceLevelBadge(
                  analysis.confidence_assessment.confidence_level
                )}`}
              >
                {analysis.confidence_assessment.confidence_level} ({analysis.confidence_assessment.confidence_score}%)
              </span>
            </div>
            <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden mt-2">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  analysis.confidence_assessment.confidence_score >= 85
                    ? 'bg-emerald-500'
                    : analysis.confidence_assessment.confidence_score >= 60
                    ? 'bg-amber-500'
                    : 'bg-rose-500'
                }`}
                style={{ width: `${analysis.confidence_assessment.confidence_score}%` }}
              />
            </div>
            <p className="text-xs text-slate-600 mt-2 leading-relaxed">
              {analysis.confidence_assessment.confidence_reason}
            </p>
          </div>
        </div>

        {/* Executive Summary Callout */}
        <div className="bg-indigo-50/70 border-l-4 border-indigo-600 p-4 rounded-r-lg">
          <h4 className="text-xs font-bold text-indigo-950 uppercase tracking-wider mb-1 flex items-center gap-1.5">
            <Info className="w-4 h-4 text-indigo-600" />
            Executive Summary
          </h4>
          <p className="text-sm font-medium text-indigo-900 leading-snug">
            {analysis.summary}
          </p>
        </div>

        {/* Detailed Investigation Sections */}
        <div className="space-y-4">
          {/* 1. What the Bug Is */}
          <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              1. What the Bug Is
            </h4>
            <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">
              {analysis.bug_explanation}
            </p>
          </div>

          {/* 2. Underlying Root Cause */}
          <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-indigo-500" />
              2. Underlying Root Cause
            </h4>
            <p className="text-sm text-slate-800 font-medium leading-relaxed bg-slate-50/70 p-3 rounded border border-slate-100">
              {analysis.root_cause}
            </p>
          </div>

          {/* 3. Deep Technical Semantics & Architecture (Collapsible Toggle) */}
          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-sm">
            <button
              onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
              className="w-full flex items-center justify-between p-4 bg-slate-50/80 hover:bg-slate-100/80 text-left transition-colors"
            >
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <Cpu className="w-4 h-4 text-slate-500" />
                3. Technical Reasoning & Language Semantics
              </h4>
              <div className="text-slate-400">
                {showTechnicalDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </div>
            </button>
            {showTechnicalDetails && (
              <div className="p-4 border-t border-slate-200 bg-white">
                <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-line">
                  {analysis.technical_reasoning}
                </p>
              </div>
            )}
          </div>

          {/* 4. Trigger Conditions & Consequences Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Trigger Conditions */}
            <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-blue-500" />
                Trigger Conditions
              </h4>
              {analysis.trigger_conditions && analysis.trigger_conditions.length > 0 ? (
                <ul className="space-y-1.5">
                  {analysis.trigger_conditions.map((cond, idx) => (
                    <li key={idx} className="text-xs text-slate-700 flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 shrink-0" />
                      <span>{cond}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-slate-500 italic">No specific trigger conditions specified.</p>
              )}
            </div>

            {/* Potential Consequences */}
            <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Flame className="w-4 h-4 text-rose-500" />
                Potential Consequences
              </h4>
              {analysis.potential_consequences && analysis.potential_consequences.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {analysis.potential_consequences.map((cons, idx) => (
                    <span
                      key={idx}
                      className="inline-flex items-center text-xs px-2.5 py-1 rounded-md bg-rose-50 text-rose-800 border border-rose-200/60 font-medium"
                    >
                      {cons}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic">No specific failure modes specified.</p>
              )}
            </div>
          </div>

          {/* 5. Execution State Impact */}
          <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm">
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-purple-500" />
              Runtime Execution & State Impact
            </h4>
            <p className="text-sm text-slate-700 leading-relaxed">
              {analysis.execution_impact}
            </p>
          </div>
        </div>

        {/* Actionable Guidance (No Code Patches) */}
        <div className="bg-emerald-50/50 border border-emerald-200 rounded-lg p-4 space-y-3">
          <div>
            <h4 className="text-xs font-bold text-emerald-900 uppercase tracking-wider flex items-center gap-1.5 mb-1">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              Recommended Architectural Approach
            </h4>
            <p className="text-sm text-emerald-950 leading-relaxed font-medium">
              {analysis.recommended_approach}
            </p>
          </div>

          {analysis.prevention && (
            <div className="border-t border-emerald-200/70 pt-2.5">
              <h5 className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider mb-1">
                Prevention Strategy
              </h5>
              <p className="text-xs text-emerald-900 leading-relaxed">
                {analysis.prevention}
              </p>
            </div>
          )}

          {analysis.missing_context && analysis.missing_context.length > 0 && (
            <div className="border-t border-emerald-200/70 pt-2.5">
              <h5 className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider mb-1">
                Out-of-Scope Context / Information Needed
              </h5>
              <ul className="list-disc list-inside text-xs text-emerald-900 space-y-0.5">
                {analysis.missing_context.map((ctx, idx) => (
                  <li key={idx}>{ctx}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Limitations Dropdown */}
        {analysis.confidence_assessment.limitations && analysis.confidence_assessment.limitations.length > 0 && (
          <div className="border-t border-slate-200 pt-3">
            <button
              onClick={() => setShowLimitations(!showLimitations)}
              className="text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1 font-medium transition-colors"
            >
              <span>Static Analysis Boundaries & Limitations ({analysis.confidence_assessment.limitations.length})</span>
              {showLimitations ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
            {showLimitations && (
              <ul className="mt-2 space-y-1 bg-slate-50 p-3 rounded border border-slate-200 text-xs text-slate-600 list-disc list-inside">
                {analysis.confidence_assessment.limitations.map((lim, idx) => (
                  <li key={idx}>{lim}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
