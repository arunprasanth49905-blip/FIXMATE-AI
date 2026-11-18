export interface HealthResponse {
  service: string;
  status: string;
  version: string;
  environment: string;
  timestamp: string;
}

export interface SystemInfoResponse {
  application_name: string;
  version: string;
  environment: string;
  api_prefix: string;
  supported_languages: string[];
  configured_ai_provider: string;
  backend_status: string;
}

export type ConnectionState = 'not_configured' | 'configured_untested' | 'connected' | 'connection_failed';

export interface AIStatusResponse {
  provider: string;
  configured: boolean;
  configured_model: string;
  connection_state: ConnectionState;
  message: string;
}

export interface AITestResponse {
  success: boolean;
  provider: string;
  model: string;
  latency_ms: number | null;
  message: string;
  timestamp: string;
  error: string | null;
}

export interface ApiError {
  message: string;
  status?: number;
  details?: unknown;
}
