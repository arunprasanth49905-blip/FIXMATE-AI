# FIXMATE AI — Phase 5: AI Root Cause Analysis Engine Report

## 1. Executive Summary

Phase 5 of **FIXMATE AI** has been successfully implemented and verified. This phase introduces an **AI Root Cause Analysis (RCA) Engine** that bridges deterministic bug detection findings (Phase 4) with semantic understanding powered by Google Gemini via the official `google-genai` Python SDK.

### Core Workflow Integration
```
DETECT (Phase 4)  ──▶  EXPLAIN / RCA (Phase 5)  ──▶  REPAIR (Phase 6)
Deterministic          Semantic Investigation        Autonomous Patching
Static Rules           Architecture & Cause Only     (Upcoming)
```

In accordance with strict system boundaries:
- **Analysis-Only Enforcement**: The engine produces comprehensive conceptual, architectural, and systemic explanations. It **strictly avoids generating automated code patches, unified diffs, or overwriting files**. Code modification is reserved exclusively for Phase 6.
- **Static Safety Guarantees**: User source code is never executed. Delimiter tagging (`<<<UNTRUSTED_SOURCE_SNIPPET>>>`) and system instruction safeguards neutralize prompt injection attempts in code comments or string literals.
- **Secret Redaction**: Context extraction cleans Gemini keys, GitHub tokens, Bearer headers, AWS keys, and password patterns before sending payloads to Gemini.
- **Dual Severity Architecture**: Static detection severity remains authoritative; AI-assessed severity is surfaced alongside it as an expert second opinion with explicit rationale.

---

## 2. Architecture & Components

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Frontend (React 19)                            │
│  DetectionPanel ──▶ RootCauseAnalysisCard ──▶ RootCauseHistoryModal    │
└────────────────────────────────────▲───────────────────────────────────┘
                                     │ HTTP REST
┌────────────────────────────────────▼───────────────────────────────────┐
│                     FastAPI Backend (Python 3.13)                      │
│                                                                        │
│  /projects/{id}/root-cause/analyze                                     │
│  /projects/{id}/root-cause/latest                                      │
│  /projects/{id}/root-cause/history                                     │
│  /projects/{id}/root-cause/{analysis_id}                               │
│  /projects/{id}/root-cause/finding/{finding_id}                        │
│                                                                        │
│  ┌───────────────────────┐         ┌───────────────────────────────┐   │
│  │   RootCauseService    │ ──────▶ │ SQLite (root_cause_analyses)  │   │
│  └───────────┬───────────┘         └───────────────────────────────┘   │
│              │                                                         │
│              ├───────────────────┐                                     │
│              ▼                   ▼                                     │
│  ┌───────────────────────┐ ┌───────────────────────────────────────┐   │
│  │  ContextBuilder       │ │       RootCauseEngine                 │   │
│  │  - Context Slicing    │ │       - System Prompt Enforcer        │   │
│  │  - Line Numbering     │ │       - Schema-Constrained JSON       │   │
│  │  - Secret Redaction   │ │       - Calibrated Confidence         │   │
│  │  - 8,000 Char Capping │ │       - Transient Retry & Sanitize    │   │
│  └───────────────────────┘ └───────────────────┬───────────────────┘   │
└────────────────────────────────────────────────┼───────────────────────┘
                                                 │ HTTPS
                                     ┌───────────▼───────────┐
                                     │ Google Gemini API     │
                                     │ (google-genai SDK)    │
                                     └───────────────────────┘
