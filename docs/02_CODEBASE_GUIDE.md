# AutoParts Sourcing Agent — Complete Codebase Guide

This document provides a comprehensive tour of the repository, detailing the purpose of every directory, file, and data contract.

---

## 1. Directory Tree & Architecture Overview

```
CAS / Convo_AI_Sourcing_Agent
├── data/
│   └── boodmo_catalog.json         # Complete offline Boodmo taxonomy (450 categories + fallbacks)
├── cache/
│   └── boodmo_categories.json      # Pre-indexed category taxonomy for Boodmo (legacy cache)
├── docs/                           # Official technical & architectural documentation
├── frontend/                       # React 18 + Vite + Tailwind CSS Single-Page Application
│   ├── src/
│   │   ├── __tests__/              # Automated Vitest component tests
│   │   │   ├── ConversationPanel.test.jsx
│   │   │   └── ProductResults.test.jsx
│   │   ├── components/
│   │   │   ├── Header.jsx          # Top brand bar, status dot, headless toggle
│   │   │   ├── ConversationPanel.jsx # Chat feed, voice input, quick test chips, options
│   │   │   ├── SupplierMonitor.jsx # Live status cards for Boodmo & AutoDukan
│   │   │   ├── ActivityLog.jsx     # Execution stats & collapsible technical logs
│   │   │   ├── ProductResults.jsx  # Dedicated supplier tables, executive recommendation
│   │   │   └── NotificationToast.jsx # Completion & error toast banners
│   │   ├── services/
│   │   │   └── api.js              # REST endpoints & SSE EventSource client
│   │   ├── App.jsx                 # Master state management & real-time event router
│   │   ├── setupTests.js           # JSDOM environment polyfills
│   │   └── index.css               # Tailwind CSS & custom scrollbar styles
│   └── dist/                       # Compiled production build served by FastAPI
├── backend/                        # Complete Backend (Agent, Server, Tests, Data)
│   ├── parts_agent/                # Core Python Agent Backend
│   │   ├── __init__.py
│   │   ├── models.py               # Data contracts: VehicleProfile, Listing, NeedInput
│   │   ├── llm.py                  # Multi-tier Gemini inference, assembly guards, STT
│   │   ├── graph.py                # LangGraph conversational DAG state machine
│   │   ├── boodmo.py               # Boodmo Playwright scraper & category navigator
│   │   ├── auto_dukan.py           # AutoDukan Playwright scraper & selector resolver
│   │   ├── relevance.py            # Relevance classification and ranking engine
│   │   ├── terminal_recorder.py    # Terminal video recorder and compositor
│   │   ├── variants.py             # Variant disambiguation engine
│   │   └── voice.py                # Audio processing and format conversions
│   ├── server.py                   # FastAPI application serving REST, SSE, and frontend
│   ├── run_agent.py                # CLI testing harness for interactive terminal runs
│   ├── requirements.txt            # Python dependencies
│   ├── data/                       # Verified catalogs (boodmo_catalog.json)
│   ├── cache/                      # Offline category caches
│   ├── runs/                       # Audit logs of historical search sessions in JSON format
│   └── tests/                      # Automated unit, integration, and scenario tests
│       ├── test_50_cases.py        # 50 comprehensive test cases
│       ├── test_api_integration.py # Deterministic FastAPI TestClient endpoint integration tests
│       ├── test_unit.py            # Core unit tests (models, adapters, regexes, offline taxonomy)
│       ├── test_negative.py        # Negative & edge-case tests
│       ├── test_relevance.py       # Product relevance & classification tests
│       ├── test_dashboard_scenarios.py # Multi-supplier workflow tests
│       └── test_swift_clutch_live.py # Live clutch search verification
├── docs/                           # Architecture guides and onboarding documents
├── CHANGELOG.md                    # Keep a Changelog compliant project history
├── STUDY_GUIDE.md                  # Comprehensive architectural deep dive
└── README.md                       # Project overview and run guide
```

---

## 2. Core Python Modules (`backend/parts_agent/`)

### 1. Data Contracts: [`backend/parts_agent/models.py`](file:///home/habilelabs/Development/CAS/backend/parts_agent/models.py)
Defines type-safe dataclasses used across the graph, adapters, and frontend:
- **`VehicleProfile`**: Stores vehicle attributes (`maker`, `model`, `year`, `variant`), candidate filters, and unverified speech hints.
- **`NeedInput`**: Represents an active clarifying question posed to the mechanic. Contains `field`, `question`, and `options` (clickable chips or dropdowns).
- **`Listing`**: Represents a single spare part scraped from a supplier. Contains `title`, `brand`, `part_number`, `price`, `mrp`, `url`, `origin`, `fitment`, `available`, and `relevance` (`EXACT_MATCH`, `COMPONENT`, `ACCESSORY`, `IRRELEVANT`).
- **`SearchOutcome`**: The result of a supplier extraction run containing vendor name, status (`ok`, `no_results`, `failed`), listings list, and message.

