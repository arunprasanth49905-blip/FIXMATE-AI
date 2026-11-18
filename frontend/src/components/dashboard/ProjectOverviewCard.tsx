import React from 'react';
import { FolderGit2, Bug, Wrench, ShieldAlert } from 'lucide-react';

interface MetricBoxProps {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  subtitle: string;
}

const MetricBox: React.FC<MetricBoxProps> = ({ icon, label, value, subtitle }) => {
  return (
    <div className="metric-card">
      <div className="metric-header">
        <span className="metric-title">{label}</span>
        {icon}
      </div>
      <div className="metric-value">{value}</div>
      <div className="metric-note">{subtitle}</div>
    </div>
  );
};

export const ProjectOverviewCard: React.FC = () => {
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px', marginTop: '24px' }}>
        <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-navy-900)' }}>
          Analysis & Autonomous Repair Metrics
        </h3>
        <span style={{ fontSize: '12px', color: 'var(--color-navy-400)' }}>
          Honest State • Phase 1
        </span>
      </div>

      <div className="grid-4" style={{ marginTop: 0 }}>
        <MetricBox
          icon={<FolderGit2 size={18} style={{ color: 'var(--color-blue-primary)' }} />}
          label="Projects Analyzed"
          value="0"
          subtitle="No projects ingested yet"
        />

        <MetricBox
          icon={<Bug size={18} style={{ color: 'var(--color-red-danger)' }} />}
          label="Bugs Detected"
          value="0"
          subtitle="Bug detection starts in Phase 2"
        />

        <MetricBox
          icon={<Wrench size={18} style={{ color: 'var(--color-cyan-accent)' }} />}
          label="Repairs Completed"
          value="0"
          subtitle="Repair pipeline scheduled for Phase 3"
        />

        <MetricBox
          icon={<ShieldAlert size={18} style={{ color: 'var(--color-amber-warning)' }} />}
          label="Verification Rate"
          value="—"
          subtitle="Awaiting automated test suite"
        />
      </div>
    </div>
  );
};
