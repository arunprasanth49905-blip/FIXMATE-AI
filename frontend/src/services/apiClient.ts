import {
  HealthResponse,
  SystemInfoResponse,
  AIStatusResponse,
  AITestResponse,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';

export class ApiClientError extends Error {
  status?: number;
  details?: unknown;

  constructor(message: string, status?: number, details?: unknown) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.details = details;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}, timeoutMs = 8000): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const url = `${API_BASE_URL.replace(/\/$/, '')}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...options.headers,
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      let errorDetails: unknown = null;
      try {
        const errorJson = await response.json();
        if (errorJson && typeof errorJson === 'object') {
          errorMessage = (errorJson as { detail?: string }).detail || errorMessage;
          errorDetails = errorJson;
        }
      } catch {
        // Fall back to default status text if not JSON
      }
      throw new ApiClientError(errorMessage, response.status, errorDetails);
    }

    const data: T = await response.json();
    return data;
  } catch (err: unknown) {
    clearTimeout(timeoutId);

    if (err instanceof ApiClientError) {
      throw err;
    }

    if (err instanceof DOMException && err.name === 'AbortError') {
      throw new ApiClientError('Request timed out. Backend did not respond in time.', 408);
    }

    const message = err instanceof Error ? err.message : 'Network request failed';
    throw new ApiClientError(`Connection failed: ${message}`, 0);
  }
}

export const apiClient = {
  getHealth: (): Promise<HealthResponse> => {
    return request<HealthResponse>('/health');
  },

  getSystemInfo: (): Promise<SystemInfoResponse> => {
    return request<SystemInfoResponse>('/system/info');
  },

  getAIStatus: (): Promise<AIStatusResponse> => {
    return request<AIStatusResponse>('/system/ai-status');
  },

  testAIConnection: (): Promise<AITestResponse> => {
    return request<AITestResponse>('/system/ai-test', {
      method: 'POST',
    }, 25000); // 25s timeout for AI generation test
  },
};
