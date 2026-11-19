import React, { useEffect, useState } from 'react';
import {
  X,
  History,
  Sparkles,
  Trash2,
  ChevronRight,
  ShieldCheck,
  Clock,
  FileCode,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { apiClient } from '../../services/apiClient';
import { RootCauseAnalysis, RootCauseHistoryItem } from '../../types/api';

interface RootCauseHistoryModalProps {
  isOpen: boolean;
  projectId: string;
  onClose: () => void;
  onSelectAnalysis: (analysis: RootCauseAnalysis) => void;
}

export const RootCauseHistoryModal: React.FC<RootCauseHistoryModalProps> = ({
  isOpen,
  projectId,
  onClose,
  onSelectAnalysis,
}) => {
  const [items, setItems] = useState<RootCauseHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && projectId) {
      loadHistory();
    }
  }, [isOpen, projectId]);

  const loadHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.getRootCauseHistory(projectId);
      setItems(res.analyses);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load root cause analysis history';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = async (analysisId: string) => {
    try {
      setLoading(true);
      const fullAnalysis = await apiClient.getRootCauseById(projectId, analysisId);
      onSelectAnalysis(fullAnalysis);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load selected analysis';
      setError(msg);
      setLoading(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, analysisId: string) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this root cause analysis record?')) {
      return;
    }

    try {
      setDeletingId(analysisId);
      await apiClient.deleteRootCause(projectId, analysisId);
      setItems((prev) => prev.filter((item) => item.id !== analysisId));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to delete analysis';
      setError(msg);
    } finally {
      setDeletingId(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-3xl max-h-[85vh] flex flex-col overflow-hidden">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-800">
                Root Cause Analysis History
              </h2>
              <p className="text-xs text-slate-500">
                Browse and restore previous AI investigations performed for this project
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-200/50 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {loading && items.length === 0 ? (
            <div className="py-12 flex flex-col items-center justify-center text-slate-400 space-y-2">
              <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
              <p className="text-xs">Loading analysis history...</p>
            </div>
          ) : items.length === 0 ? (
            <div className="py-12 text-center text-slate-400 space-y-3">
              <Sparkles className="w-10 h-10 mx-auto text-slate-300" />
              <div className="space-y-1">
                <p className="text-sm font-medium text-slate-600">No root cause analyses recorded</p>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  Click the "Analyze Root Cause" button on any bug finding in the detection panel to generate your first AI report.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-2.5">
              {items.map((item) => (
                <div
                  key={item.id}
                  onClick={() => handleSelect(item.id)}
                  className="p-3.5 rounded-lg border border-slate-200 hover:border-indigo-300 hover:bg-indigo-50/20 transition-all cursor-pointer flex items-center justify-between group"
                >
                  <div className="space-y-1.5 flex-1 pr-4">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                        {item.rule_id}
                      </span>
                      <span className="text-sm font-semibold text-slate-800">
                        {item.rule_name}
                      </span>
                      <span className="text-xs text-slate-400">•</span>
                      <span className="inline-flex items-center gap-1 font-mono text-xs text-slate-500">
                        <FileCode className="w-3.5 h-3.5" />
                        {item.file_path}:{item.start_line}
                      </span>
                    </div>

                    <p className="text-xs text-slate-600 line-clamp-1">
                      {item.summary}
                    </p>

                    <div className="flex items-center gap-3 text-[11px] text-slate-400">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(item.created_at).toLocaleString()}
                      </span>
                      <span>•</span>
                      <span className="flex items-center gap-1">
                        <ShieldCheck className="w-3 h-3 text-emerald-600" />
                        {item.confidence_level} ({item.confidence_score}%)
                      </span>
                      <span>•</span>
                      <span>AI: <strong className="uppercase">{item.ai_assessed_severity}</strong></span>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={(e) => handleDelete(e, item.id)}
                      disabled={deletingId === item.id}
                      className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                      title="Delete this analysis"
                    >
                      {deletingId === item.id ? (
                        <Loader2 className="w-4 h-4 animate-spin text-red-600" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </button>
                    <div className="p-1 text-slate-300 group-hover:text-indigo-600 transition-colors">
                      <ChevronRight className="w-5 h-5" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs text-slate-500">
          <span>Total Recorded Analyses: {items.length}</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-white border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-100 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
