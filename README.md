# FIXMATE AI — Autonomous Bug Detection & Code Repair Platform

FIXMATE AI is an advanced AI-powered software bug detection and autonomous code repair platform designed for enterprise engineering teams. It analyzes codebases, detects architectural flaws, semantic bugs, and vulnerabilities, and synthesizes verifiable patches.

- **Phase 1:** Core foundational full-stack architecture, live system telemetry, secure Google Gemini API integration, and an enterprise light dashboard.
- **Phase 2:** Project Management & Code Workspace — SQLite database persistence, secure file workspace storage, path traversal protection, interactive Monaco Editor, file tree navigation, and multi-file tab system.
- **Phase 3:** Multi-Language Code Parsing & Structural Intelligence Engine — Real AST and syntax-tree parsing without execution for Python (`ast`), JavaScript (`tree-sitter-javascript`), and TypeScript/TSX (`tree-sitter-typescript`), deep symbol extraction, syntax diagnostics detection, project-level metrics, and Monaco Editor deep navigation.
- **Phase 4:** Deterministic Bug Detection Engine — Static, zero-execution rule engine with 20 deterministic rules across Python, JavaScript, and TypeScript, calibrated confidence scoring, code evidence extraction, actionable remediation, and Monaco Editor line/column deep navigation.
- **Phase 5:** AI Root Cause Analysis Engine — Deep semantic investigation powered by Google Gemini (`google-genai` SDK) analyzing deterministic findings without executing code. Features dual-severity comparison (authoritative static vs AI assessed), calibrated confidence scoring (0-100), root cause breakdown, execution/state impact, failure consequences, conceptual guidance (strictly no code patches), secret redaction, and SQLite analysis history.
- **Phase 6:** Intelligent Code Repair & Safe Patch Generation Engine — Safe patch synthesis powered by Google Gemini 3.5 Flash Lite (`gemini-3.5-flash-lite`). Produces in-memory unified diffs with line-level indentation preservation, SHA-256 source freshness fingerprinting, multi-layer deterministic validation (AST syntax parsing, patch reversibility, path confinement), and interactive review in Monaco without writing to disk files.

---

## 1. Technology Stack

### Frontend
- **Framework:** React 19 + TypeScript (Strict Mode)
- **Tooling:** Vite 6
- **Routing:** React Router v7
- **Editor:** Monaco Editor (`@monaco-editor/react`) with syntax highlighting, automatic layout, line numbers, and keyboard shortcuts (`Ctrl+S`)
- **Icons:** Lucide React
- **Design System:** Custom Modern Light SaaS Developer Theme (Navy / White / Cyan / Blue)
- **Testing:** Vitest + React Testing Library + jsdom

### Backend
- **Framework:** FastAPI (Python 3.13)
- **Database & ORM:** SQLite + SQLAlchemy 2.0
- **ASGI Server:** Uvicorn
- **Configuration:** Pydantic Settings v2 + Python-dotenv
- **File Uploads:** `python-multipart`
- **HTTP Client:** HTTPX
- **AI SDK:** Official Google GenAI Python SDK (`google-genai`)
- **Testing:** Pytest + Pytest-Asyncio + unittest.mock

---

## 2. Architecture Overview

