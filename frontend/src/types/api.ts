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

// ==========================================
// Phase 3: Parsing & Structural Intelligence Types
// ==========================================

export interface ParameterInfo {
  name: string;
  type?: string | null;
  default_value?: string | null;
}

export interface Symbol {
  id: string;
  name: string;
  kind: 'function' | 'async_function' | 'method' | 'class' | 'interface' | 'enum' | 'type_alias' | 'variable' | 'constant';
  file_id?: string | null;
  file_path?: string | null;
  start_line: number;
  end_line: number;
  start_column: number;
  end_column: number;
  nesting_level: number;
  parent_symbol?: string | null;
  is_async: boolean;
  is_exported: boolean;
  parameters?: ParameterInfo[] | null;
  return_type?: string | null;
  visibility?: 'public' | 'private' | 'protected' | null;
  docstring?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface ImportSymbol {
  source_module: string;
  imported_names: string[];
  alias?: string | null;
  import_type: string;
  file_id?: string | null;
  file_path?: string | null;
  line: number;
  column: number;
  is_type_only: boolean;
}

export interface SyntaxDiagnostic {
  id: string;
  file_id?: string | null;
  file_path: string;
  severity: 'error' | 'warning' | 'info';
  category: string;
  message: string;
  line: number;
  column: number;
  end_line?: number | null;
  end_column?: number | null;
  parser_name: string;
  error_code?: string | null;
}

export interface FileStatistics {
  lines: number;
  functions: number;
  async_functions: number;
  classes: number;
  methods: number;
  imports: number;
  variables: number;
  constants: number;
  loops: number;
  conditions: number;
  calls: number;
}

export interface FileAnalysis {
  analysis_id?: string | null;
  project_id: string;
  file_id?: string | null;
  file_path: string;
  language: string;
  parser: string;
  status: 'success' | 'diagnostics' | 'failed' | 'skipped';
  source_hash: string;
  source_size: number;
  analysis_timestamp: string;
  statistics: FileStatistics;
  symbols: Symbol[];
  imports: ImportSymbol[];
  diagnostics: SyntaxDiagnostic[];
  structure: Record<string, unknown>;
  warnings?: string[];
}

export interface SkippedFile {
  file_path: string;
  reason: string;
  size_bytes: number;
}

export interface ProjectStatistics {
  total_files: number;
  supported_files: number;
  parsed_files: number;
  failed_files: number;
  skipped_files: number;
  python_files: number;
  javascript_files: number;
  typescript_files: number;
  total_lines: number;
  total_functions: number;
  total_async_functions: number;
  total_classes: number;
  total_methods: number;
  total_imports: number;
  total_variables: number;
  total_loops: number;
  total_conditions: number;
  total_calls: number;
  total_diagnostics: number;
  duration_ms: number;
}

export interface ProjectAnalysisResponse {
  analysis_id: string;
  project_id: string;
  status: 'completed' | 'completed_with_diagnostics' | 'failed' | 'cancelled';
  start_time: string;
  end_time: string;
  duration_ms: number;
  statistics: ProjectStatistics;
  language_distribution: Record<string, number>;
  skipped_files: SkippedFile[];
  warnings: string[];
  total_diagnostics_count: number;
  files: FileAnalysis[];
}

export interface ParserLimitConfig {
  max_file_size_bytes: number;
  max_files_per_analysis: number;
  max_total_source_bytes: number;
  excluded_directories: string[];
}

export interface ParserStatusResponse {
  available_parsers: Record<string, string>;
  supported_languages: string[];
  supported_extensions: Record<string, string[]>;
  parser_versions: Record<string, string>;
  limits: ParserLimitConfig;
  readiness: boolean;
  capabilities: Record<string, string[]>;
}

export interface ProjectParseRequest {
  file_ids?: string[];
  file_paths?: string[];
  exclude_dirs?: string[];
}

// ==========================================
// Phase 4: Deterministic Bug Detection Types
// ==========================================

export type FindingSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export type FindingCategory = 'correctness' | 'security' | 'performance' | 'maintainability' | 'suspicious';

export interface Finding {
  id: string;
  run_id?: string | null;
  project_id: string;
  rule_id: string;
  rule_name: string;
  language: string;
  severity: FindingSeverity;
  confidence: number;
  category: FindingCategory;
  file_path: string;
  start_line: number;
  start_column: number;
  end_line: number;
  end_column: number;
  message: string;
  explanation: string;
  evidence: string;
  remediation: string;
}

export interface DetectionRuleInfo {
  rule_id: string;
  name: string;
  language: string;
  severity: FindingSeverity;
  confidence: number;
  category: FindingCategory;
  description: string;
  remediation_guide: string;
  version: string;
}

export interface SeverityCounts {
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

export interface DetectionRunResponse {
  run_id: string;
  project_id: string;
  analysis_id?: string | null;
  status: 'completed' | 'completed_with_findings' | 'failed';
  engine_version: string;
  created_at: string;
  duration_ms: number;
  files_scanned: number;
  total_findings: number;
  severity_counts: SeverityCounts;
  findings_by_category: Record<string, number>;
  warnings: string[];
  findings: Finding[];
}

export interface ProjectDetectionRequest {
  file_ids?: string[];
  file_paths?: string[];
  rule_ids?: string[];
  severities?: FindingSeverity[];
  reuse_analysis?: boolean;
}

export interface FileDetectionRequest {
  file_path: string;
  content?: string;
  language?: string;
}

// ==========================================
// Phase 5: AI Root Cause Analysis Types
// ==========================================

export interface BugLocation {
  file: string;
  line: number;
  rule_id: string;
  language: string;
}

export interface SeverityAssessment {
  detected_severity: FindingSeverity | string;
  ai_assessed_severity: FindingSeverity | string;
  severity_reasoning: string;
  severity_changed: boolean;
}

export interface ConfidenceAssessment {
  confidence_score: number;
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW' | string;
  confidence_reason: string;
  limitations: string[];
}

export interface RootCauseAnalysis {
  id: string;
  project_id: string;
  finding_id: string;
  detection_run_id?: string | null;
  rule_id: string;
  rule_name: string;
  language: string;
  file_path: string;
  start_line: number;
  end_line: number;
  model: string;
  created_at: string;
  duration_ms: number;
  status: 'success' | 'failed' | string;

