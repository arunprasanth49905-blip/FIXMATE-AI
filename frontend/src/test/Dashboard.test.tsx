import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { App } from '../app/App';
import { apiClient } from '../services/apiClient';

// Mock apiClient methods
vi.mock('../services/apiClient', () => ({
  apiClient: {
    getHealth: vi.fn(),
    getSystemInfo: vi.fn(),
    getAIStatus: vi.fn(),
    testAIConnection: vi.fn(),
    getProjects: vi.fn().mockResolvedValue({ total: 0, projects: [] }),
    getLatestAnalysis: vi.fn().mockRejectedValue(new Error('no analysis')),
  },
  parseErrorMessage: (err: any, fallback = 'Error') =>
    typeof err === 'string' ? err : err?.message || fallback,
  ApiClientError: class extends Error {
    status?: number;
    constructor(msg: string, status?: number) {
      super(msg);
      this.status = status;
    }
  },
}));

describe('FIXMATE AI Dashboard and Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('1. Dashboard renders with welcome section and metrics', async () => {
    vi.mocked(apiClient.getHealth).mockResolvedValue({
      service: 'FIXMATE AI',
      status: 'healthy',
      version: '0.1.0',
      environment: 'development',
      timestamp: '2026-11-18T18:00:00Z',
    });
    vi.mocked(apiClient.getSystemInfo).mockResolvedValue({
      application_name: 'FIXMATE AI',
      version: '0.1.0',
      environment: 'development',
      api_prefix: '/api/v1',
      supported_languages: ['Python', 'JavaScript'],
      configured_ai_provider: 'Google Gemini',
      backend_status: 'running',
    });
    vi.mocked(apiClient.getAIStatus).mockResolvedValue({
      provider: 'Google Gemini',
      configured: false,
      configured_model: 'gemini-2.5-flash',
      connection_state: 'not_configured',
      message: 'Gemini API key is not configured.',
    });

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    expect(screen.getByText('FIXMATE AI Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Analysis & Autonomous Repair Metrics')).toBeInTheDocument();
    expect(screen.getByText('Projects Analyzed')).toBeInTheDocument();
    expect(screen.getByText('Bugs Detected')).toBeInTheDocument();
    expect(screen.getByText('Repairs Completed')).toBeInTheDocument();
  });

  it('2. Successful backend connection appears correctly', async () => {
    vi.mocked(apiClient.getHealth).mockResolvedValue({
      service: 'FIXMATE AI',
      status: 'healthy',
      version: '0.1.0',
      environment: 'development',
      timestamp: '2026-11-18T18:00:00Z',
    });
    vi.mocked(apiClient.getSystemInfo).mockResolvedValue({
      application_name: 'FIXMATE AI',
      version: '0.1.0',
      environment: 'development',
      api_prefix: '/api/v1',
      supported_languages: ['Python', 'JavaScript'],
      configured_ai_provider: 'Google Gemini',
      backend_status: 'running',
    });
    vi.mocked(apiClient.getAIStatus).mockResolvedValue({
      provider: 'Google Gemini',
      configured: true,
      configured_model: 'gemini-2.5-flash',
      connection_state: 'configured_untested',
      message: 'Configured and ready.',
    });

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText('Backend Available')[0]).toBeInTheDocument();
      expect(screen.getByText('LIVE TELEMETRY')).toBeInTheDocument();
    });
  });

  it('3. Backend disconnection appears correctly with failure state', async () => {
    vi.mocked(apiClient.getHealth).mockRejectedValue(new Error('Connection refused'));

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText('Backend Unavailable')[0]).toBeInTheDocument();
      expect(screen.getByText('OFFLINE')).toBeInTheDocument();
      expect(screen.getByText('Backend Communication Failed')).toBeInTheDocument();
    });
  });

  it('4. Loading state appears correctly initially', () => {
    // Hang promise to verify loading state
    vi.mocked(apiClient.getHealth).mockReturnValue(new Promise(() => {}));

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    expect(screen.getByText('Checking Connection...')).toBeInTheDocument();
    expect(screen.getByText('Fetching system diagnostics from backend...')).toBeInTheDocument();
  });

  it('5. Retry action works when disconnected', async () => {
    vi.mocked(apiClient.getHealth).mockRejectedValueOnce(new Error('Connection error'));

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getAllByText('Backend Unavailable')[0]).toBeInTheDocument();
    });

    const retryButton = screen.getByTestId('retry-backend-button');
    expect(retryButton).toBeInTheDocument();

    // Now resolve health
    vi.mocked(apiClient.getHealth).mockResolvedValueOnce({
      service: 'FIXMATE AI',
      status: 'healthy',
      version: '0.1.0',
      environment: 'development',
      timestamp: '2026-11-18T18:00:00Z',
    });

    fireEvent.click(retryButton);

    await waitFor(() => {
      expect(screen.getAllByText('Backend Available')[0]).toBeInTheDocument();
    });
  });

  it('6. Gemini status is displayed accurately', async () => {
    vi.mocked(apiClient.getHealth).mockResolvedValue({
      service: 'FIXMATE AI',
      status: 'healthy',
      version: '0.1.0',
      environment: 'development',
      timestamp: '2026-11-18T18:00:00Z',
    });
    vi.mocked(apiClient.getSystemInfo).mockResolvedValue({
      application_name: 'FIXMATE AI',
      version: '0.1.0',
      environment: 'development',
      api_prefix: '/api/v1',
      supported_languages: ['Python', 'JavaScript'],
      configured_ai_provider: 'Google Gemini',
      backend_status: 'running',
    });
    vi.mocked(apiClient.getAIStatus).mockResolvedValue({
      provider: 'Google Gemini',
      configured: true,
      configured_model: 'gemini-2.5-flash',
      connection_state: 'configured_untested',
      message: 'Gemini API key is configured with model gemini-2.5-flash.',
    });

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('CONFIGURED • UNTESTED')).toBeInTheDocument();
      expect(screen.getByText('Gemini API key is configured with model gemini-2.5-flash.')).toBeInTheDocument();
    });
  });

  it('7. Gemini test success and failure are displayed', async () => {
    vi.mocked(apiClient.getHealth).mockResolvedValue({
      service: 'FIXMATE AI',
      status: 'healthy',
      version: '0.1.0',
      environment: 'development',
      timestamp: '2026-11-18T18:00:00Z',
    });
    vi.mocked(apiClient.getSystemInfo).mockResolvedValue({
      application_name: 'FIXMATE AI',
      version: '0.1.0',
      environment: 'development',
      api_prefix: '/api/v1',
      supported_languages: ['Python', 'JavaScript'],
      configured_ai_provider: 'Google Gemini',
      backend_status: 'running',
    });
    vi.mocked(apiClient.getAIStatus).mockResolvedValue({
      provider: 'Google Gemini',
      configured: true,
      configured_model: 'gemini-2.5-flash',
      connection_state: 'configured_untested',
      message: 'Ready to test.',
    });

    // Mock successful test
    vi.mocked(apiClient.testAIConnection).mockResolvedValueOnce({
      success: true,
      provider: 'Google Gemini',
      model: 'gemini-2.5-flash',
      latency_ms: 312.4,
      message: 'Connection successful (312ms). Model response: PONG',
      timestamp: '2026-11-18T18:00:00Z',
      error: null,
    });

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('test-gemini-button')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('test-gemini-button'));

    await waitFor(() => {
      expect(screen.getByText('Gemini Verification Succeeded')).toBeInTheDocument();
      expect(screen.getByText('(312.4 ms)')).toBeInTheDocument();
    });

    // Now test failure response
    vi.mocked(apiClient.testAIConnection).mockResolvedValueOnce({
      success: false,
      provider: 'Google Gemini',
      model: 'gemini-2.5-flash',
      latency_ms: null,
      message: 'Invalid or unauthorized API key.',
      timestamp: '2026-11-18T18:00:05Z',
      error: 'AUTHENTICATION_ERROR',
    });

    fireEvent.click(screen.getByTestId('test-gemini-button'));

    await waitFor(() => {
      expect(screen.getByText('Gemini Verification Failed')).toBeInTheDocument();
      expect(screen.getByText('Invalid or unauthorized API key.')).toBeInTheDocument();
    });
  });

  it('8. Navigation works smoothly to other views', async () => {
    vi.mocked(apiClient.getHealth).mockResolvedValue({
      service: 'FIXMATE AI',
      status: 'healthy',
      version: '0.1.0',
      environment: 'development',
      timestamp: '2026-11-18T18:00:00Z',
    });
    vi.mocked(apiClient.getSystemInfo).mockResolvedValue({
      application_name: 'FIXMATE AI',
      version: '0.1.0',
      environment: 'development',
      api_prefix: '/api/v1',
      supported_languages: ['Python', 'JavaScript'],
      configured_ai_provider: 'Google Gemini',
      backend_status: 'running',
    });
    vi.mocked(apiClient.getAIStatus).mockResolvedValue({
      provider: 'Google Gemini',
      configured: false,
      configured_model: 'gemini-2.5-flash',
      connection_state: 'not_configured',
      message: 'Not configured.',
    });

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    // Click on New Analysis (select the first link, e.g. sidebar or banner)
    const newAnalysisLinks = screen.getAllByRole('link', { name: /new analysis/i });
    fireEvent.click(newAnalysisLinks[0]);

    await waitFor(() => {
      expect(screen.getByText('Autonomous Code Analysis Engine')).toBeInTheDocument();
      expect(screen.getByText('PHASE 2 ROADMAP')).toBeInTheDocument();
    });
  });

  it('9. No hardcoded successful backend state by default', () => {
    // When API has not returned, state is 'checking', not 'connected'
    vi.mocked(apiClient.getHealth).mockReturnValue(new Promise(() => {}));

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    expect(screen.queryByText('Backend Available')).not.toBeInTheDocument();
    expect(screen.getByText('Checking Connection...')).toBeInTheDocument();
  });
});
