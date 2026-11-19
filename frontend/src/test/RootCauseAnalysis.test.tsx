import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RootCauseAnalysisCard } from '../components/root_cause/RootCauseAnalysisCard';
import { RootCauseHistoryModal } from '../components/root_cause/RootCauseHistoryModal';
import { DetectionPanel } from '../components/detection/DetectionPanel';
import { RootCauseAnalysis, DetectionRunResponse } from '../types/api';
import { apiClient } from '../services/apiClient';

vi.mock('../services/apiClient');

const mockAnalysis: RootCauseAnalysis = {
  id: 'rca-101',
  project_id: 'proj-123',
  finding_id: 'f-1',
  detection_run_id: 'run-1',
  rule_id: 'PY-E001',
  rule_name: 'Undefined Variable Used',
  language: 'Python',
  file_path: 'src/billing.py',
  start_line: 15,
  end_line: 15,
  model: 'gemini-2.5-flash',
  created_at: '2026-11-19T14:30:00Z',
  duration_ms: 185.5,
  status: 'success',
  summary: 'Accumulator variable referenced prior to initialization in loop scope',
  bug_explanation: "The variable 'total' is augmented inside the loop but was never declared in the enclosing scope.",
  root_cause: 'Missing variable declaration before entering the accumulator loop.',
  technical_reasoning: 'In Python, augmented assignment assigns to local scope. Because RHS is evaluated first, UnboundLocalError is raised.',
  trigger_conditions: ['Invoking function with a non-empty items array', 'First loop iteration'],
  execution_impact: 'Immediate runtime crash halts request processing.',
  potential_consequences: ['Uncaught UnboundLocalError', 'Service 500 error', 'Transaction abort'],
  severity_assessment: {
    detected_severity: 'critical',
    ai_assessed_severity: 'critical',
    severity_reasoning: 'Agreed: Function completely fails on runtime execution.',
    severity_changed: false,
  },
  recommended_approach: "Initialize 'total = 0' immediately above the 'for item in items:' loop construct.",
  prevention: 'Configure static checkers (e.g. Ruff or Pyflakes) in pre-commit hooks.',
  missing_context: ['Calling function signature in order_processor.py'],
  confidence_assessment: {
    confidence_score: 96.0,
    confidence_level: 'HIGH',
    confidence_reason: 'Local function scope has full visibility without external dynamic variables.',
    limitations: ['Static AST does not verify caller arguments.'],
  },
};

const mockDetectionRun: DetectionRunResponse = {
  run_id: 'run-1',
  project_id: 'proj-123',
  status: 'completed_with_findings',
  engine_version: '1.0.0',
  created_at: '2026-11-19T14:00:00Z',
  duration_ms: 32.1,
  files_scanned: 2,
  total_findings: 1,
  severity_counts: {
    critical: 1,
    high: 0,
    medium: 0,
    low: 0,
    info: 0,
  },
  findings_by_category: {
    correctness: 1,
  },
  warnings: [],
  findings: [
    {
      id: 'f-1',
      run_id: 'run-1',
      project_id: 'proj-123',
      rule_id: 'PY-E001',
      rule_name: 'Undefined Variable Used',
      language: 'Python',
      severity: 'critical',
      confidence: 0.95,
      category: 'correctness',
      file_path: 'src/billing.py',
      start_line: 15,
      start_column: 8,
      end_line: 15,
      end_column: 13,
      message: "Local variable 'total' referenced before assignment",
      explanation: 'Augmented assignment requires variable to exist beforehand.',
      evidence: "total += item['amount']",
      remediation: 'Initialize total = 0 before the loop.',
    },
  ],
};