  // Upgraded Concise & Correction Fields
  bug_location?: BugLocation;
  original_code?: string;
  evidence?: string;
  simple_explanation?: string;
  corrected_code?: string;
  correction_explanation?: string;
  assumptions?: string[];
  fix_status?: 'suggested_not_applied' | 'needs_clarification' | string;

  // Backward-compatible fields
  summary: string;
  bug_explanation: string;
  root_cause: string;
  technical_reasoning: string;
  trigger_conditions: string[];
  execution_impact: string;
  potential_consequences: string[];

  severity_assessment: SeverityAssessment;
  recommended_approach: string;
  prevention: string;
  missing_context: string[];

  confidence_assessment: ConfidenceAssessment;
  error_message?: string | null;
}

export interface AnalyzeFindingRequest {
  finding_id: string;
  include_surrounding_context?: boolean;
  custom_user_notes?: string;
}

export interface RootCauseHistoryItem {
  id: string;
  project_id: string;
  finding_id: string;
  rule_id: string;
  rule_name: string;
  file_path: string;
  start_line: number;
  summary: string;
  original_code?: string;
  corrected_code?: string;
  fix_status?: string;
  detected_severity: string;
  ai_assessed_severity: string;
  confidence_score: number;
  confidence_level: string;
  created_at: string;
  duration_ms: number;
  status: string;
}

export interface RootCauseHistoryResponse {
  project_id: string;
  total: number;
  analyses: RootCauseHistoryItem[];
}

// ==========================================
// Phase 6: Intelligent Code Repair Types
// ==========================================

export interface ValidationCheck {
  name: string;
  status: 'passed' | 'failed' | 'warning';
  message: string;
  details?: string;
}

export interface PatchValidationDetails {
  checks: ValidationCheck[];
  overall_status: 'passed' | 'failed' | 'warning';
  is_syntactically_valid: boolean;
  is_reversible: boolean;
  is_scope_valid: boolean;
  validation_errors: string[];
}

export interface GenerateRepairRequest {
  finding_id: string;
  custom_instructions?: string;
}

export interface RepairProposal {
  id: string;
  project_id: string;
  finding_id: string;
  root_cause_analysis_id?: string | null;

  rule_id: string;
  rule_name: string;
  language: string;
  file_path: string;
  start_line: number;
  end_line: number;

  source_fingerprint: string;
  is_stale: boolean;

  repair_status: 'generated' | 'needs_clarification' | 'rejected_by_validation' | 'stale_source' | 'generation_failed' | string;
  repair_summary: string;
  repair_explanation: string;
  original_code: string;
  proposed_code: string;

  diff: string;
  additions: number;
  deletions: number;

  assumptions: string[];
  confidence_score: number;

  validation_status: 'passed' | 'failed' | 'warning' | string;
  validation_details: PatchValidationDetails;

  model: string;
  duration_ms: number;
  created_at: string;
  error_message?: string | null;
}

export interface RepairHistoryResponse {
  project_id: string;
  total: number;
  proposals: RepairProposal[];
}

