import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DetectionPanel } from '../components/detection/DetectionPanel';
import { DetectionRunResponse } from '../types/api';

const mockDetectionRun: DetectionRunResponse = {
  run_id: 'test-run-123',
  project_id: 'proj-456',
  analysis_id: 'analysis-789',
  status: 'completed_with_findings',
  engine_version: '1.0.0',
  created_at: '2026-11-19T10:00:00Z',
  duration_ms: 45.2,
  files_scanned: 3,
  total_findings: 3,
  severity_counts: {
    critical: 1,
    high: 1,
    medium: 1,
    low: 0,
    info: 0,
  },
  findings_by_category: {
    security: 1,
    correctness: 2,
  },
  warnings: [],
  findings: [
    {
      id: 'f-1',
      run_id: 'test-run-123',
      project_id: 'proj-456',
      rule_id: 'JS-W006',
      rule_name: 'dangerous-eval',
      language: 'JavaScript',
      severity: 'critical',
      confidence: 0.95,
      category: 'security',
      file_path: 'src/app.js',
      start_line: 14,
      start_column: 4,
      end_line: 14,
      end_column: 16,
      message: "Dangerous execution of 'eval()'",
      explanation: "Invocation of 'eval()' allows arbitrary script execution and opens severe XSS/RCE risks.",
      evidence: "const res = eval(input);",
      remediation: "Refactor away from 'eval()'; use 'JSON.parse()' or structured functions.",
    },
    {
      id: 'f-2',
      run_id: 'test-run-123',
      project_id: 'proj-456',
      rule_id: 'PY-W001',
      rule_name: 'dangerous-default-argument',
      language: 'Python',
      severity: 'high',
      confidence: 0.95,
      category: 'correctness',
      file_path: 'src/worker.py',
      start_line: 5,
      start_column: 16,
      end_line: 5,
      end_column: 18,
      message: "Mutable default argument in function 'process_batch'",
      explanation: "Default arguments are evaluated once at definition time, leading to shared state bugs.",
      evidence: "def process_batch(items=[]):",
      remediation: "Replace mutable default with 'None' and initialize inside the function body.",
    },
    {
      id: 'f-3',
      run_id: 'test-run-123',
      project_id: 'proj-456',
      rule_id: 'PY-W004',
      rule_name: 'suspicious-comparison',
      language: 'Python',
      severity: 'medium',
      confidence: 0.90,
      category: 'correctness',
      file_path: 'src/worker.py',
      start_line: 10,
      start_column: 4,
      end_line: 10,
      end_column: 16,
      message: "Comparison using '== None'. Use 'is None' instead.",
      explanation: "Singletons like None should be compared using identity 'is'.",
      evidence: "if status == None:",
      remediation: "Use 'status is None' instead.",
    },
  ],
};

describe('DetectionPanel and Deterministic Bug Engine UI', () => {
  it('1. Renders empty state when detection is null and calls onRunDetection on click', () => {
    const handleRun = vi.fn();
    const handleClose = vi.fn();
    const handleNav = vi.fn();

    render(
      <DetectionPanel
        projectId="proj-456"
        detection={null}
        isDetecting={false}
        onRunDetection={handleRun}
        onClose={handleClose}
        onNavigateToSource={handleNav}
      />
    );

    expect(screen.getByText('Deterministic Bug Detection')).toBeInTheDocument();
    expect(screen.getByText('No Bug Detection Runs Yet')).toBeInTheDocument();

    const runButtons = screen.getAllByRole('button', { name: /Run Detection/i });
    fireEvent.click(runButtons[0]);
    expect(handleRun).toHaveBeenCalledTimes(1);
  });

  it('2. Renders severity counters and finding cards with rule IDs and messages', () => {
    const handleNav = vi.fn();

    render(
      <DetectionPanel
        projectId="proj-456"
        detection={mockDetectionRun}
        isDetecting={false}
        onRunDetection={vi.fn()}
        onClose={vi.fn()}
        onNavigateToSource={handleNav}
      />
    );

    // Severity metric chips
    expect(screen.getByText('CRIT')).toBeInTheDocument();
    expect(screen.getAllByText('HIGH').length).toBeGreaterThan(0);
    expect(screen.getByText('MED')).toBeInTheDocument();

    // Findings listed
    expect(screen.getByText('JS-W006')).toBeInTheDocument();
    expect(screen.getByText("Dangerous execution of 'eval()'")).toBeInTheDocument();
    expect(screen.getByText('PY-W001')).toBeInTheDocument();
    expect(screen.getByText("Mutable default argument in function 'process_batch'")).toBeInTheDocument();
    expect(screen.getByText('PY-W004')).toBeInTheDocument();
  });

  it('3. Filters findings when clicking severity chip or typing in search filter', () => {
    render(
      <DetectionPanel
        projectId="proj-456"
        detection={mockDetectionRun}
        isDetecting={false}
        onRunDetection={vi.fn()}
        onClose={vi.fn()}
        onNavigateToSource={vi.fn()}
      />
    );

    // Filter by Critical
    fireEvent.click(screen.getByTestId('sev-chip-critical'));

    expect(screen.getByText('JS-W006')).toBeInTheDocument();
    expect(screen.queryByText('PY-W001')).not.toBeInTheDocument();

    // Reset severity filter
    fireEvent.click(screen.getByText('Clear severity filter'));
    expect(screen.getByText('PY-W001')).toBeInTheDocument();

    // Search query filter
    const searchInput = screen.getByPlaceholderText(/Filter findings by keyword/i);
    fireEvent.change(searchInput, { target: { value: 'dangerous-eval' } });

    expect(screen.getByText('JS-W006')).toBeInTheDocument();
    expect(screen.queryByText('PY-W001')).not.toBeInTheDocument();
  });

  it('4. Expands finding to display code evidence, explanation, and remediation', () => {
    render(
      <DetectionPanel
        projectId="proj-456"
        detection={mockDetectionRun}
        isDetecting={false}
        onRunDetection={vi.fn()}
        onClose={vi.fn()}
        onNavigateToSource={vi.fn()}
      />
    );

    // Click finding row to expand
    fireEvent.click(screen.getByTestId('finding-row-f-1'));

    expect(screen.getByText(/arbitrary script execution/i)).toBeInTheDocument();
    expect(screen.getByText('const res = eval(input);')).toBeInTheDocument();
    expect(screen.getByText(/Suggested Remediation/i)).toBeInTheDocument();
    expect(screen.getByText(/Refactor away/i)).toBeInTheDocument();
  });

  it('5. Clicking Jump button invokes onNavigateToSource with exact file and line coordinates', () => {
    const handleNav = vi.fn();

    render(
      <DetectionPanel
        projectId="proj-456"
        detection={mockDetectionRun}
        isDetecting={false}
        onRunDetection={vi.fn()}
        onClose={vi.fn()}
        onNavigateToSource={handleNav}
      />
    );

    fireEvent.click(screen.getByTestId('jump-btn-f-1'));

    expect(handleNav).toHaveBeenCalledWith('src/app.js', 14, 4);
  });
});
