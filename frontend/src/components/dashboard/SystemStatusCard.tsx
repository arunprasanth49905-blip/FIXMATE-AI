import React from 'react';
import { Server, Activity, ShieldCheck, Cpu } from 'lucide-react';
import { HealthResponse, SystemInfoResponse, AIStatusResponse } from '../../types/api';
import { Card } from '../common/Card';
import { Badge } from '../common/Badge';

interface SystemStatusCardProps {
  health: HealthResponse | null;
  systemInfo: SystemInfoResponse | null;
  aiStatus: AIStatusResponse | null;
  isLoading: boolean;
  error: string | null;
}

export const SystemStatusCard: React.FC<SystemStatusCardProps> = ({
  health,
  systemInfo,
  aiStatus,
  isLoading,
  error,
}) => {
  return (
    <Card>
      <div className="card-header">
        <h3 className="card-title">
          <Server size={17} style={{ color: 'var(--color-blue-primary)' }} />
          <span>System & Backend Architecture</span>
        </h3>
        <Badge variant={health ? 'success' : error ? 'danger' : 'neutral'}>
          {health ? 'LIVE TELEMETRY' : error ? 'OFFLINE' : 'CONNECTING'}
        </Badge>
      </div>

      {isLoading ? (
        <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--color-navy-500)', fontSize: '13px' }}>
          Fetching system diagnostics from backend...
        </div>
      ) : error ? (
        <div style={{ padding: '16px', backgroundColor: 'var(--color-red-subtle)', border: '1px solid var(--color-red-border)', borderRadius: '6px' }}>
          <div style={{ fontWeight: 600, color: 'var(--color-red-danger)', fontSize: '13px', marginBottom: '4px' }}>
            Backend Communication Failed
          </div>
          <div style={{ fontSize: '12px', color: 'var(--color-navy-700)' }}>
            {error}. Ensure the FastAPI server is running on port 8001.
          </div>
        </div>
      ) : (
        <div className="key-value-list">
          <div className="key-value-item">
            <span className="key-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Activity size={14} /> Service Name
            </span>
            <span className="key-val">{systemInfo?.application_name || health?.service || 'N/A'}</span>
          </div>

          <div className="key-value-item">
            <span className="key-label">API Version / Environment</span>
            <span className="key-val">
              v{systemInfo?.version || health?.version || 'N/A'} ({systemInfo?.environment || health?.environment || 'unknown'})
            </span>
          </div>

          <div className="key-value-item">
            <span className="key-label">REST API Prefix</span>
            <span className="key-val">{systemInfo?.api_prefix || '/api/v1'}</span>
          </div>

          <div className="key-value-item">
            <span className="key-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldCheck size={14} /> Supported Core Languages
            </span>
            <div style={{ display: 'flex', gap: '6px' }}>
              {systemInfo?.supported_languages?.map((lang) => (
                <Badge key={lang} variant="blue">{lang}</Badge>
              )) || <span className="key-val">Python, JavaScript</span>}
            </div>
          </div>

          <div className="key-value-item">
            <span className="key-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Cpu size={14} /> AI Engine Provider
            </span>
            <span className="key-val">
              {aiStatus?.provider || 'Google Gemini'} ({aiStatus?.configured_model || 'gemini-3.5-flash-lite'})
            </span>
          </div>

          <div className="key-value-item">
            <span className="key-label">Server Timestamp</span>
            <span className="key-val" style={{ fontSize: '11.5px', color: 'var(--color-navy-500)' }}>
              {health?.timestamp ? new Date(health.timestamp).toLocaleString() : 'N/A'}
            </span>
          </div>
        </div>
      )}
    </Card>
  );
};
