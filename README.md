# FIXMATE AI — Autonomous Bug Detection & Code Repair Platform

FIXMATE AI is an advanced AI-powered software bug detection and autonomous code repair platform designed for enterprise engineering teams. It analyzes codebases, detects architectural flaws, semantic bugs, and vulnerabilities, and synthesizes verifiable patches.

- **Phase 1:** Core foundational full-stack architecture, live system telemetry, secure Google Gemini API integration, and an enterprise light dashboard.
- **Phase 2:** Project Management & Code Workspace — SQLite database persistence, secure file workspace storage, path traversal protection, interactive Monaco Editor, file tree navigation, and multi-file tab system.

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
│   │   │   ├── config.py               # Pydantic Settings configuration & storage limits
│   │   │   └── logging.py              # Secret-redacting logger
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   └── session.py              # SQLite SQLAlchemy engine, Base, & SessionLocal
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── project.py              # Project and ProjectFile SQLAlchemy models
│   │   ├── api/v1/
│   │   │   ├── router.py               # API v1 router aggregation
│   │   │   └── endpoints/
│   │   │       ├── health.py           # GET /api/v1/health
│   │   │       ├── system.py           # GET /info, GET /ai-status, POST /ai-test
│   │   │       ├── projects.py         # CRUD /api/v1/projects
│   │   │       └── files.py            # File tree, create, edit, rename, delete, upload
│   │   ├── schemas/                    # Pydantic data schemas
│   │   │   ├── health.py
│   │   │   ├── system.py
│   │   │   ├── ai.py
│   │   │   ├── project.py
│   │   │   └── file.py
│   │   └── services/
│   │       ├── gemini_service.py       # Google GenAI SDK integration & error sanitization
│   │       ├── project_service.py      # Project creation, listing, updating, deletion
│   │       └── file_service.py         # Path traversal security, tree building, disk I/O
│   ├── data/                           # Local SQLite database & isolated workspaces (gitignored)
│   │   ├── fixmate.db
│   │   └── workspaces/{project_id}/...
│   ├── tests/                          # 23 Pytest unit and integration tests
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/                        # App root & route definitions
│   │   ├── components/
│   │   │   ├── common/                 # Buttons, Badges, StatusIndicators, Cards, Modal
│   │   │   ├── layout/                 # Sidebar, Navbar, Main Layout
│   │   │   ├── dashboard/              # SystemStatus, GeminiTest, Metrics, Activity
│   │   │   └── workspace/              # FileExplorer, EditorTabs, CodeEditor, FileIcon
│   │   ├── pages/                      # DashboardPage, ProjectsPage, WorkspacePage, NewAnalysisPage
│   │   ├── services/                   # apiClient.ts (Typed HTTP client)
│   │   ├── types/                      # TypeScript API interface definitions
│   │   └── styles/                     # Modern Light Theme stylesheet
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   └── .env.example
├── documentation/
│   ├── PHASE_1_REPORT.md
│   └── PHASE_2_REPORT.md               # Phase 2 master verification report
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
GEMINI_MODEL=gemini-2.5-flash

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

---

## 6. Automated Testing

### Backend Tests (Pytest - 23 Tests)
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

### Frontend Tests (Vitest - 14 Tests)
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

### Frontend Production Build
```cmd
cd /d "D:\FIXMATE AI\frontend"
npm run build
```

---

## 7. Security Architecture

1. **Path Traversal Protection:** Every incoming file path is strictly sanitized (`/` and `\\` normalized, leading slashes stripped, `..` disallowed, null bytes blocked). The resolved physical path is verified with `path.is_relative_to(project_workspace_dir)`.
2. **Server Filesystem Anonymization:** API endpoints never expose absolute server paths (e.g. `D:\FIXMATE AI\...`). Only relative paths (`src/main.py`) are returned to the client.
3. **Execution Prohibition:** Uploaded source files are strictly stored as static data on disk. No uploaded code is executed on the host system.
4. **Size and Extension Validation:** Configurable upload ceiling (default 10MB per file) and whitelist of allowed development file types.
5. **Backend-Only Secrets:** Gemini API keys are isolated exclusively to backend runtime environments with automatic regex redaction.
