import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Code2, Cpu, ShieldAlert, Sparkles, Terminal } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Badge } from '../components/common/Badge';

export const NewAnalysisPage: React.FC = () => {
  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Link to="/" className="btn btn-secondary btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
          <ArrowLeft size={14} />
          <span>Back to Dashboard</span>
        </Link>
        <Badge variant="warning">PHASE 2 ROADMAP</Badge>
      </div>

      <Card>
        <div style={{ textAlign: 'center', padding: '30px 20px' }}>
          <div
            style={{
              width: '56px',
              height: '56px',
              borderRadius: '12px',
              backgroundColor: 'var(--color-blue-subtle)',
              color: 'var(--color-blue-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
            }}
          >
            <Code2 size={28} />
          </div>

          <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--color-navy-900)', marginBottom: '8px' }}>
            Autonomous Code Analysis Engine
          </h2>

          <p style={{ fontSize: '14px', color: 'var(--color-navy-600)', maxWidth: '580px', margin: '0 auto 24px', lineHeight: 1.6 }}>
            The FIXMATE AI code ingestion, AST parsing, and vulnerability detection pipeline is scheduled for implementation in <strong>Phase 2</strong>.
            In Phase 1, foundational architecture, security boundaries, and API integrations are being verified.
          </p>

          <div
            style={{
              textAlign: 'left',
              backgroundColor: 'var(--color-surface-subtle)',
              border: '1px solid var(--color-border)',
              borderRadius: '8px',
              padding: '20px',
              marginTop: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
            }}
          >
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-navy-800)' }}>
              Upcoming Pipeline Features (Phase 2 & Phase 3):
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                <Terminal size={16} style={{ color: 'var(--color-blue-primary)', marginTop: '2px', flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--color-navy-900)' }}>Multi-File AST Parsing</div>
                  <div style={{ fontSize: '11.5px', color: 'var(--color-navy-500)' }}>Static syntax analysis for Python and JavaScript repositories.</div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                <Cpu size={16} style={{ color: 'var(--color-cyan-accent)', marginTop: '2px', flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--color-navy-900)' }}>Gemini Semantic Bug Detection</div>
                  <div style={{ fontSize: '11.5px', color: 'var(--color-navy-500)' }}>Context-aware flaw identification and severity categorization.</div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                <Sparkles size={16} style={{ color: 'var(--color-amber-warning)', marginTop: '2px', flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--color-navy-900)' }}>Autonomous Patch Synthesis</div>
                  <div style={{ fontSize: '11.5px', color: 'var(--color-navy-500)' }}>Synthesizes targeted diffs without overwriting unrelated code.</div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
                <ShieldAlert size={16} style={{ color: 'var(--color-green-success)', marginTop: '2px', flexShrink: 0 }} />
                <div>
                  <div style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--color-navy-900)' }}>Isolated Sandbox Verification</div>
                  <div style={{ fontSize: '11.5px', color: 'var(--color-navy-500)' }}>Automated test execution inside hermetic environments.</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};