```
FIXMATE AI/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI application entry, CORS, & DB lifespan
│   │   ├── core/
│   │   │   ├── config.py               # Pydantic Settings configuration, storage & parser limits
│   │   │   └── logging.py              # Secret-redacting logger
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   └── session.py              # SQLite SQLAlchemy engine, Base, & SessionLocal
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── project.py              # Project and ProjectFile SQLAlchemy models
│   │   │   ├── analysis.py             # ProjectAnalysis and FileAnalysisRecord models
│   │   │   ├── detection.py            # DetectionRun and DetectionFinding SQLAlchemy models
│   │   │   ├── root_cause.py           # RootCauseAnalysis SQLAlchemy model
│   │   │   └── repair.py               # Phase 6 RepairProposal SQLAlchemy model
│   │   ├── api/v1/
│   │   │   ├── router.py               # API v1 router aggregation
│   │   │   └── endpoints/
│   │   │       ├── health.py           # GET /api/v1/health
│   │   │       ├── system.py           # GET /info, GET /ai-status, POST /ai-test
│   │   │       ├── projects.py         # CRUD /api/v1/projects
│   │   │       ├── files.py            # File tree, create, edit, rename, delete, upload
│   │   │       ├── parsing.py          # AST parsing, project analysis, diagnostics APIs
│   │   │       ├── detection.py        # Bug detection runs, findings, rules catalog APIs
│   │   │       ├── root_cause.py       # AI Root Cause Analysis, history, and single finding RCA APIs
│   │   │       └── repair.py           # Phase 6 Safe Patch Generation, history, and proposal APIs
│   │   ├── schemas/                    # Pydantic data schemas
│   │   │   ├── health.py
│   │   │   ├── system.py
│   │   │   ├── ai.py
│   │   │   ├── project.py
│   │   │   ├── file.py
│   │   │   ├── parsing.py              # AST symbols, diagnostics, statistics, responses
│   │   │   ├── detection.py            # Finding, DetectionRunResponse, rules schemas
│   │   │   ├── root_cause.py           # RootCauseAnalysisResponse, history, confidence schemas
│   │   │   └── repair.py               # Phase 6 PatchValidationDetails, RepairProposal schemas
│   │   └── services/
│   │       ├── gemini_service.py       # Google GenAI SDK integration & error sanitization
│   │       ├── project_service.py      # Project creation, listing, updating, deletion
│   │       ├── file_service.py         # Path traversal security, tree building, disk I/O
│   │       ├── parsing/                # Phase 3 Multi-Language Parsing Engine
│   │       │   ├── base_parser.py      # Abstract BaseParser interface
│   │       │   ├── python_parser.py    # Native AST parser (classes, methods, functions, calls)
│   │       │   ├── javascript_parser.py# Tree-sitter JS parser (ESM/CJS, classes, arrows)
│   │       │   ├── typescript_parser.py# Tree-sitter TS/TSX parser (interfaces, types, enums)
│   │       │   ├── parser_registry.py  # Language parser registry and status reporter
│   │       │   ├── parser_limits.py    # Resource thresholds (1MB, 500 files, 25MB)
│   │       │   ├── syntax_diagnostics.py# Error node converter & diagnostics builder
│   │       │   └── project_analysis_service.py # Full workspace scanner & SQLite persistence
│   │       ├── detection/              # Phase 4 Deterministic Bug Detection Engine
│   │       │   ├── base_rule.py        # Abstract BaseRule interface
│   │       │   ├── rule_context.py     # RuleContext encapsulation (AST, source, analysis)
│   │       │   ├── rule_registry.py    # Central rule catalog and language index
│   │       │   ├── detection_engine.py # Workspace scanner, evaluator, and DB persistence
│   │       │   └── rules/
│   │       │       ├── python_rules.py     # 10 deterministic Python rules (PY-W001..W010)
│   │       │       └── javascript_rules.py # 10 deterministic JS/TS rules (JS-W001..W010)
│   │       ├── root_cause/             # Phase 5 AI Root Cause Analysis Engine
│   │       │   ├── root_cause_context.py   # Context extraction, padding, secret redaction, 8k cap
│   │       │   ├── root_cause_prompt_builder.py # Delimiter safety, anti-injection, schema prompt
│   │       │   ├── root_cause_engine.py    # Gemini client, structured JSON parser, calibrated confidence
│   │       │   └── root_cause_service.py   # Business logic, SQLite CRUD, dual severity comparison
│   │       └── repair/                 # Phase 6 Safe Patch Generation Engine
│   │           ├── repair_context.py       # Source SHA-256 fingerprinting, evidence slice, redaction
│   │           ├── repair_prompt_builder.py# 18 AI instructions, anti-injection, JSON schema
│   │           ├── repair_engine.py        # Gemini 3.5 Flash Lite synthesis & transient 503 retry
│   │           ├── patch_generator.py      # Unified diff construction & indentation preservation
│   │           ├── patch_validator.py      # Freshness, path security, reversibility, AST syntax
│   │           └── repair_service.py       # Orchestrator, SQLite persistence, staleness check
│   ├── data/                           # Local SQLite database & isolated workspaces (gitignored)
│   │   ├── fixmate.db
│   │   └── workspaces/{project_id}/...
│   ├── tests/                          # 100 Pytest unit and integration tests (100% pass)
│   │   ├── test_repair.py              # Phase 6 comprehensive patch engine test suite
│   ├── requirements.txt                # tree-sitter, tree-sitter-javascript, tree-sitter-typescript
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/                        # App root & route definitions
│   │   ├── components/
│   │   │   ├── common/                 # Buttons, Badges, StatusIndicators, Cards, Modal
│   │   │   ├── layout/                 # Sidebar, Navbar, Main Layout
│   │   │   ├── dashboard/              # SystemStatus, GeminiTest, Metrics, Activity
│   │   │   ├── workspace/              # FileExplorer, EditorTabs, CodeEditor, FileIcon
│   │   │   ├── analysis/               # AnalysisPanel, AnalysisSummaryCard, StructuralViewer
│   │   │   ├── detection/              # DetectionPanel, RulesModal
│   │   │   ├── root_cause/             # RootCauseAnalysisCard, RootCauseHistoryModal
│   │   │   └── repair/                 # Phase 6 RepairProposalCard, RepairHistoryModal
│   │   ├── test/                       # 48 Vitest frontend tests (100% pass)
│   │   │   └── RepairProposal.test.tsx # Phase 6 UI and workflow unit tests
│   │   │   ├── detection/              # DetectionPanel (Findings list, filters, Monaco jump)
│   │   │   └── root_cause/             # RootCauseAnalysisCard, RootCauseHistoryModal
│   │   ├── pages/                      # DashboardPage, ProjectsPage, WorkspacePage, NewAnalysisPage
│   │   ├── services/                   # apiClient.ts (Typed HTTP client for Phase 1-5)
│   │   ├── types/                      # TypeScript API interface definitions
│   │   └── styles/                     # Modern Light Theme stylesheet
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   └── .env.example
├── documentation/
│   ├── PHASE_1_REPORT.md
│   ├── PHASE_2_REPORT.md               # Phase 2 master verification report
│   ├── PHASE_3_REPORT.md               # Phase 3 multi-language parsing report
│   ├── PHASE_4_REPORT.md               # Phase 4 deterministic bug detection report
│   └── PHASE_5_REPORT.md               # Phase 5 AI root cause analysis report
└── README.md
```

