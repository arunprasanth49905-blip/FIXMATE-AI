import {
  HealthResponse,
  SystemInfoResponse,
  AIStatusResponse,
  AITestResponse,
  Project,
  ProjectCreatePayload,
  ProjectUpdatePayload,
  ProjectListResponse,
  FileMetadata,
  FileContentResponse,
  FileTreeItem,
  FileCreatePayload,
  FileUploadResponse,
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

async function request<T>(endpoint: string, options: RequestInit = {}, timeoutMs = 10000): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const url = `${API_BASE_URL.replace(/\/$/, '')}${endpoint}`;

  try {
    const isFormData = options.body instanceof FormData;
    const headers: Record<string, string> = {
      Accept: 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    };

    if (!isFormData && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (response.status === 204) {
      return {} as T;
    }

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
  // Phase 1 System APIs
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
    }, 25000);
  },

  // Phase 2 Project Management APIs
  getProjects: (search?: string): Promise<ProjectListResponse> => {
    const query = search ? `?search=${encodeURIComponent(search)}` : '';
    return request<ProjectListResponse>(`/projects${query}`);
  },

  createProject: (payload: ProjectCreatePayload): Promise<Project> => {
    return request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getProject: (projectId: string): Promise<Project> => {
    return request<Project>(`/projects/${projectId}`);
  },

  updateProject: (projectId: string, payload: ProjectUpdatePayload): Promise<Project> => {
    return request<Project>(`/projects/${projectId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  deleteProject: (projectId: string): Promise<void> => {
    return request<void>(`/projects/${projectId}`, {
      method: 'DELETE',
    });
  },

  // Phase 2 File Workspace APIs
  getProjectFiles: (projectId: string, tree = true): Promise<FileTreeItem[]> => {
    return request<FileTreeItem[]>(`/projects/${projectId}/files?tree=${tree}`);
  },

  createProjectFile: (projectId: string, payload: FileCreatePayload): Promise<FileMetadata> => {
    return request<FileMetadata>(`/projects/${projectId}/files`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getFileContent: (projectId: string, fileId: string): Promise<FileContentResponse> => {
    return request<FileContentResponse>(`/projects/${projectId}/files/${fileId}`);
  },

  saveFileContent: (projectId: string, fileId: string, content: string): Promise<FileMetadata> => {
    return request<FileMetadata>(`/projects/${projectId}/files/${fileId}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    });
  },

  renameFile: (projectId: string, fileId: string, newPath: string): Promise<FileMetadata> => {
    return request<FileMetadata>(`/projects/${projectId}/files/${fileId}`, {
      method: 'PATCH',
      body: JSON.stringify({ path: newPath }),
    });
  },

  deleteFile: (projectId: string, fileId: string): Promise<void> => {
    return request<void>(`/projects/${projectId}/files/${fileId}`, {
      method: 'DELETE',
    });
  },

  uploadFiles: (projectId: string, formData: FormData): Promise<FileUploadResponse> => {
    return request<FileUploadResponse>(`/projects/${projectId}/upload`, {
      method: 'POST',
      body: formData,
    }, 60000); // 60s timeout for large uploads
  },
};