### 2. LLM & Guardrails: [`backend/parts_agent/llm.py`](file:///home/habilelabs/Development/CAS/backend/parts_agent/llm.py)
Handles all generative AI operations and strict safety guards:
- **`check_major_assembly(part_text)`**: Intercepts requests for complete crate assemblies (`gearbox`, `engine`). Returns 12 official subcategories for gearboxes or 5 service components for engines.
- **`check_commercial_vehicle(text)`**: Identifies commercial vehicles (`Tata Ace`, `Ashok Leyland Dost`, `Tata 407`) and warns that suppliers prioritize passenger cars.
- **`generate_async(prompt)`**: Executes Gemini calls with automatic fallback from `gemini-3.8-flash` to `gemini-3.5-flash-lite`.
- **`match_option_locally(answer, options)`**: Fast-path fuzzy matching for user replies against website dropdown options without invoking an API call.

### 3. State Machine & Graph: [`backend/parts_agent/graph.py`](file:///home/habilelabs/Development/CAS/backend/parts_agent/graph.py)
The central intelligence coordinator implemented as a LangGraph state machine:
- Manages conversational memory across multiple turns.
- Synchronizes shared facts (make, model, year) between Boodmo and AutoDukan.
- Passes Boodmo-resolved variant signatures into AutoDukan (`hints["boodmo_variant"]`) to eliminate duplicate user questions.
- Aggregates scraped listings, executes relevance scoring, and triggers summary announcements.

### 4. Boodmo Adapter: [`backend/parts_agent/boodmo.py`](file:///home/habilelabs/Development/CAS/backend/parts_agent/boodmo.py)
Automates Boodmo's marketplace (`https://boodmo.com`):
- **Offline Taxonomy Engine**: Resolves part names using `data/boodmo_catalog.json` (450 verified subcategories) with zero live network calls, eliminating 25-45 second page timeouts.
- **Canonical URL Mapping**: Maps canonical IDs cleanly (`Radiator` -> `/catalog/3731-radiator/`, `Fuel Pump` -> `/catalog/3620-fuel_pump/`).
- **Multi-Category Fallback**: If a vehicle's primary category yields 0 parts, it automatically explores candidate alternate categories (e.g. `Radiator Support`, `Cooling Fan`) before reporting.
- **Sequential Dropdown Navigation**: Drives `Maker` ➔ `Model Line` ➔ `Year` ➔ `Modification`.
- **Multi-Tab Product Enrichment (`_enrich`)**: Concurrently enriches top product listings using headless Playwright tabs to verify seller name, dispatch timeline, and live stock.
- **Part Number Unmasking**: Unmasks protected OEM part numbers (`KLP...9AA`) using URL slug analysis.

### 5. AutoDukan Adapter: [`backend/parts_agent/auto_dukan.py`](file:///home/habilelabs/Development/CAS/backend/parts_agent/auto_dukan.py)
Automates AutoDukan's distributor portal (`https://autodukan.com`):
- Interacts with Material-UI (MUI) dynamic comboboxes for Brand, Model, Year, and Variant.
- Contains brand aliasing (e.g., mapping `"Mercedes"` to `"MERCEDES-BENZ"`).
- Features multi-stage navigation in `_goto`: falls back to `wait_until="commit"` (12s) if `domcontentloaded` exceeds 25s.
- Automatic keyword search fallback (`_search_fallback`) if catalog category routes are unreachable.

---

## 3. Web Server & Streaming: [`backend/server.py`](file:///home/habilelabs/Development/CAS/backend/server.py)

Built on FastAPI, the server provides:
- **`POST /api/chat/start`**: Initiates a new sourcing session. Accepts mechanic message, thread ID, and headless browser preference.
- **`POST /api/chat/reply`**: Delivers mechanic's answer to an active `NeedInput` question.
- **`GET /api/events/{thread_id}`**: Server-Sent Events (SSE) streaming endpoint pushing live progress events (`adapter_progress`, `adapter_completed`, `log_event`) to the React dashboard.
- **`POST /api/transcribe`**: Accepts raw audio blobs from the browser microphone and transcribes speech using Gemini STT.
- **`POST /api/reset`**: Cleanly terminates background Playwright browser processes and resets session state.
- **Static Mounting**: Serves the compiled production frontend from `frontend/dist/`.

---

## 4. Frontend Dashboard: `frontend/`

- **Single-Page Application**: Built with React 18, Vite, and Tailwind CSS.
- **Zero Polling**: Consumes SSE events via `EventSource` in `App.jsx`, incrementally appending listings as suppliers finish.
- **Supplier Isolation**: Dedicated separate tables for Boodmo and AutoDukan with high-contrast prices, stock badges, and external links.
- **Procurement Recommendation Card**: Automatically compares live in-stock prices and provides a one-click **"Copy for Mechanic"** button.
- **Quick Test Chips**: One-click prompt buttons to quickly trigger test queries without manual typing.

---

## 5. Developer Guide: How to Run, Test, and Build

### Start Backend & Serve UI:
```bash
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```
Then open `http://localhost:8000` in your web browser.

### Run Comprehensive 50 Test Cases:
```bash
python3 -m unittest tests/test_50_cases.py -v
```

### Run Full Python Backend Test Suite (115 tests in <0.5s):
```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

### Run Frontend Component Test Suite (Vitest):
```bash
cd frontend
npm run test
cd ..
```

### Rebuild Frontend Production Assets:
```bash
cd frontend
npm run build
cd ..
```
