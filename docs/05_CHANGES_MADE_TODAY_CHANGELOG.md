# Detailed Technical Changelog: Key Engineering Upgrades Made Today

This document outlines all technical updates, architectural enhancements, bug fixes, and test implementations completed in this engineering session.

---

## 1. Major Assembly Disambiguation & The "₹124 Gearbox" Fix

### The Problem:
- When a mechanic searched for `"gear box"`, Boodmo does not sell complete crate gearboxes online (they only stock individual repair components).
- Naive text matching previously returned ₹124 and ₹135 rubber dust boots (`Gear Lever Bellow`), displaying misleading prices for a "gearbox".

### The Solution Implemented:
1. **Major Assembly Disambiguation Guard** ([`parts_agent/llm.py`](file:///home/habilelabs/Development/CAS/parts_agent/llm.py)):
   - Added `check_major_assembly()` to intercept broad assembly requests (`gearbox`, `engine`).
   - Informs the mechanic that online portals stock service parts rather than crate assemblies.
   - Prompts the mechanic with Boodmo's **12 official replacement categories**.
2. **Aligned with Boodmo's 12 Official Transmission Categories**:
   - `Manual Transmission`, `Automatic Transmission`, `Transmission Bracket (Mounting)`, `Gear Shift Cable`, `Clutch Kit`, `Gear Shifter Repair Kit`, `Transmission Gear`, `Transmission Housing`, `Transmission Shaft`, `Gear Shift Fork`, `Synchronizer Ring`, `Manual Transmission Fluid`.
   - Registered all 12 categories in `cache/boodmo_categories.json` under `"leaf"` with verified category URLs.
   - Removed the previous hardcoded `n=4` limit in [`parts_agent/boodmo.py`](file:///home/habilelabs/Development/CAS/parts_agent/boodmo.py).
3. **Specific Component Passthrough**:
   - When the user already specifies a concrete subcomponent (e.g. `"Swift gearbox mounting"` or `"Honda City clutch kit"`), the guard detects the component and passes it directly through to the catalog search without friction.

---

## 2. Catalogue Navigation Timeout Mitigation

### The Problem:
- Run `runs/20261112-114100-eca5eda2.json` failed with:
  `Page.goto: Timeout 45000ms exceeded. Call log: - navigating to "https://autodukan.com/category", waiting until "domcontentloaded"`
- Queries like `"Manual Transmission"` were missing from the direct category regex table, triggering an unnecessary navigation to AutoDukan's `/category` page, which often hangs on heavy tracking scripts.

### The Solution Implemented:
1. **Multi-Stage Navigation Safeguard** in [`parts_agent/auto_dukan.py`](file:///home/habilelabs/Development/CAS/parts_agent/auto_dukan.py#L256) and [`parts_agent/boodmo.py`](file:///home/habilelabs/Development/CAS/parts_agent/boodmo.py#L141):
   - Lowered navigation timeout from 45s to 25s.
   - Implemented an automatic retry with `wait_until="commit"` (12s) if `domcontentloaded` stalls, allowing HTML parsing to continue without hanging.
2. **Expanded Direct Regex Mappings**:
   - Added direct fast-path regexes for `TRANSMISSION`, `TRANSMISSION MOUNTING`, `CLUTCH SET`, `WIPER BLADES`, `SPARK PLUG`, `RADIATOR`, `HORN`, `BATTERY`, `ALTERNATOR`, `SHOCK ABSORBER`, `WATER PUMP`, and `BELTS`.
   - These parts now bypass `/category` entirely.
3. **Automatic Search Bar Fallback**:
   - Wrapped category indexing in `try...except`.
   - If direct category routing is unavailable or times out, the adapter automatically executes:
     `https://autodukan.com/products-list?search=Tata+Nexon+Manual+Transmission`
   - Sets `_using_search_fallback = True` and scrapes search results cleanly without crashing.

---

## 3. Dedicated Supplier Product Listings on Frontend

### The Problem:
- Products from Boodmo and AutoDukan were previously mixed together in a single row list, making it difficult for procurement officers to track supplier performance or compare prices.

### The Solution Implemented ([`frontend/src/components/ProductResults.jsx`](file:///home/habilelabs/Development/CAS/frontend/src/components/ProductResults.jsx)):
1. **Isolated Supplier Sections**:
   - Replaced mixed rows with dedicated, branded sections:
     - **Boodmo Verified Marketplace Catalog**
     - **AutoDukan Verified Distributor Catalog**
2. **Executive Procurement Recommendation Card**:
   - Compares lowest in-stock prices between suppliers.
   - Highlights exact rupee savings (e.g. *"Source from Boodmo: Save ₹250 with Bosch..."*).
   - Features a one-click **"Copy for Mechanic"** button to copy recommendation text to clipboard.
3. **Flexible View Modes**:
   - Stacked View (both suppliers visible), Side-by-Side (50/50 split), and Supplier Tabs (`All`, `Boodmo Only`, `AutoDukan Only`).

---

## 4. UI Polish & Simplification ("Keep It Basic")

### The Improvements Made:
1. **One-Click Quick Test Suggestions** ([`frontend/src/components/ConversationPanel.jsx`](file:///home/habilelabs/Development/CAS/frontend/src/components/ConversationPanel.jsx#L427-L457)):
   - Added 4 starter prompt chips (`Tata Nexon oil filter`, `Swift front brake pads`, `Innova Crysta clutch kit`, `Mercedes E-Class brake pads`) for instant manager testing.
2. **Decluttered Header** ([`frontend/src/components/Header.jsx`](file:///home/habilelabs/Development/CAS/frontend/src/components/Header.jsx)):
   - Clean automotive wrench branding, live connection dot, headless browser toggle, and reset button.
3. **Simplified Supplier Monitor** ([`frontend/src/components/SupplierMonitor.jsx`](file:///home/habilelabs/Development/CAS/frontend/src/components/SupplierMonitor.jsx)):
   - Streamlined status cards for Boodmo and AutoDukan with clean status badges and slim progress indicators.
4. **Clean Execution Activity Bar** ([`frontend/src/components/ActivityLog.jsx`](file:///home/habilelabs/Development/CAS/frontend/src/components/ActivityLog.jsx)):
   - Replaced 5 bulky metric boxes with a sleek 1-line summary (`16 parts found • 12 in stock`).
   - Technical browser log is tucked behind a clean collapsible toggle.
5. **Fresh Production Build**:
   - Rebuilt frontend assets into `frontend/dist/` via Vite (`index-BTyPvZqI.css` & `index-B8-9HpZI.js`).

---

## 5. Comprehensive 50 Automated Test Cases

### Implementation ([`tests/test_50_cases.py`](file:///home/habilelabs/Development/CAS/tests/test_50_cases.py)):
- Created a standalone test suite containing **50 deterministic test cases**:
  - `TC-01 – TC-08`: Major Assembly Disambiguation
  - `TC-09 – TC-15`: Specific Component Passthrough
  - `TC-16 – TC-23`: Vehicle Extraction & Trim Parsing
  - `TC-24 – TC-28`: Cross-Supplier Variant Handover
  - `TC-29 – TC-34`: Timeout Resilience & Fallback
  - `TC-35 – TC-40`: Relevance Filtering & Classification
  - `TC-41 – TC-45`: Price Parsing, Stock & Offers
  - `TC-46 – TC-50`: Procurement Recommendation & Commercial Vehicle Guard
- **Execution Result**:
  `Ran 50 tests in 0.160s ... OK (100% passing)`
- Published executive verification matrix in `test_cases_50.md`.

---

## 6. Reliable Python Test Isolation & Frontend Vitest Test Suite

### The Problem:
- The synchronous FastAPI `TestClient` tests in `tests/test_api_integration.py` previously hung for ~19 seconds because they triggered background Gemini API calls and Playwright browser allocations.
- There was no automated frontend test script or component test coverage.

### The Solution Implemented:
1. **Isolated Backend Integration Tests** ([`tests/test_api_integration.py`](file:///home/habilelabs/Development/CAS/tests/test_api_integration.py)):
   - Mocked `server.Conversation` and `server.open_session` in `/api/chat/start` and `/api/reset`.
   - Mocked `CONVERSATIONS[thread_id]` in `/api/chat/reply`.
   - Mocked `server.voice.transcribe` and `subprocess.run` (ffmpeg conversion) in `/api/transcribe`.
   - Reduced integration test execution time from ~19s to **0.089s**.
2. **Frontend Test Framework Setup** ([`frontend/package.json`](file:///home/habilelabs/Development/CAS/frontend/package.json), [`frontend/vite.config.js`](file:///home/habilelabs/Development/CAS/frontend/vite.config.js)):
   - Configured `vitest` (^2.1.8), `@testing-library/react` (^16.3.3), and `jsdom` (^25.0.1) matching Vite 5.
   - Added `"test": "vitest run"` script to `package.json`.
   - Created [`frontend/src/setupTests.js`](file:///home/habilelabs/Development/CAS/frontend/src/setupTests.js) with JSDOM polyfills.
3. **Automated Component Tests**:
   - [`frontend/src/__tests__/ProductResults.test.jsx`](file:///home/habilelabs/Development/CAS/frontend/src/__tests__/ProductResults.test.jsx): 4 tests covering adapter section separation, procurement recommendation savings, text filtering, and tier filtering.
   - [`frontend/src/__tests__/ConversationPanel.test.jsx`](file:///home/habilelabs/Development/CAS/frontend/src/__tests__/ConversationPanel.test.jsx): 4 tests covering empty state prompts, message rendering, form submission, and question option chips.
   - **Result**: All 8 tests passing in ~3.9s.

---

## 7. Offline Boodmo Taxonomy Catalogue & Multi-Category Fallback Flow

### The Problem:
- When searching for parts outside the initial cache (such as `"Radiator"`), Boodmo attempted to scrape parent category trees (like `Engine Cooling System`) live during the user request, causing a **25-45 second page timeout**.
- A corrupt entry in the legacy cache pointed `"Radiator"` to category ID `3620` (`Fuel Pump`), returning fuel pumps instead of radiators.
- When a specific car trim had 0 parts under a category, the system gave up immediately without exploring valid related categories (e.g. `Radiator Support`, `Cooling Fan`).

### The Solution Implemented:
1. **Canonical Offline Catalogue** ([`data/boodmo_catalog.json`](file:///home/habilelabs/Development/CAS/data/boodmo_catalog.json)):
   - Indexed all **34 top-level sections** and **450 subcategories** into a standalone, local JSON catalogue.
   - Fixed Radiator canonical URL to **`/catalog/3731-radiator/`** and Fuel Pump to **`/catalog/3620-fuel_pump/`**.
   - Added 35 automotive synonym and fallback mappings (`radiator`, `water pump`, `clutch`, `brake pads`, `shock absorber`, etc.).
2. **Zero-Network Category Resolution** ([`parts_agent/boodmo.py`](file:///home/habilelabs/Development/CAS/parts_agent/boodmo.py)):
   - Rewrote `resolve_category()` to load directly from `data/boodmo_catalog.json` in memory.
   - **100% eliminated live category scraping timeouts**.
3. **Multi-Category Fallback Flow**:
   - If the selected vehicle variant returns 0 listings in the primary category, the adapter extracts the vehicle slug and checks candidate alternate categories (`profile.hints["alternate_categories"]`).
   - If found in an alternate category, it extracts verified listings and informs the user via `resolved_alternate_category`.
   - If all candidate categories have no parts, it generates a transparent and truthful message:
     `"This part is not listed in Boodmo's catalogue for {vehicle}. (Checked categories: ...)"`
4. **Hardened Price Parsing**:
   - Updated `_price()` in `boodmo.py` to robustly accept integer and float values in addition to currency strings.
5. **Backend Test Suite Expansion** ([`tests/test_unit.py`](file:///home/habilelabs/Development/CAS/tests/test_unit.py)):
   - Added tests verifying offline resolution of Radiator, Water Pump, and Cooling Fan.
   - Added tests for multi-category fallback execution and honest "not listed" reporting.
   - Total backend tests expanded to **115 tests passing in 0.439s**.
