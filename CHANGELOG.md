# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [2026-11-12] - Monorepo Separation: Dedicated Backend Directory

### Purpose
Organize the project into clean, decoupled `backend/` and `frontend/` directories. Move all backend-related modules, CLI runners, server code, test suites, datasets, and cache into `backend/`, and update path resolution and test harnesses to maintain full backward and forward compatibility.

### Files Moved & Restructured
- **Moved to `backend/`**:
  - `parts_agent/` ➔ `backend/parts_agent/`
  - `server.py` ➔ `backend/server.py`
  - `run_agent.py` ➔ `backend/run_agent.py`
  - `learnig.py` ➔ `backend/learnig.py`
  - `requirements.txt` ➔ `backend/requirements.txt`
  - `tests/` ➔ `backend/tests/`
  - `data/` ➔ `backend/data/`
  - `cache/` ➔ `backend/cache/`
  - `runs/` ➔ `backend/runs/`
  - `.env` ➔ `backend/.env` (and root `.env` maintained for fallback)
- **Created**:
  - `backend/__init__.py`: Package entrypoint for module imports (`import backend.server`).

### Code & Configuration Updates
- [`backend/server.py`](file:///home/habilelabs/Development/CAS/backend/server.py):
  - Updated `sys.path` injection so the server can be run from root (`uvicorn backend.server:app`) or from backend directory (`cd backend && uvicorn server:app`).
  - Updated `FRONTEND_DIST` resolution to look in `../frontend/dist` and local `frontend/dist`.
  - Added multi-path `.env` loading checking both backend and root.
- [`backend/run_agent.py`](file:///home/habilelabs/Development/CAS/backend/run_agent.py):
  - Injected `_backend_dir` into `sys.path` to allow execution from root (`python3 backend/run_agent.py`) and inside backend.
- [`backend/parts_agent/boodmo.py`](file:///home/habilelabs/Development/CAS/backend/parts_agent/boodmo.py):
  - Added multi-path fallback for `CATALOG_FILE` and `CACHE`.
- [`backend/parts_agent/graph.py`](file:///home/habilelabs/Development/CAS/backend/parts_agent/graph.py):
  - Added multi-path fallback for `RUNS` audit directory.
- [`backend/parts_agent/llm.py`](file:///home/habilelabs/Development/CAS/backend/parts_agent/llm.py):
  - Added multi-path `.env` loader.
- [`backend/tests/`](file:///home/habilelabs/Development/CAS/backend/tests/):
  - Added dynamic sys.path resolution to all test files and `__init__.py` allowing tests to run via `python3 -m unittest discover backend/tests` or `cd backend && python3 -m unittest discover tests`.
- [`cmd.txt`](file:///home/habilelabs/Development/CAS/cmd.txt), [`README.md`](file:///home/habilelabs/Development/CAS/README.md), [`docs/02_CODEBASE_GUIDE.md`](file:///home/habilelabs/Development/CAS/docs/02_CODEBASE_GUIDE.md), [`STUDY_GUIDE.md`](file:///home/habilelabs/Development/CAS/STUDY_GUIDE.md):
  - Updated execution commands and architectural file path diagrams.

---

## [2026-11-12] - Offline Boodmo Catalogue & Multi-Category Fallback Flow

### Purpose
Resolve catalog page timeouts and miscategorization (e.g. Radiator hanging on live category tree navigation and pointing to incorrect fuel pump category id `3620` instead of canonical `3731`). Establish a complete offline Boodmo taxonomy catalogue (`data/boodmo_catalog.json`) and implement multi-category fallback that attempts related categories when 0 parts are found, transparently notifying the user if a part is not listed for that vehicle.

### Files Changed
- [`data/boodmo_catalog.json`](file:///home/habilelabs/Development/CAS/data/boodmo_catalog.json):
  - Created canonical catalogue mapping 34 top-level sections, 450 verified subcategories with correct category IDs (`Radiator` -> `/catalog/3731-radiator/`), and synonym/fallback mappings.
- [`cache/boodmo_categories.json`](file:///home/habilelabs/Development/CAS/cache/boodmo_categories.json):
  - Corrected legacy leaf mapping for `Radiator` to `/catalog/3731-radiator/` and `Fuel Pump` to `/catalog/3620-fuel_pump/`.
- [`parts_agent/boodmo.py`](file:///home/habilelabs/Development/CAS/parts_agent/boodmo.py):
  - Updated category resolution to load directly from the offline catalogue with zero live website scraping, completely eliminating page timeouts during category lookup.
  - Implemented multi-category fallback in `collect()`: when 0 parts are found in the primary category for a vehicle variant, candidate alternate categories (e.g. `Radiator Support`, `Cooling Fan`) are automatically checked.
  - Formatted truthful notification when all candidates yield 0 results: `"This part is not listed in Boodmo's catalogue for {vehicle}. (Checked categories: ...)"`.
  - Hardened `_price()` to support integer and float values in addition to currency strings.
- [`parts_agent/graph.py`](file:///home/habilelabs/Development/CAS/parts_agent/graph.py):
  - Updated `_summarize_boodmo()` to reflect the resolved alternate category name in the customer response when a fallback category was utilized.
- [`tests/test_unit.py`](file:///home/habilelabs/Development/CAS/tests/test_unit.py):
  - Added unit tests verifying offline resolution of Radiator (`/catalog/3731-radiator/`), Water Pump, and Cooling Fan.
  - Added unit tests for multi-category fallback execution and honest "not listed" reporting.

### Checks Run
- **Python Backend Test Suite**:
  - `python3 -m unittest discover -s tests -p 'test_*.py'`
  - **Result**: 115 tests ran in 0.439s, all passed (OK).
- **Frontend Test Suite**:
  - `cd frontend && npm run test`
  - **Result**: 2 test files, 8 tests ran in 3.95s, all passed (OK).
- **Frontend Production Build**:
  - `cd frontend && npm run build`
  - **Result**: Production bundle built cleanly in 3.64s.

### Remaining Limitations
- AutoDukan continues to use universal/category fallback search as its catalog does not offer independent variant-level fitment verification.

---

## [2026-11-12] - Reliable Python Test Setup & Frontend Test Coverage

### Purpose
Resolve Python `FastAPI TestClient` hanging issues by isolating API endpoint tests from external network dependencies (live Gemini API calls and background browser sessions) and establish deterministic frontend unit/component test coverage with `vitest` and `@testing-library/react`.

### Files Changed
- [`tests/test_api_integration.py`](file:///home/habilelabs/Development/CAS/tests/test_api_integration.py):
  - Isolated `/api/chat/start` and `/api/reset` tests using mocks for `server.Conversation` and `server.open_session`.
  - Added deterministic test for `/api/chat/reply` mocking `CONVERSATIONS[thread_id]`.
  - Added deterministic test for `/api/transcribe` mocking `server.voice.transcribe` and `subprocess.run` (ffmpeg conversion).
  - Reduced test execution time from ~19s (hanging on live external API calls) down to 0.089s.
- [`frontend/package.json`](file:///home/habilelabs/Development/CAS/frontend/package.json):
  - Added `"test": "vitest run"` script.
  - Added `vitest` (^2.1.8), `@testing-library/react` (^16.3.3), and `jsdom` (^25.0.1) as devDependencies matching Vite 5.
- [`frontend/vite.config.js`](file:///home/habilelabs/Development/CAS/frontend/vite.config.js):
  - Configured Vitest runner with JSDOM environment and test setup file.
- [`frontend/src/setupTests.js`](file:///home/habilelabs/Development/CAS/frontend/src/setupTests.js):
  - Added JSDOM polyfill for `HTMLElement.prototype.scrollIntoView`.
- [`frontend/src/__tests__/ProductResults.test.jsx`](file:///home/habilelabs/Development/CAS/frontend/src/__tests__/ProductResults.test.jsx):
  - Added 4 unit tests verifying:
    1. Separate supplier catalog rendering for Boodmo and AutoDukan.
    2. Executive procurement savings calculation.
    3. Live search query text filtering.
    4. Relevance category tier filtering.
- [`frontend/src/__tests__/ConversationPanel.test.jsx`](file:///home/habilelabs/Development/CAS/frontend/src/__tests__/ConversationPanel.test.jsx):
  - Added 4 unit tests verifying:
    1. Empty state welcome suggestions.
    2. User and agent chat bubble rendering with profile chips.
    3. Form text input and submission via callback.
    4. Pending question option chips and reply triggers.

### Checks Run
- **Python Backend Test Suite**:
  - `python3 -m unittest discover -s tests -p 'test_*.py'`
  - **Result**: 112 tests ran in 0.437s, all passed (OK).
- **Frontend Test Suite**:
  - `cd frontend && npm run test`
  - **Result**: 2 test files, 8 tests ran in 3.78s, all passed (OK).
- **Frontend Production Build**:
  - `cd frontend && npm run build`
  - **Result**: Vite v5.4.21 built production bundle in 4.02s without errors.

### Remaining Limitations
- End-to-end browser automation tests (`playwright`) still require live browser binaries or recorded HAR mocks.
- API endpoints currently do not enforce CORS origin allowlists, authentication tokens, or rate limits (deferred to Item 2).
