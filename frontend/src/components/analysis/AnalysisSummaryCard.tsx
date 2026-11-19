import React from 'react';
import { AlertTriangle, Clock, FileCode, Layers, GitBranch, ShieldAlert } from 'lucide-react';
import { ProjectAnalysisResponse } from '../../types/api';
import { Badge } from '../common/Badge';

interface AnalysisSummaryCardProps {
  analysis: ProjectAnalysisResponse;
}

export const AnalysisSummaryCard: React.FC<AnalysisSummaryCardProps> = ({ analysis }) => {
  const { statistics: stats, language_distribution: langDist, warnings } = analysis;

  const getStatusBadge = () => {
    switch (analysis.status) {
      case 'completed':
        return <Badge variant="success">PARSING COMPLETED</Badge>;
      case 'completed_with_diagnostics':
        return <Badge variant="warning">COMPLETED WITH DIAGNOSTICS</Badge>;
      case 'failed':
        return <Badge variant="danger">PARSING FAILED</Badge>;
      default:
        return <Badge variant="neutral">{analysis.status.toUpperCase()}</Badge>;
    }
  };

  const totalLangFiles = Object.values(langDist).reduce((acc, curr) => acc + curr, 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Top Status & Duration Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {getStatusBadge()}
          <span style={{ fontSize: '12px', color: 'var(--color-navy-500)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <Clock size={12} /> {stats.duration_ms} ms
          </span>
        </div>
        <span style={{ fontSize: '12px', color: 'var(--color-navy-500)' }}>
          Analyzed at {new Date(analysis.end_time).toLocaleTimeString()}
        </span>
      </div>

      {/* Metrics Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '12px',
        }}
      >
        <div style={{ padding: '12px', borderRadius: '8px', border: '1px solid var(--color-border)', backgroundColor: 'var(--color-surface)' }}>
          <div style={{ fontSize: '11px', color: 'var(--color-navy-500)', textTransform: 'uppercase', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
            <FileCode size={13} style={{ color: 'var(--color-blue-primary)' }} /> Files Parsed
          </div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--color-navy-900)', marginTop: '4px' }}>
            {stats.parsed_files} <span style={{ fontSize: '12px', color: 'var(--color-navy-400)', fontWeight: 400 }}>/ {stats.supported_files}</span>
          </div>
        </div>

        <div style={{ padding: '12px', borderRadius: '8px', border: '1px solid var(--color-border)', backgroundColor: 'var(--color-surface)' }}>
          <div style={{ fontSize: '11px', color: 'var(--color-navy-500)', textTransform: 'uppercase', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
            <Layers size={13} style={{ color: 'var(--color-cyan-primary)' }} /> Functions
          </div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--color-navy-900)', marginTop: '4px' }}>
            {stats.total_functions} <span style={{ fontSize: '12px', color: 'var(--color-navy-400)', fontWeight: 400 }}>({stats.total_async_functions} async)</span>
          </div>
        </div>

        <div style={{ padding: '12px', borderRadius: '8px', border: '1px solid var(--color-border)', backgroundColor: 'var(--color-surface)' }}>
          <div style={{ fontSize: '11px', color: 'var(--color-navy-500)', textTransform: 'uppercase', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
            <GitBranch size={13} style={{ color: 'var(--color-blue-dark)' }} /> Classes
          </div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--color-navy-900)', marginTop: '4px' }}>
            {stats.total_classes} <span style={{ fontSize: '12px', color: 'var(--color-navy-400)', fontWeight: 400 }}>({stats.total_methods} methods)</span>
          </div>
        </div>

        <div style={{ padding: '12px', borderRadius: '8px', border: '1px solid var(--color-border)', backgroundColor: 'var(--color-surface)' }}>
          <div style={{ fontSize: '11px', color: 'var(--color-navy-500)', textTransform: 'uppercase', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
            <FileCode size={13} style={{ color: 'var(--color-navy-500)' }} /> Imports
          </div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--color-navy-900)', marginTop: '4px' }}>
            {stats.total_imports}
          </div>
        </div>

        <div style={{ padding: '12px', borderRadius: '8px', border: '1px solid var(--color-border)', backgroundColor: 'var(--color-surface)' }}>
          <div style={{ fontSize: '11px', color: stats.total_diagnostics > 0 ? 'var(--color-amber-warning)' : 'var(--color-green-success)', textTransform: 'uppercase', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
            <ShieldAlert size={13} /> Diagnostics
          </div>
          <div style={{ fontSize: '20px', fontWeight: 700, color: stats.total_diagnostics > 0 ? 'var(--color-amber-warning)' : 'var(--color-green-success)', marginTop: '4px' }}>
            {stats.total_diagnostics}
          </div>
        </div>
      </div>

      {/* Language Breakdown */}
      <div style={{ padding: '14px', borderRadius: '8px', border: '1px solid var(--color-border)', backgroundColor: 'var(--color-surface-subtle)' }}>
        <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-navy-700)', marginBottom: '8px' }}>
          Language Breakdown ({totalLangFiles} files analyzed)
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {Object.entries(langDist).map(([lang, count]) => {
            const pct = totalLangFiles > 0 ? Math.round((count / totalLangFiles) * 100) : 0;
            let badgeVar: 'blue' | 'neutral' = 'neutral';
            if (lang === 'Python' || lang === 'JavaScript' || lang === 'TypeScript') badgeVar = 'blue';

            return (
              <div key={lang} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px' }}>
                <Badge variant={badgeVar}>{lang}</Badge>
                <span style={{ fontWeight: 600, color: 'var(--color-navy-900)' }}>{count}</span>
                <span style={{ color: 'var(--color-navy-400)', fontSize: '11.5px' }}>({pct}%)</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Warnings & Skipped Files */}
      {warnings && warnings.length > 0 && (
        <div style={{ padding: '10px 14px', borderRadius: '6px', backgroundColor: 'var(--color-amber-subtle)', border: '1px solid var(--color-amber-warning)', fontSize: '12px', color: 'var(--color-navy-900)' }}>
          <div style={{ fontWeight: 600, marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <AlertTriangle size={14} style={{ color: 'var(--color-amber-warning)' }} /> Analysis Warnings
          </div>
          <ul style={{ margin: 0, paddingLeft: '18px' }}>
            {warnings.map((w, idx) => (
              <li key={idx}>{w}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
