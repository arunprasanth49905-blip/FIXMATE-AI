import React, { useState } from 'react';
import { Sparkles, Play, CheckCircle2, AlertTriangle, XCircle, Info, RefreshCw } from 'lucide-react';
import { AIStatusResponse, AITestResponse } from '../../types/api';
import { Card } from '../common/Card';
import { Button } from '../common/Button';
import { Badge } from '../common/Badge';

interface GeminiTestCardProps {
  aiStatus: AIStatusResponse | null;
  onRunTest: () => Promise<AITestResponse>;
  onRefreshStatus?: () => void;
}

export const GeminiTestCard: React.FC<GeminiTestCardProps> = ({
  aiStatus,
  onRunTest,
  onRefreshStatus,
}) => {
  const [isRunningTest, setIsRunningTest] = useState(false);
  const [testResult, setTestResult] = useState<AITestResponse | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  const handleTestClick = async () => {
    setIsRunningTest(true);
    setTestError(null);
    try {
      const res = await onRunTest();
      setTestResult(res);
      if (onRefreshStatus) {
        onRefreshStatus();
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to execute test request';
      setTestError(msg);
    } finally {
      setIsRunningTest(false);
    }
  };

  const renderStateBadge = () => {
    if (!aiStatus) {
      return <Badge variant="neutral">UNKNOWN</Badge>;
    }
    switch (aiStatus.connection_state) {
      case 'connected':
        return <Badge variant="success">CONNECTED & VERIFIED</Badge>;
      case 'configured_untested':
        return <Badge variant="warning">CONFIGURED • UNTESTED</Badge>;
      case 'connection_failed':
        return <Badge variant="danger">TEST FAILED</Badge>;
      case 'not_configured':
      default:
        return <Badge variant="neutral">NOT CONFIGURED</Badge>;
    }
  };

  return (
    <Card>
      <div className="card-header">
        <h3 className="card-title">
          <Sparkles size={17} style={{ color: 'var(--color-cyan-accent)' }} />
          <span>Google Gemini AI Integration</span>
        </h3>
        {renderStateBadge()}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <div style={{ fontSize: '13px', color: 'var(--color-navy-600)' }}>
          {aiStatus?.message || 'Checking Gemini provider configuration status...'}
        </div>

        <div className="key-value-list">
          <div className="key-value-item">
            <span className="key-label">Provider Name</span>
            <span className="key-val">{aiStatus?.provider || 'Google Gemini'}</span>
          </div>
          <div className="key-value-item">
            <span className="key-label">Selected Model</span>
            <span className="key-val">{aiStatus?.configured_model || 'gemini-3.5-flash-lite'}</span>
          </div>
          <div className="key-value-item">
            <span className="key-label">API Key Security</span>
            <span className="key-val" style={{ color: 'var(--color-green-success)', fontSize: '12px' }}>
              ✓ Protected on Backend (Never transmitted to Client)
            </span>
          </div>
        </div>

        {/* Action Button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '4px' }}>
          <Button
            variant="primary"
            onClick={handleTestClick}
            isLoading={isRunningTest}
            data-testid="test-gemini-button"
          >
            {isRunningTest ? (
              <>
                <RefreshCw size={14} className="animate-spin" />
                <span>Testing Connection...</span>
              </>
            ) : (
              <>
                <Play size={14} />
                <span>Test Gemini Connection</span>
              </>
            )}
          </Button>

          <span style={{ fontSize: '12px', color: 'var(--color-navy-400)' }}>
            Executes a minimal harmless ping prompt on the backend
          </span>
        </div>

        {/* Test Result Display */}
        {testResult && (
          <div
            data-testid="gemini-test-result"
            style={{
              padding: '14px 16px',
              borderRadius: '8px',
              backgroundColor: testResult.success ? 'var(--color-green-subtle)' : 'var(--color-red-subtle)',
              border: `1px solid ${testResult.success ? 'var(--color-green-border)' : 'var(--color-red-border)'}`,
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600, fontSize: '13px', color: testResult.success ? 'var(--color-green-success)' : 'var(--color-red-danger)' }}>
              {testResult.success ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
              <span>{testResult.success ? 'Gemini Verification Succeeded' : 'Gemini Verification Failed'}</span>
              {testResult.latency_ms && (
                <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', fontWeight: 500, color: 'var(--color-navy-600)' }}>
                  ({testResult.latency_ms} ms)
                </span>
              )}
            </div>
            <div style={{ fontSize: '12.5px', color: 'var(--color-navy-700)' }}>
              {testResult.message}
            </div>
            {testResult.error && (
              <div style={{ fontSize: '11.5px', fontFamily: 'var(--font-mono)', color: 'var(--color-red-danger)' }}>
                Code: {testResult.error}
              </div>
            )}
          </div>
        )}

        {testError && (
          <div
            data-testid="gemini-test-client-error"
            style={{
              padding: '12px 14px',
              borderRadius: '6px',
              backgroundColor: 'var(--color-red-subtle)',
              border: '1px solid var(--color-red-border)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '12.5px',
              color: 'var(--color-red-danger)',
            }}
          >
            <AlertTriangle size={15} />
            <span>Client Error: {testError}</span>
          </div>
        )}

        {!aiStatus?.configured && (
          <div
            style={{
              padding: '10px 12px',
              borderRadius: '6px',
              backgroundColor: 'var(--color-surface-subtle)',
              border: '1px solid var(--color-border)',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px',
              fontSize: '12px',
              color: 'var(--color-navy-600)',
            }}
          >
            <Info size={14} style={{ marginTop: '2px', flexShrink: 0 }} />
            <span>
              To enable Google Gemini, generate an API key from Google AI Studio and configure <code>GEMINI_API_KEY</code> in <code>backend/.env</code>.
            </span>
          </div>
        )}
      </div>
    </Card>
  );
};
