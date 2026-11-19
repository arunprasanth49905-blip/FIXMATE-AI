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
  rule_id: 'PY-W007',
  rule_name: 'Division by Zero',
  language: 'Python',
  file_path: 'src/pricing.py',
  start_line: 2,
  end_line: 2,
  model: 'gemini-3.5-flash-lite',
  created_at: '2026-11-19T14:30:00Z',
  duration_ms: 185.5,
  status: 'success',
  bug_location: {
    file: 'src/pricing.py',
    line: 2,
    rule_id: 'PY-W007',
    language: 'Python',
  },
  original_code: 'return price * discount / 0',
  simple_explanation: 'This code divides a number by zero, which causes Python to raise an exception and crash.',
  root_cause: 'The divisor in the calculation is hardcoded as zero.',
  corrected_code: 'return price * discount / 100',
  correction_explanation: 'Changed the divisor to 100 assuming discount is a percentage.',
  assumptions: ['The discount variable is intended to represent a percentage.'],
  fix_status: 'suggested_not_applied',
  summary: 'Division by zero in pricing formula',
  bug_explanation: 'Dividing by zero is mathematically undefined.',
  technical_reasoning: 'Python raises ZeroDivisionError on integer or float division by 0.',
  trigger_conditions: ['Invoking discount calculation function'],
  execution_impact: 'Immediate crash with ZeroDivisionError',
  potential_consequences: ['Uncaught ZeroDivisionError', 'Service 500 error'],
  severity_assessment: {
    detected_severity: 'high',
    ai_assessed_severity: 'high',
    severity_reasoning: 'Deterministic crash upon calling function.',
    severity_changed: false,
  },
  recommended_approach: 'Change denominator to 100 for percentage calculation.',
  prevention: 'Configure static analysis rule PY-W007.',
  missing_context: [],
  confidence_assessment: {
    confidence_score: 98.0,
    confidence_level: 'HIGH',
    confidence_reason: 'Literal zero in division operator leaves no ambiguity.',
    limitations: [],
  },
};

const mockDetectionRun: DetectionRunResponse = {
  run_id: 'run-1',
  project_id: 'proj-123',
  status: 'completed_with_findings',
  engine_version: '1.0.0',
  created_at: '2026-11-19T14:00:00Z',
  duration_ms: 32.1,
  files_scanned: 1,
  total_findings: 1,
  severity_counts: {
    critical: 0,
    high: 1,
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
      rule_id: 'PY-W007',
      rule_name: 'Division by Zero',
      language: 'Python',
      severity: 'high',
      confidence: 0.98,
      category: 'correctness',
      file_path: 'src/pricing.py',
      start_line: 2,
      start_column: 12,
      end_line: 2,
      end_column: 32,
      message: 'Division by literal zero',
      explanation: 'Dividing by zero raises ZeroDivisionError.',
      evidence: 'return price * discount / 0',
      remediation: 'Change divisor to non-zero.',
    },
  ],
};

