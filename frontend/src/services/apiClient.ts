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
  ParserStatusResponse,
  ProjectAnalysisResponse,
  FileAnalysis,
  SyntaxDiagnostic,
  ProjectParseRequest,
  DetectionRuleInfo,
  DetectionRunResponse,
  Finding,
  ProjectDetectionRequest,
  FileDetectionRequest,
  RootCauseAnalysis,
  AnalyzeFindingRequest,
  RootCauseHistoryResponse,
  GenerateRepairRequest,
  RepairProposal,
  RepairHistoryResponse,
  ApproveRepairResponse,
  RejectRepairResponse,
  ApplyRepairRequest,
  ApplyRepairResponse,
  RollbackRepairResponse,
  ProposalAuditHistoryResponse,
  VerificationReportResponse,
  VerificationHistoryResponse,
  VerificationListResponse,
  SandboxStatusResponse,
  ExecuteCodeRequest,
  ExecuteTestRequest,
  SandboxExecutionResponse,
  SandboxExecutionListResponse,
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

/**
 * Safely extracts a human-readable error string from any error object,
 * Pydantic/FastAPI validation detail array, Axios/Fetch response, or Error instance.
 * Guarantees that "[object Object]" is never returned.
 */
export function parseErrorMessage(errorData: unknown, defaultMessage = 'An unexpected error occurred'): string {
  if (!errorData) {
    return defaultMessage;
  }

  // 1. Direct string
  if (typeof errorData === 'string') {
    const trimmed = errorData.trim();
    if (trimmed && trimmed !== '[object Object]') {
      return trimmed.startsWith('Value error, ') ? trimmed.replace('Value error, ', '') : trimmed;
    }
    return defaultMessage;
  }

  // 2. ApiClientError or standard Error instance
  if (errorData instanceof Error) {
    if (errorData.message && errorData.message !== '[object Object]') {
      return errorData.message.startsWith('Value error, ')
        ? errorData.message.replace('Value error, ', '')
        : errorData.message;
    }
  }

  // 3. Object / JSON responses
  if (typeof errorData === 'object') {
    const obj = errorData as Record<string, unknown>;

    // Case 3a: FastAPI / Pydantic validation error array: detail: [{ msg: "...", loc: [...] }]
    if (Array.isArray(obj.detail)) {
      const messages = obj.detail
        .map((item) => {
          if (typeof item === 'string') return item;
          if (item && typeof item === 'object') {
            const dict = item as Record<string, unknown>;
            let msg = typeof dict.msg === 'string' ? dict.msg : '';
            if (msg.startsWith('Value error, ')) {
              msg = msg.replace('Value error, ', '');
            }
            if (Array.isArray(dict.loc) && dict.loc.length > 0) {
              const field = dict.loc[dict.loc.length - 1];
              if (field && typeof field === 'string' && field !== 'body' && !msg.toLowerCase().includes(field.toLowerCase())) {
                return `${field}: ${msg}`;
              }
            }
            return msg || '';
          }
          return '';
        })
        .filter((m): m is string => Boolean(m && m !== '[object Object]'));

      if (messages.length > 0) {
        return messages.join('. ');
      }
    }

    // Case 3b: detail string
    if (typeof obj.detail === 'string' && obj.detail.trim() && obj.detail !== '[object Object]') {
      const detailStr = obj.detail.trim();
      return detailStr.startsWith('Value error, ') ? detailStr.replace('Value error, ', '') : detailStr;
    }

    // Case 3c: message field
    if (typeof obj.message === 'string' && obj.message.trim() && obj.message !== '[object Object]') {
      return obj.message.trim();
    }

    // Case 3d: error string or nested error object
    if (typeof obj.error === 'string' && obj.error.trim() && obj.error !== '[object Object]') {
      return obj.error.trim();
    }
    if (obj.error && typeof obj.error === 'object') {
      const nested = obj.error as Record<string, unknown>;
      if (typeof nested.message === 'string' && nested.message.trim() && nested.message !== '[object Object]') {
        return nested.message.trim();
      }
    }

    // Case 3e: errors array
    if (Array.isArray(obj.errors) && obj.errors.length > 0) {
      const first = obj.errors[0];
      if (typeof first === 'string') return first;
      if (first && typeof first === 'object') {
        const firstObj = first as Record<string, unknown>;
        if (typeof firstObj.msg === 'string') return firstObj.msg;
        if (typeof firstObj.message === 'string') return firstObj.message;
      }
    }
  }

  return defaultMessage;
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
      let defaultMsg = `HTTP ${response.status}: ${response.statusText}`;
      if (response.status === 400) defaultMsg = 'Invalid file path or parameters.';
      else if (response.status === 403) defaultMsg = 'Path traversal is not allowed.';
      else if (response.status === 404) defaultMsg = 'Resource not found.';
      else if (response.status === 409) defaultMsg = 'File or folder already exists.';
      else if (response.status === 413) defaultMsg = 'File exceeds maximum allowed upload size.';
      else if (response.status === 422) defaultMsg = 'Invalid file path or validation failed.';

      let errorDetails: unknown = null;
      let errorMessage = defaultMsg;

      try {
        const errorJson = await response.json();
        errorDetails = errorJson;
        errorMessage = parseErrorMessage(errorJson, defaultMsg);
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

    const netMessage = err instanceof Error ? err.message : 'Network request failed';
    throw new ApiClientError(`Unable to connect to backend: ${netMessage}`, 0);
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

  // Phase 3 Code Parsing & Structural Intelligence APIs
  getParserStatus: (projectId: string): Promise<ParserStatusResponse> => {
    return request<ParserStatusResponse>(`/projects/${projectId}/analysis/parser-status`);
  },

  analyzeProject: (projectId: string, payload?: ProjectParseRequest): Promise<ProjectAnalysisResponse> => {
    return request<ProjectAnalysisResponse>(`/projects/${projectId}/analysis/parse`, {
      method: 'POST',
      body: payload ? JSON.stringify(payload) : undefined,
    }, 120000); // 2 minute timeout for full codebase parsing
  },

  getLatestAnalysis: (projectId: string): Promise<ProjectAnalysisResponse> => {
    return request<ProjectAnalysisResponse>(`/projects/${projectId}/analysis/latest`);
  },

  getAnalysisById: (projectId: string, analysisId: string): Promise<ProjectAnalysisResponse> => {
    return request<ProjectAnalysisResponse>(`/projects/${projectId}/analysis/parse/${analysisId}`);
  },

  getAnalyzedFiles: (projectId: string, analysisId: string, language?: string, status?: string): Promise<FileAnalysis[]> => {
    const params = new URLSearchParams();
    if (language) params.append('language', language);
    if (status) params.append('status', status);
    const query = params.toString() ? `?${params.toString()}` : '';
    return request<FileAnalysis[]>(`/projects/${projectId}/analysis/parse/${analysisId}/files${query}`);
  },

  getFileAnalysis: (projectId: string, analysisId: string, fileIdOrPath: string): Promise<FileAnalysis> => {
    return request<FileAnalysis>(`/projects/${projectId}/analysis/parse/${analysisId}/files/${encodeURIComponent(fileIdOrPath)}`);
  },

  getAnalysisDiagnostics: (projectId: string, analysisId: string): Promise<SyntaxDiagnostic[]> => {
    return request<SyntaxDiagnostic[]>(`/projects/${projectId}/analysis/parse/${analysisId}/diagnostics`);
  },

  // Phase 4 Deterministic Bug Detection APIs
  getDetectionRules: (projectId: string, severity?: string): Promise<DetectionRuleInfo[]> => {
    const query = severity ? `?severity=${severity}` : '';
    return request<DetectionRuleInfo[]>(`/projects/${projectId}/detection/rules${query}`);
  },

  runBugDetection: (projectId: string, payload?: ProjectDetectionRequest): Promise<DetectionRunResponse> => {
    return request<DetectionRunResponse>(`/projects/${projectId}/detection/run`, {
      method: 'POST',
      body: payload ? JSON.stringify(payload) : undefined,
    }, 120000);
  },

  getLatestDetection: (projectId: string): Promise<DetectionRunResponse> => {
    return request<DetectionRunResponse>(`/projects/${projectId}/detection/latest`);
  },

  getDetectionRun: (projectId: string, runId: string): Promise<DetectionRunResponse> => {
    return request<DetectionRunResponse>(`/projects/${projectId}/detection/runs/${runId}`);
  },

  getDetectionFindings: (projectId: string, runId: string, params?: Record<string, string>): Promise<Finding[]> => {
    const q = params ? `?${new URLSearchParams(params).toString()}` : '';
    return request<Finding[]>(`/projects/${projectId}/detection/runs/${runId}/findings${q}`);
  },

  runFileDetection: (projectId: string, payload: FileDetectionRequest): Promise<Finding[]> => {
    return request<Finding[]>(`/projects/${projectId}/detection/run-file`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // Phase 5 AI Root Cause Analysis APIs
  analyzeFinding: (projectId: string, payload: AnalyzeFindingRequest): Promise<RootCauseAnalysis> => {
    return request<RootCauseAnalysis>(`/projects/${projectId}/root-cause/analyze`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }, 60000);
  },

  getLatestRootCause: (projectId: string): Promise<RootCauseAnalysis> => {
    return request<RootCauseAnalysis>(`/projects/${projectId}/root-cause/latest`);
  },

  getRootCauseForFinding: (projectId: string, findingId: string): Promise<RootCauseAnalysis | null> => {
    return request<RootCauseAnalysis | null>(`/projects/${projectId}/root-cause/finding/${findingId}`);
  },

  getRootCauseById: (projectId: string, analysisId: string): Promise<RootCauseAnalysis> => {
    return request<RootCauseAnalysis>(`/projects/${projectId}/root-cause/${analysisId}`);
  },

  getRootCauseHistory: (projectId: string, limit?: number): Promise<RootCauseHistoryResponse> => {
    const q = limit ? `?limit=${limit}` : '';
    return request<RootCauseHistoryResponse>(`/projects/${projectId}/root-cause/history${q}`);
  },

  deleteRootCause: (projectId: string, analysisId: string): Promise<{ deleted: boolean; analysis_id: string }> => {
    return request<{ deleted: boolean; analysis_id: string }>(`/projects/${projectId}/root-cause/${analysisId}`, {
      method: 'DELETE',
    });
  },

  // Phase 6 Intelligent Code Repair APIs
  generateRepair: (projectId: string, payload: GenerateRepairRequest): Promise<RepairProposal> => {
    return request<RepairProposal>(`/projects/${projectId}/repair/generate`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }, 60000);
  },

  getRepairProposal: (projectId: string, proposalId: string): Promise<RepairProposal> => {
    return request<RepairProposal>(`/projects/${projectId}/repair/${proposalId}`);
  },

  getRepairForFinding: (projectId: string, findingId: string): Promise<RepairProposal | null> => {
    return request<RepairProposal | null>(`/projects/${projectId}/repair/finding/${findingId}`);
  },

  getRepairHistory: (projectId: string, findingId?: string, limit?: number): Promise<RepairHistoryResponse> => {
    const params = new URLSearchParams();
    if (findingId) params.append('finding_id', findingId);
    if (limit) params.append('limit', String(limit));
    const q = params.toString() ? `?${params.toString()}` : '';
    return request<RepairHistoryResponse>(`/projects/${projectId}/repair/history${q}`);
  },

  deleteRepairProposal: (projectId: string, proposalId: string): Promise<{ deleted: boolean; proposal_id: string }> => {
    return request<{ deleted: boolean; proposal_id: string }>(`/projects/${projectId}/repair/${proposalId}`, {
      method: 'DELETE',
    });
  },

  // Phase 7 Human Approval & Controlled Patch Application APIs
  approveRepair: (projectId: string, proposalId: string): Promise<ApproveRepairResponse> => {
    return request<ApproveRepairResponse>(`/projects/${projectId}/repair/${proposalId}/approve`, {
      method: 'POST',
    });
  },

  rejectRepair: (projectId: string, proposalId: string): Promise<RejectRepairResponse> => {
    return request<RejectRepairResponse>(`/projects/${projectId}/repair/${proposalId}/reject`, {
      method: 'POST',
    });
  },

  applyRepair: (projectId: string, proposalId: string, payload: ApplyRepairRequest): Promise<ApplyRepairResponse> => {
    return request<ApplyRepairResponse>(`/projects/${projectId}/repair/${proposalId}/apply`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  rollbackRepair: (projectId: string, proposalId: string): Promise<RollbackRepairResponse> => {
    return request<RollbackRepairResponse>(`/projects/${projectId}/repair/${proposalId}/rollback`, {
      method: 'POST',
    });
  },

  getRepairAuditLog: (projectId: string, proposalId: string): Promise<ProposalAuditHistoryResponse> => {
    return request<ProposalAuditHistoryResponse>(`/projects/${projectId}/repair/${proposalId}/audit-log`);
  },

  // Phase 8 Automated Verification & Repair Validation APIs
  verifyRepair: (projectId: string, proposalId: string): Promise<VerificationReportResponse> => {
    return request<VerificationReportResponse>(`/projects/${projectId}/repair/${proposalId}/verify`, {
      method: 'POST',
    });
  },

  getRepairVerificationHistory: (projectId: string, proposalId: string, limit?: number): Promise<VerificationHistoryResponse> => {
    const q = limit ? `?limit=${limit}` : '';
    return request<VerificationHistoryResponse>(`/projects/${projectId}/repair/${proposalId}/verification-history${q}`);
  },

  getVerificationById: (projectId: string, verificationId: string): Promise<VerificationReportResponse> => {
    return request<VerificationReportResponse>(`/projects/${projectId}/verification/${verificationId}`);
  },

  getVerificationHistoryList: (params?: {
    projectId?: string;
    status?: string;
    search?: string;
    page?: number;
    pageSize?: number;
  }): Promise<VerificationListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.projectId) searchParams.set('project_id', params.projectId);
    if (params?.status) searchParams.set('status', params.status);
    if (params?.search) searchParams.set('search', params.search);
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.pageSize) searchParams.set('page_size', params.pageSize.toString());
    const qs = searchParams.toString() ? `?${searchParams.toString()}` : '';
    return request<VerificationListResponse>(`/verification/history${qs}`);
  },

  // Phase 9 Secure Sandbox Execution & Runtime Validation APIs
  getSandboxStatus: (): Promise<SandboxStatusResponse> => {
    return request<SandboxStatusResponse>('/sandbox/status');
  },

  executeCode: (projectId: string, payload: ExecuteCodeRequest): Promise<SandboxExecutionResponse> => {
    return request<SandboxExecutionResponse>(`/projects/${projectId}/execution/run`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  executeTests: (projectId: string, payload: ExecuteTestRequest): Promise<SandboxExecutionResponse> => {
    return request<SandboxExecutionResponse>(`/projects/${projectId}/execution/tests`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getExecutionHistory: (projectId: string, limit?: number): Promise<SandboxExecutionListResponse> => {
    const q = limit ? `?limit=${limit}` : '';
    return request<SandboxExecutionListResponse>(`/projects/${projectId}/execution/history${q}`);
  },

  getExecutionById: (projectId: string, executionId: string): Promise<SandboxExecutionResponse> => {
    return request<SandboxExecutionResponse>(`/projects/${projectId}/execution/${executionId}`);
  },
};
