import React from 'react';
import { RefreshCw, CheckCircle2, AlertCircle, Clock } from 'lucide-react';

export type StatusState = 'connected' | 'disconnected' | 'checking' | 'warning' | 'neutral';

interface StatusIndicatorProps {
  state: StatusState;
  label?: string;
  showIcon?: boolean;
  onRetry?: () => void;
  isRetrying?: boolean;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  state,
  label,
  showIcon = true,
  onRetry,
  isRetrying = false,
}) => {
  const getLabel = () => {
    if (label) return label;
    switch (state) {
      case 'connected':
        return 'Backend Available';
      case 'disconnected':
        return 'Backend Unavailable';
      case 'checking':
        return 'Checking Connection...';
      case 'warning':
        return 'Attention Needed';
      case 'neutral':
        return 'Not Configured';
      default:
        return 'Unknown';
    }
  };

  const renderIcon = () => {
    if (!showIcon) return null;
    switch (state) {
      case 'connected':
        return <CheckCircle2 size={13} />;
      case 'disconnected':
        return <AlertCircle size={13} />;
      case 'checking':
        return <Clock size={13} className="animate-spin" />;
      case 'warning':
        return <AlertCircle size={13} />;
      case 'neutral':
        return <span className="status-dot" />;
    }
  };

  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
      <span className={`status-pill ${state}`} data-testid={`status-indicator-${state}`}>
        {renderIcon()}
        <span>{getLabel()}</span>
      </span>

      {state === 'disconnected' && onRetry && (
        <button
          type="button"
          onClick={onRetry}
          disabled={isRetrying}
          className="btn btn-secondary btn-sm"
          style={{ padding: '3px 8px', fontSize: '11px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
          data-testid="retry-backend-button"
        >
          <RefreshCw size={11} className={isRetrying ? 'animate-spin' : ''} />
          <span>{isRetrying ? 'Retrying...' : 'Retry'}</span>
        </button>
      )}
    </div>
  );
};
