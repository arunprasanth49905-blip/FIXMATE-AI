import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Clock } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';

interface ComingSoonPageProps {
  moduleName: string;
  phase: string;
}

export const ComingSoonPage: React.FC<ComingSoonPageProps> = ({ moduleName, phase }) => {
  return (
    <div style={{ maxWidth: '700px', margin: '40px auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Link to="/" className="btn btn-secondary btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
          <ArrowLeft size={14} />
          <span>Back to Dashboard</span>
        </Link>
        <Badge variant="neutral">COMING SOON</Badge>
      </div>

      <Card>
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              backgroundColor: 'var(--color-surface-subtle)',
              color: 'var(--color-navy-500)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
            }}
          >
            <Clock size={24} />
          </div>

          <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--color-navy-900)', marginBottom: '8px' }}>
            {moduleName} Module
          </h2>

          <p style={{ fontSize: '13.5px', color: 'var(--color-navy-600)', maxWidth: '440px', margin: '0 auto 20px' }}>
            This feature is scheduled for development in <strong>{phase}</strong>. Phase 1 focuses on core API communication, backend architecture, and Gemini integration.
          </p>
        </div>
      </Card>
    </div>
  );
};
