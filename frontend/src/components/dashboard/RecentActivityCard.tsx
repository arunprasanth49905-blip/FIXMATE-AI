import React from 'react';
import { Clock, Info } from 'lucide-react';
import { Card } from '../common/Card';

export const RecentActivityCard: React.FC = () => {
  return (
    <Card style={{ marginTop: '20px' }}>
      <div className="card-header">
        <h3 className="card-title">
          <Clock size={17} style={{ color: 'var(--color-navy-600)' }} />
          <span>Recent Activity Stream</span>
        </h3>
        <span style={{ fontSize: '11px', color: 'var(--color-navy-400)', fontFamily: 'var(--font-mono)' }}>
          EMPTY LOG
        </span>
      </div>

      <div
        style={{
          padding: '32px 16px',
          textAlign: 'center',
          backgroundColor: 'var(--color-surface-subtle)',
          borderRadius: '8px',
          border: '1px dashed var(--color-border)',
        }}
      >
        <Info size={24} style={{ color: 'var(--color-navy-400)', margin: '0 auto 8px' }} />
        <div style={{ fontSize: '13.5px', fontWeight: 600, color: 'var(--color-navy-700)', marginBottom: '4px' }}>
          No Activity Recorded Yet
        </div>
        <p style={{ fontSize: '12.5px', color: 'var(--color-navy-500)', maxWidth: '480px', margin: '0 auto' }}>
          Real project activities, AST analysis events, and automated repair diffs will populate this timeline
          as analysis jobs are executed in Phase 2.
        </p>
      </div>
    </Card>
  );
};
