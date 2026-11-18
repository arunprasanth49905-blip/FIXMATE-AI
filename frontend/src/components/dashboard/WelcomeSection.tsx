import React from 'react';
import { Link } from 'react-router-dom';
import { PlusCircle, Sparkles } from 'lucide-react';

export const WelcomeSection: React.FC = () => {
  return (
    <div className="welcome-banner">
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
          <h2 className="welcome-title">FIXMATE AI Dashboard</h2>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              padding: '2px 8px',
              borderRadius: '9999px',
              fontSize: '11px',
              fontWeight: 600,
              backgroundColor: 'var(--color-blue-subtle)',
              color: 'var(--color-blue-primary)',
            }}
          >
            <Sparkles size={11} /> Phase 1 Live
          </span>
        </div>
        <p className="welcome-desc">
          Autonomous bug detection and intelligent code repair platform.
          Phase 1 establishes real-time backend health monitoring, system architecture telemetry,
          and secure Google Gemini integration.
        </p>
      </div>
      <div>
        <Link to="/analysis" className="btn btn-primary" style={{ whiteSpace: 'nowrap' }}>
          <PlusCircle size={15} />
          <span>New Analysis</span>
        </Link>
      </div>
    </div>
  );
};
