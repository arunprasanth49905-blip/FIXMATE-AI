# FIXMATE AI — Autonomous Bug Detection & Code Repair Platform

FIXMATE AI is an advanced AI-powered software bug detection and autonomous code repair platform designed for enterprise engineering teams. It analyzes codebases, detects architectural flaws, semantic bugs, and vulnerabilities, and synthesizes verifiable patches.

Phase 1 establishes the production-grade foundational full-stack architecture, live system telemetry, secure Google Gemini API integration, and an enterprise light dashboard.

---

## 1. Technology Stack

### Frontend
- **Framework:** React 19 + TypeScript (Strict Mode)
- **Tooling:** Vite 6
- **Routing:** React Router v7
- **Icons:** Lucide React
- **Design System:** Custom Modern Light SaaS Developer Theme (Navy / White / Cyan / Blue)
- **Testing:** Vitest + React Testing Library + jsdom

### Backend
- **Framework:** FastAPI (Python 3.13)
- **ASGI Server:** Uvicorn
- **Configuration:** Pydantic Settings v2 + Python-dotenv
- **HTTP Client:** HTTPX
- **AI SDK:** Official Google GenAI Python SDK (`google-genai`)
- **Testing:** Pytest + Pytest-Asyncio + unittest.mock

---

## 2. Architecture Overview

```
FIXMATE AI/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI application entry & CORS middleware
│   │   ├── core/
│   │   │   ├── config.py               # Pydantic Settings configuration
│   │   │   └── logging.py              # Secret-redacting logger
│   │   ├── api/v1/
│   │   │   ├── router.py               # API v1 router aggregation
│   │   │   └── endpoints/
│   │   │       ├── health.py           # GET /api/v1/health
│   │   │       └── system.py           # GET /info, GET /ai-status, POST /ai-test
│   │   ├── schemas/                    # Pydantic data schemas
│   │   │   ├── health.py
│   │   │   ├── system.py
│   │   │   └── ai.py
│   │   └── services/
│   │       └── gemini_service.py       # Google GenAI SDK integration & error sanitization
│   ├── tests/                          # 8 Pytest unit and integration tests
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/                        # App root & route definitions
│   │   ├── components/                 # Reusable layout & dashboard components
│   │   │   ├── common/                 # Buttons, Badges, StatusIndicators, Cards
│   │   │   ├── layout/                 # Sidebar, Navbar, Main Layout
│   │   │   └── dashboard/              # SystemStatus, GeminiTest, Metrics, Activity
│   │   ├── pages/                      # DashboardPage, NewAnalysisPage, ComingSoonPage
│   │   ├── services/                   # apiClient.ts (Typed HTTP client)
│   │   ├── types/                      # TypeScript API interface definitions
│   │   └── styles/                     # Modern Light Theme stylesheet
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   └── .env.example
├── documentation/
│   └── PHASE_1_REPORT.md               # Comprehensive verification report
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
cd /d D:\FIXMATE-AI
```

### Step 2: Backend Setup
```cmd
cd /d D:\FIXMATE-AI\backend

:: Create Python virtual environment
python -m venv .venv

:: Activate virtual environment
.venv\Scripts\activate

:: Install dependencies
pip install -r requirements.txt

:: Configure environment
copy .env.example .env
```

Edit `backend/.env` to configure your environment:
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
```

### Step 3: Frontend Setup
In a new terminal:
```cmd
cd /d D:\FIXMATE-AI\frontend

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
cd /d D:\FIXMATE-AI\backend
.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

- **Interactive API Docs (Swagger):** [http://localhost:8001/docs](http://localhost:8001/docs)
- **Health Endpoint:** [http://localhost:8001/api/v1/health](http://localhost:8001/api/v1/health)
- **System Info Endpoint:** [http://localhost:8001/api/v1/system/info](http://localhost:8001/api/v1/system/info)

### Start the Frontend Dev Server (Terminal 2)
```cmd
cd /d D:\FIXMATE-AI\frontend
npm run dev
```

- **Application Dashboard:** [http://localhost:5173](http://localhost:5173)

---

## 5. API Documentation

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Returns service name, status (`healthy`), version, environment, and server ISO timestamp. |
| `GET` | `/api/v1/system/info` | Returns application metadata, API prefix, supported languages (`Python`, `JavaScript`), and backend state. |
| `GET` | `/api/v1/system/ai-status` | Returns AI provider name, configured status, active model, and connection state (`not_configured`, `configured_untested`, `connected`, `connection_failed`). |
| `POST` | `/api/v1/system/ai-test` | Triggers a live minimal connection test to Google Gemini API via official SDK, measuring roundtrip latency and returning safe sanitized diagnostics. |

---

## 6. Automated Testing

### Backend Tests (Pytest)
```cmd
cd /d D:\FIXMATE-AI\backend
.venv\Scripts\activate
pytest tests -v
```
Verifies:
1. Health endpoint response format and schema.
2. System info endpoint response and language support.
3. AI status when `GEMINI_API_KEY` is missing.
4. AI status when `GEMINI_API_KEY` is configured.
5. AI test response when credentials are missing.
6. AI test success using mocked provider.
7. AI test failure handling with safe error code categorization.
8. Secret protection & redaction verification.

### Frontend Tests (Vitest)
```cmd
cd /d D:\FIXMATE-AI\frontend
npm test
```
Verifies:
1. Dashboard rendering and component mounting.
2. Successful backend live connection indicator.
3. Backend disconnection detection and offline UI state.
4. Initial checking / loading indicator state.
5. Interactive retry action behavior.
6. Gemini configuration status badge and details.
7. Explicit Gemini connection test trigger and result rendering.
8. Navigation between views (Dashboard, New Analysis, Coming Soon modules).
9. Verifies that the UI never defaults to a hardcoded "Connected" state.

### Frontend Production Build
```cmd
cd /d D:\FIXMATE-AI\frontend
npm run build
```

---

## 7. Security Architecture

1. **Backend-Only Secrets:** The Gemini API key is never exposed to the client application or included in Vite bundles.
2. **Secret Redaction Filter:** Backend logging and error serialization sanitize API keys and credential strings before they reach output channels or HTTP responses.
3. **Strict CORS Policy:** Only authorized local frontend origins (`http://localhost:5173` and `http://127.0.0.1:5173`) are permitted. Wildcards with credentials are explicitly prohibited.
4. **No Arbitrary Code Execution:** Phase 1 prohibits host-level execution of untrusted user scripts.

---

## 8. Current Limitations & Roadmap

### Phase 1 Limitations
- AST parsing and bug detection engines are not yet active (introductory pipeline page provided).
- Metrics use honest empty states (`0 projects`, `0 bugs`) until real project analysis is connected.
- Code sandboxing and automated patch verification will be introduced in subsequent phases.

### Upcoming Phases
- **Phase 2:** Multi-file AST parsing, repository ingestion, and Gemini semantic flaw detection.
- **Phase 3:** Autonomous patch synthesis and isolated test execution.
- **Phase 4:** Platform analytics, reporting, and CI/CD integration.
