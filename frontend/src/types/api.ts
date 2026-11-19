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
  total_projects?: number;
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

// ==========================================
// Phase 2: Project & File Workspace Types
// ==========================================

export interface Project {
  id: string;
  name: string;
  description: string | null;
  language: string;
  created_at: string;
  updated_at: string;
  file_count: number;
}

export interface ProjectCreatePayload {
  name: string;
  description?: string;
  language?: string;
}

export interface ProjectUpdatePayload {
  name?: string;
  description?: string;
  language?: string;
}

export interface ProjectListResponse {
  total: number;
  projects: Project[];
}

export interface FileMetadata {
  id: string;
  project_id: string;
  path: string;
  name: string;
  is_directory: boolean;
  size: number;
  extension: string;
  created_at: string;
  updated_at: string;
}

export interface FileContentResponse extends FileMetadata {
  content: string | null;
  is_binary: boolean;
}

export interface FileTreeItem {
  id: string;
  path: string;
  name: string;
  is_directory: boolean;
  size: number;
  extension: string;
  children?: FileTreeItem[] | null;
}

export interface FileCreatePayload {
  path: string;
  content?: string;
  is_directory?: boolean;
}

export interface FileUpdatePayload {
  content?: string;
  path?: string;
}

export interface FileUploadResponse {
  uploaded: FileMetadata[];
  errors: string[];
}