---

## 3. Installation & Setup (Windows)

### Prerequisites
- Node.js (v20+ or v24+)
- Python 3.13+
- Git

### Step 1: Clone or Navigate to the Repository
```cmd
cd /d "D:\FIXMATE AI"
```

### Step 2: Backend Setup
```cmd
cd /d "D:\FIXMATE AI\backend"

:: Create Python virtual environment
python -m venv .venv

:: Activate virtual environment
.venv\Scripts\activate

:: Install dependencies
pip install -r requirements.txt

:: Configure environment
copy .env.example .env
```

`backend/.env` contents:
```ini
APP_NAME=FIXMATE AI
APP_ENV=development
APP_VERSION=0.1.0
API_V1_PREFIX=/api/v1
BACKEND_PORT=8001
FRONTEND_ORIGIN=http://localhost:5173

# Optional: Add Google Gemini API Key from Google AI Studio
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash-lite

# Database & Storage
DATABASE_URL=sqlite:///./data/fixmate.db
WORKSPACE_ROOT=./data/workspaces
```

### Step 3: Frontend Setup
In a new terminal:
```cmd
cd /d "D:\FIXMATE AI\frontend"

:: Install packages
npm install

:: Configure environment
copy .env.example .env
```

`frontend/.env` contents:
```ini
VITE_API_BASE_URL=http://localhost:8001/api/v1
```

---

## 4. Running the Application