describe('Phase 5: AI Root Cause Analysis Frontend', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders RootCauseAnalysisCard with all rich technical sections', () => {
    render(<RootCauseAnalysisCard analysis={mockAnalysis} />);

    // Header & Summary
    expect(screen.getByText('Undefined Variable Used')).toBeDefined();
    expect(screen.getByText(/src\/billing.py:15/)).toBeDefined();
    expect(screen.getByText(mockAnalysis.summary)).toBeDefined();

    // Dual Severity Evaluation
    expect(screen.getByText('Severity Evaluation')).toBeDefined();
    expect(screen.getByText('Aligned')).toBeDefined();
    expect(screen.getByText(/"Agreed: Function completely fails on runtime execution."/)).toBeDefined();

    // Calibrated Confidence Breakdown
    expect(screen.getByText('HIGH (96%)')).toBeDefined();
    expect(screen.getByText(mockAnalysis.confidence_assessment.confidence_reason)).toBeDefined();

    // Technical Investigation Breakdown
    expect(screen.getByText(/The variable 'total' is augmented inside the loop/)).toBeDefined();
    expect(screen.getByText(mockAnalysis.root_cause)).toBeDefined();
    expect(screen.getByText(mockAnalysis.execution_impact)).toBeDefined();
    expect(screen.getByText('Uncaught UnboundLocalError')).toBeDefined();

    // Actionable Guidance (No Code Patches)
    expect(screen.getByText(mockAnalysis.recommended_approach)).toBeDefined();
    expect(screen.getByText(mockAnalysis.prevention)).toBeDefined();
  });

  it('renders divergent severity badge when AI disagrees with static severity', () => {
    const divergentAnalysis: RootCauseAnalysis = {
      ...mockAnalysis,
      severity_assessment: {
        detected_severity: 'medium',
        ai_assessed_severity: 'critical',
        severity_reasoning: 'Critical because it can be reached without authentication.',
        severity_changed: true,
      },
    };

    render(<RootCauseAnalysisCard analysis={divergentAnalysis} />);
    expect(screen.getByText('AI Assesses Differently')).toBeDefined();
    expect(screen.getByText('critical')).toBeDefined();
  });

  it('triggers AI root cause analysis from DetectionPanel and displays the card', async () => {
    vi.mocked(apiClient.analyzeFinding).mockResolvedValueOnce(mockAnalysis);

    render(
      <DetectionPanel
        projectId="proj-123"
        detection={mockDetectionRun}
        isDetecting={false}
        onRunDetection={vi.fn()}
        onClose={vi.fn()}
        onNavigateToSource={vi.fn()}
      />
    );

    // Initial finding row
    expect(screen.getByText("Local variable 'total' referenced before assignment")).toBeDefined();

    // Click Analyze RCA button
    const analyzeBtn = screen.getByTestId('analyze-btn-f-1');
    fireEvent.click(analyzeBtn);

    // Verify API called with finding ID
    expect(apiClient.analyzeFinding).toHaveBeenCalledWith('proj-123', {
      finding_id: 'f-1',
      include_surrounding_context: true,
      custom_user_notes: undefined,
    });

    // Wait for analysis card to render
    await waitFor(() => {
      expect(screen.getByText(mockAnalysis.summary)).toBeDefined();
      expect(screen.getByText('HIGH (96%)')).toBeDefined();
    });
  });

  it('opens RootCauseHistoryModal and allows selecting past analysis', async () => {
    vi.mocked(apiClient.getRootCauseHistory).mockResolvedValueOnce({
      project_id: 'proj-123',
      total: 1,
      analyses: [
        {
          id: 'rca-101',
          project_id: 'proj-123',
          finding_id: 'f-1',
          rule_id: 'PY-E001',
          rule_name: 'Undefined Variable Used',
          file_path: 'src/billing.py',
          start_line: 15,
          summary: 'Accumulator variable referenced prior to initialization in loop scope',
          detected_severity: 'critical',
          ai_assessed_severity: 'critical',
          confidence_score: 96.0,
          confidence_level: 'HIGH',
          created_at: '2026-11-19T14:30:00Z',
          duration_ms: 185.5,
          status: 'success',
        },
      ],
    });
    vi.mocked(apiClient.getRootCauseById).mockResolvedValueOnce(mockAnalysis);

    const onSelect = vi.fn();
    const onClose = vi.fn();

    render(
      <RootCauseHistoryModal
        isOpen={true}
        projectId="proj-123"
        onClose={onClose}
        onSelectAnalysis={onSelect}
      />
    );

    // Check history items load
    await waitFor(() => {
      expect(screen.getByText('Undefined Variable Used')).toBeDefined();
      expect(screen.getByText(/src\/billing.py:15/)).toBeDefined();
    });

    // Click item to restore
    fireEvent.click(screen.getByText('Undefined Variable Used'));

    await waitFor(() => {
      expect(apiClient.getRootCauseById).toHaveBeenCalledWith('proj-123', 'rca-101');
      expect(onSelect).toHaveBeenCalledWith(mockAnalysis);
      expect(onClose).toHaveBeenCalled();
    });
  });
});