describe('Phase 5: Upgraded AI RCA Intelligence & Code Correction', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockImplementation(() => Promise.resolve()),
      },
    });
  });

  it('renders concise RCA card with exact error location, simple explanation, and corrected code', () => {
    const onNavigate = vi.fn();
    render(<RootCauseAnalysisCard analysis={mockAnalysis} onNavigateToFile={onNavigate} />);

    // 1. Bug Location & Navigation
    expect(screen.getByText('Division by Zero')).toBeDefined();
    expect(screen.getByText('src/pricing.py')).toBeDefined();
    expect(screen.getByText('2')).toBeDefined();
    expect(screen.getByText('View Error in Editor')).toBeDefined();

    // 2. Original Buggy Code (Red/Error context)
    expect(screen.getByText('Error Code (Line 2)')).toBeDefined();
    expect(screen.getByText('return price * discount / 0')).toBeDefined();

    // 3. What Went Wrong? (Simple English)
    expect(screen.getByText('What Went Wrong?')).toBeDefined();
    expect(
      screen.getByText('This code divides a number by zero, which causes Python to raise an exception and crash.')
    ).toBeDefined();

    // 4. Root Cause
    expect(screen.getByText('Root Cause')).toBeDefined();
    expect(screen.getByText('The divisor in the calculation is hardcoded as zero.')).toBeDefined();

    // 5. Corrected Code (Green/Success context)
    expect(screen.getByText('Corrected Code')).toBeDefined();
    expect(screen.getByText('return price * discount / 100')).toBeDefined();
    expect(screen.getByText('Suggested Fix (Not Applied)')).toBeDefined();

    // 6. What Changed?
    expect(screen.getByText('What Changed?')).toBeDefined();
    expect(screen.getByText('Changed the divisor to 100 assuming discount is a percentage.')).toBeDefined();

    // 7. AI Assumptions
    expect(screen.getByText('AI Assumptions & Inferences')).toBeDefined();
    expect(screen.getByText('The discount variable is intended to represent a percentage.')).toBeDefined();

    // 8. Severity & Confidence metrics
    expect(screen.getByText('high')).toBeDefined();
    expect(screen.getByText('98% (HIGH)')).toBeDefined();
  });

  it('handles "View Error in Editor" click to jump to exact file and line', () => {
    const onNavigate = vi.fn();
    render(<RootCauseAnalysisCard analysis={mockAnalysis} onNavigateToFile={onNavigate} />);

    const jumpBtn = screen.getByTestId('view-in-editor-btn');
    fireEvent.click(jumpBtn);

    expect(onNavigate).toHaveBeenCalledWith('src/pricing.py', 2);
  });

  it('handles Copy buttons for original code and corrected code', async () => {
    render(<RootCauseAnalysisCard analysis={mockAnalysis} />);

    // Copy original code
    const copyOriginalBtn = screen.getByTestId('copy-original-btn');
    fireEvent.click(copyOriginalBtn);
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('return price * discount / 0');

    // Copy corrected code
    const copyCorrectedBtn = screen.getByTestId('copy-corrected-btn');
    fireEvent.click(copyCorrectedBtn);
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('return price * discount / 100');
  });

  it('triggers AI root cause analysis from DetectionPanel and displays the upgraded card', async () => {
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
    expect(screen.getByText('Division by literal zero')).toBeDefined();

    // Click Analyze RCA button
    const analyzeBtn = screen.getByTestId('analyze-btn-f-1');
    fireEvent.click(analyzeBtn);

    expect(apiClient.analyzeFinding).toHaveBeenCalledWith('proj-123', {
      finding_id: 'f-1',
      include_surrounding_context: true,
      custom_user_notes: undefined,
    });

    // Wait for analysis card to render
    await waitFor(() => {
      expect(screen.getByText('What Went Wrong?')).toBeDefined();
      expect(screen.getByText('return price * discount / 100')).toBeDefined();
      expect(screen.getByText('98% (HIGH)')).toBeDefined();
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
          rule_id: 'PY-W007',
          rule_name: 'Division by Zero',
          file_path: 'src/pricing.py',
          start_line: 2,
          summary: 'Division by zero in pricing formula',
          original_code: 'return price * discount / 0',
          corrected_code: 'return price * discount / 100',
          fix_status: 'suggested_not_applied',
          detected_severity: 'high',
          ai_assessed_severity: 'high',
          confidence_score: 98.0,
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

    await waitFor(() => {
      expect(screen.getByText('Division by Zero')).toBeDefined();
      expect(screen.getByText(/src\/pricing.py:2/)).toBeDefined();
    });

    // Click item to restore
    fireEvent.click(screen.getByText('Division by Zero'));

    await waitFor(() => {
      expect(apiClient.getRootCauseById).toHaveBeenCalledWith('proj-123', 'rca-101');
      expect(onSelect).toHaveBeenCalledWith(mockAnalysis);
      expect(onClose).toHaveBeenCalled();
    });
  });
});