### Start the Backend Server (Terminal 1)
```cmd
cd /d "D:\FIXMATE AI\backend"
.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

- **Interactive API Docs (Swagger):** [http://localhost:8001/docs](http://localhost:8001/docs)
- **Health Endpoint:** [http://localhost:8001/api/v1/health](http://localhost:8001/api/v1/health)
- **Projects Endpoint:** [http://localhost:8001/api/v1/projects](http://localhost:8001/api/v1/projects)

### Start the Frontend Dev Server (Terminal 2)
```cmd
cd /d "D:\FIXMATE AI\frontend"
npm run dev
```

- **Application Dashboard:** [http://localhost:5173](http://localhost:5173)
- **Projects Directory:** [http://localhost:5173/projects](http://localhost:5173/projects)

---

## 5. API Documentation

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Returns service name, status (`healthy`), version, environment, and server ISO timestamp. |
| `GET` | `/api/v1/system/info` | Returns application metadata, API prefix, supported languages, and real project counts. |
| `GET` | `/api/v1/system/ai-status` | Returns AI provider name, configured status, active model, and connection state. |
| `POST` | `/api/v1/system/ai-test` | Triggers a live minimal connection test to Google Gemini API via official SDK. |
| `GET` | `/api/v1/projects` | List all projects with optional `?search=` filter, ordered by last modified date. |
| `POST` | `/api/v1/projects` | Create a new project workspace with language specification. |
| `GET` | `/api/v1/projects/{project_id}` | Retrieve project details and file count. |
| `PATCH` | `/api/v1/projects/{project_id}` | Rename or update project description. |
| `DELETE` | `/api/v1/projects/{project_id}` | Delete project, metadata records, and physical workspace folder. |
| `GET` | `/api/v1/projects/{project_id}/files` | Retrieve files metadata or hierarchical tree (`?tree=true`). |
| `POST` | `/api/v1/projects/{project_id}/files` | Create a new file or directory inside the project workspace. |
| `GET` | `/api/v1/projects/{project_id}/files/{file_id}` | Read file content, size, and binary status. |
| `PUT` | `/api/v1/projects/{project_id}/files/{file_id}` | Save updated file text content. |
| `PATCH` | `/api/v1/projects/{project_id}/files/{file_id}` | Rename or move file to a new path. |
| `DELETE` | `/api/v1/projects/{project_id}/files/{file_id}` | Delete file or directory recursively. |
| `POST` | `/api/v1/projects/{project_id}/upload` | Upload one or multiple source code files preserving folder structure. |
| `GET` | `/api/v1/projects/{project_id}/analysis/parser-status` | Report parser engine status, grammars, capabilities, and thresholds. |
| `POST` | `/api/v1/projects/{project_id}/analysis/parse` | Run full or incremental multi-language AST parsing across project files. |
| `GET` | `/api/v1/projects/{project_id}/analysis/latest` | Retrieve latest persisted AST analysis summary and file metrics. |
| `GET` | `/api/v1/projects/{project_id}/analysis/parse/{analysis_id}` | Retrieve specific historical analysis summary and metadata. |
| `GET` | `/api/v1/projects/{project_id}/analysis/parse/{analysis_id}/files` | List all parsed files with language, lines, symbol counts, and status. |
| `GET` | `/api/v1/projects/{project_id}/analysis/parse/{analysis_id}/files/{file_id_or_path}` | Get detailed AST symbols, imports, and diagnostics for a specific file. |
| `GET` | `/api/v1/projects/{project_id}/analysis/parse/{analysis_id}/diagnostics` | Aggregate all syntax errors and diagnostic warnings across the project. |
| `GET` | `/api/v1/projects/{project_id}/detection/rules` | Retrieve catalog of all 20 deterministic detection rules with metadata. |
| `POST` | `/api/v1/projects/{project_id}/detection/run` | Execute deterministic static bug detection across workspace files. |
| `POST` | `/api/v1/projects/{project_id}/detection/run-file` | Run ad-hoc bug detection on a single file path or provided code snippet. |
| `GET` | `/api/v1/projects/{project_id}/detection/latest` | Retrieve latest bug detection run summary and findings. |
| `GET` | `/api/v1/projects/{project_id}/detection/runs/{run_id}` | Retrieve specific historical bug detection run. |
| `GET` | `/api/v1/projects/{project_id}/detection/runs/{run_id}/findings` | Query filtered findings (`severity`, `language`, `rule_id`, `search`). |

---

## 6. Automated Testing

### Backend Tests (Pytest - 74 Tests)
```cmd
cd /d "D:\FIXMATE AI\backend"
.venv\Scripts\activate
pytest tests -v
```

Verifies:
1. Health & system info endpoints.
2. AI status & connection test modes (missing key, valid key, mocked provider, failure categorization, secret redaction).
3. Project creation, retrieval, listing, searching, updating, and deletion.
4. File creation, directory tree building, content reading, saving, renaming, and deletion.
5. Path traversal prevention (verifies rejection of `../`, `..\\`, `/absolute`, drive letters, and null bytes).
6. File extension validation & oversized payload protection (`HTTP 413`).
7. Multipart file upload and database persistence.
8. Python native AST parser (sync/async functions, classes, decorators, docstrings, imports, calls, loops, syntax error resilience).
9. JavaScript tree-sitter parser (functions, arrow functions, classes, methods, CommonJS/ESM imports, syntax errors).
10. TypeScript & TSX tree-sitter parser (interfaces, type aliases, enums, generics, type-only imports, access modifiers, JSX components).
11. Multi-language project analysis engine, directory exclusion filtering (`node_modules`, `.venv`, `.git`), and SQLite persistence.
12. 10 Python deterministic bug rules (positive & negative test coverage for `PY-W001` through `PY-W010`).
13. 10 JavaScript/TypeScript deterministic bug rules (positive & negative test coverage for `JS-W001` through `JS-W010`).
14. Bug detection API execution, latest retrieval, severity/language filtering, and ad-hoc file detection.

### Frontend Tests (Vitest - 33 Tests across 5 Suites)
```cmd
cd /d "D:\FIXMATE AI\frontend"
npm test
```

Verifies:
1. Dashboard telemetry, backend connectivity detection, offline state, and retry action.
2. Projects directory listing, language badges, and search filtering.
3. Project creation modal workflow and submission.
4. Workspace file tree hierarchy rendering.
5. Opening files into multi-file tabs, tracking unsaved changes, and closing tabs.
6. Monaco Editor content synchronization and `Ctrl+S` save operations.
7. Code Intelligence side panel docking, tab switching (Overview, Files, Diagnostics).
8. AST structural symbol inspection, language distribution charts, and click-to-editor source line navigation.
9. Deterministic Bug Detection panel, severity metric counters, search filtering, code evidence preview, and remediation advice.
10. Direct "Jump to Code" navigation from detection findings into exact Monaco line and column coordinates.
11. Resilient HTTP and API error handling (avoiding `[object Object]` rendering).

### Frontend Production Build
```cmd
cd /d "D:\FIXMATE AI\frontend"
npm run build
```

---

## 7. Security Architecture

1. **Path Traversal Protection:** Every incoming file path is strictly sanitized (`/` and `\\` normalized, leading slashes stripped, `..` disallowed, null bytes blocked). The resolved physical path is verified with `path.is_relative_to(project_workspace_dir)`.
2. **Server Filesystem Anonymization:** API endpoints never expose absolute server paths (e.g. `D:\FIXMATE AI\...`). Only relative paths (`src/main.py`) are returned to the client.
3. **Execution Prohibition:** Uploaded source files are strictly stored as static data on disk and inspected strictly via static AST parsing. No user code is executed on the host system.
4. **AST Resource Protection & Limits:**
   - Maximum single file parse limit: **1 MB**
   - Maximum files per analysis run: **500 files**
   - Maximum total workspace source bytes parsed: **25 MB**
   - Strict directory exclusions: `node_modules`, `.venv`, `venv`, `.git`, `__pycache__`, `dist`, `build`, `.next`, etc.
5. **Backend-Only Secrets:** Gemini API keys are isolated exclusively to backend runtime environments with automatic regex redaction.
6. **No AI Code Leakage in Phase 3:** User code is analyzed locally via native/tree-sitter parsers and is not sent to external AI providers.