```

---

## 3. Database Schema

Stored in `backend/data/fixmate.db` under table `root_cause_analyses`:

| Column | Type | Description |
|---|---|---|
| `id` | VARCHAR(36) PK | UUID primary key |
| `project_id` | VARCHAR(36) FK | Foreign key to `projects.id` (CASCADE) |
| `finding_id` | VARCHAR(36) FK | Foreign key to `detection_findings.id` (CASCADE) |
| `detection_run_id` | VARCHAR(36) FK | Foreign key to `detection_runs.id` (SET NULL) |
| `rule_id` | VARCHAR(32) | Deterministic rule identifier (e.g. `PY-E001`) |
| `rule_name` | VARCHAR(128) | Human-readable rule title |
| `language` | VARCHAR(64) | Programming language of analyzed file |
| `file_path` | VARCHAR(512) | Relative workspace file path |
| `start_line` / `end_line`| INTEGER | Code line coordinates |
| `model` | VARCHAR(64) | Active Gemini model (e.g. `gemini-3.5-flash-lite`) |
| `created_at` | DATETIME | UTC creation timestamp |
| `duration_ms` | FLOAT | Round-trip analysis latency in milliseconds |
| `status` | VARCHAR(32) | Status (`success`, `failed`) |
| `summary` | TEXT | Concise one-line executive summary |
| `bug_explanation` | TEXT | Narrative explanation of what the bug is |
| `root_cause` | TEXT | Deep underlying technical root cause |
| `technical_reasoning` | TEXT | Language-level mechanics & scoping rules |
| `trigger_conditions_json` | TEXT | JSON list of execution trigger conditions |
| `execution_impact` | TEXT | Runtime impact on state, stack, and memory |
| `potential_consequences_json` | TEXT | JSON list of concrete failure consequences |
| `detected_severity` | VARCHAR(32) | Phase 4 authoritative severity |
| `ai_assessed_severity` | VARCHAR(32) | AI suggested severity rating |
| `severity_reasoning` | TEXT | AI justification for severity agreement or divergence |
| `severity_changed` | BOOLEAN | Flag indicating whether AI diverged |
| `recommended_approach` | TEXT | Conceptual architecture guidance (no code patches) |
| `prevention` | TEXT | Best practices, typing, and testing strategies |
| `missing_context_json` | TEXT | JSON list of external files or inputs needed |
| `confidence_score` | FLOAT | Calibrated score from 0 to 100 |
| `confidence_level` | VARCHAR(16) | `HIGH`, `MEDIUM`, or `LOW` |
| `confidence_reason` | TEXT | Justification for confidence score |
| `limitations_json` | TEXT | Static analysis limitations |
| `raw_response` | TEXT | Full LLM response payload |
| `error_message` | TEXT | Error detail if failed |

---

## 4. API Specification

All endpoints are registered under `/api/v1/projects/{project_id}/root-cause`:

1. `POST /api/v1/projects/{project_id}/root-cause/analyze` (Status: 201)
   - Accepts: `{"finding_id": "...", "include_surrounding_context": true, "custom_user_notes": "..."}`
   - Performs context extraction, prompt construction, Gemini inference, and persistence.
   - Returns: `RootCauseAnalysisResponse`
2. `GET /api/v1/projects/{project_id}/root-cause/latest` (Status: 200)
   - Returns the most recent analysis for the project.
3. `GET /api/v1/projects/{project_id}/root-cause/history?limit=50` (Status: 200)
   - Returns list of past analyses with metadata summaries.
4. `GET /api/v1/projects/{project_id}/root-cause/{analysis_id}` (Status: 200)
   - Returns specific analysis by unique UUID.
5. `GET /api/v1/projects/{project_id}/root-cause/finding/{finding_id}` (Status: 200)
   - Returns the latest analysis for a specific finding, or `null`.
6. `DELETE /api/v1/projects/{project_id}/root-cause/{analysis_id}` (Status: 200)
   - Deletes an analysis record.

---

## 5. Security & Verification Results

### Backend Automated Test Suite
- Total test files: 15
- Total tests: **81 passed in 5.01s** (0 failures, 0 errors, 0 warnings)
- Test coverage includes:
  - Line coordinate extraction with 15-line padding and character cap
  - Secret redaction patterns (Gemini key, GitHub token, Bearer auth, AWS key, passwords)
  - Anti-prompt injection delimiter safety
  - Schema normalization and calibrated confidence scoring
  - Full CRUD lifecycle across all 6 API endpoints
  - 404 validation for nonexistent projects, findings, and analyses

### Frontend Automated Test Suite
- Total test files: 6
- Total tests: **37 passed in 19.82s** (0 failures, 0 errors)
- Production build: `npm.cmd run build --prefix frontend` succeeds cleanly generating `dist/index.html` and bundled assets.

### Live End-to-End Gemini Verification
Executed `backend/scratch/verify_live_root_cause.py` against live Gemini endpoint:
- **Model**: `gemini-3.5-flash-lite`
- **Rule**: `PY-E001` (Undefined variable referenced before assignment)
- **Result**:
  - Successfully classified bug, root cause, trigger conditions, runtime impact, and consequences.
  - Recommended approach provided clear architectural guidance without emitting code patches.
  - Confidence calibrated at `HIGH (95.0%)`.
  - Severity aligned at `critical` with explicit justification.
  - Zero raw secrets or keys exposed.

---

## 7. Phase 5 Upgrade & Regression Repair: Gemini 3.5 Flash Lite Restoration

### 7.1 Objective & Regression Audit
Following the initial Phase 5 release, the RCA experience was upgraded from dense technical reports to a concise, beginner-friendly format with exact line identification, original code display, plain English explanations, root cause determination, and suggested code corrections (non-applied).

During this upgrade:
1. **Model Inconsistency Identified**: Isolated references in UI fallbacks and tests defaulted to `gemini-2.5-flash`, while the system was standardizing on `gemini-3.5-flash-lite`.
2. **Transient Google API 503 Spikes**: Google's `gemini-3.5-flash-lite` experienced intermittent high-demand 503 spikes. The health check and connection test lacked exponential backoff retry for transient 503/429 errors, leading to false-negative test failures.
3. **Loopback Socket Access During TestClient**: In Windows sandboxed test execution, `starlette.testclient`'s internal `anyio` portal required local socket pair permissions.

### 7.2 Restoration Actions
- **Centralized Model Configuration**: Set `GEMINI_MODEL=gemini-3.5-flash-lite` centrally across `.env`, `backend/app/core/config.py`, `backend/app/services/root_cause/root_cause_engine.py`, `backend/app/services/gemini_service.py`, and frontend UI fallback cards (`GeminiTestCard.tsx`, `SystemStatusCard.tsx`).
- **Zero Legacy Model References**: Verified 0 occurrences of `gemini-2.5-flash`, `gemini-2.5-flash-lite`, or `gemini-3.8-flash` in the codebase.
- **Robust Transient Error Handling & Retries**: Added automated retry with exponential backoff for transient 503 (high demand) and 429 (rate limit) responses in both `GeminiService.test_connection()` and `RootCauseEngine.analyze()`.
- **Exact Line & Code Suggestion Safety**: Retained strictly non-destructive behavior (`fix_status: "suggested_not_applied"`). Original source files remain untouched.
- **Monaco Deep Link**: Added `View Error in Editor` action button that navigates directly to the exact file and error line in Monaco Editor.

### 7.3 Final Verification Results
1. **Gemini Model Check**: Runtime model confirmed as `gemini-3.5-flash-lite`.
2. **Real Gemini Connection Test**: Real Google Gemini API ping verified (`PONG`, 200 OK).
3. **Focused RCA Tests**: 8/8 tests passed in `backend/tests/test_root_cause.py`.
4. **Full Backend Tests**: 82/82 tests passed in `backend/tests/`.
5. **Frontend Vitest Tests**: 38/38 tests passed across 6 suites.
6. **TypeScript & Production Build**: `npm run build --prefix frontend` built successfully in 6.70s (`dist/index.html` generated).
7. **Live PY-W007 Division-by-Zero Test**:
   - Location: `main.py`, Line 2, `PY-W007`
   - Original Code: `return price * discount / 0`
   - Simple Explanation: "The code attempts to divide a number by zero, which is mathematically invalid and crashes the program with a ZeroDivisionError."
   - Suggested Correction: `return price * discount / 100` (Assumed discount is a percentage)
   - Source file on disk verified completely unchanged.
