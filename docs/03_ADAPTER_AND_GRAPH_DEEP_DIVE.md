# Deep Dive: What the Graph and Adapters Do at Every Stage

This document provides a technical walkthrough of how the conversational state graph coordinates supplier adapters to search, extract, and compare automotive parts across disparate e-commerce portals.

---

## 1. The Conversational Graph (`parts_agent/graph.py`)

The sourcing workflow is modeled as a LangGraph state machine. Each cycle processes the mechanic's message, resolves missing vehicle attributes, orchestrates browser adapters concurrently, and produces an actionable summary.

```mermaid
flowchart TD
    Start([Mechanic Input]) --> Classify[Node: classify_intent]
    Classify --> CheckAssembly{Major Assembly Guard?}
    CheckAssembly -- Yes (e.g. 'gearbox') --> AskComp[Prompt 12 Components]
    CheckAssembly -- No --> Clarify[Node: clarify_or_start]
    
    Clarify --> CheckMissing{Vehicle details complete?}
    CheckMissing -- Missing info --> NeedInput[Ask mechanic (NeedInput)]
    NeedInput --> MechanicReply([Mechanic Selection])
    MechanicReply --> Classify
    
    CheckMissing -- Complete --> Navigate[Node: navigate]
    Navigate --> AdvanceConcurrent["Advance Adapters Concurrently<br/>(Boodmo & AutoDukan)"]
    AdvanceConcurrent --> SyncHints[Sync Boodmo variant hint to AutoDukan]
    SyncHints --> Collect[Node: collect]
    
    Collect --> ScrapeConcurrent["Collect Listings Concurrently<br/>(Scrape + Enrich)"]
    ScrapeConcurrent --> Relevance[Filter & Tag Relevance]
    Relevance --> Summarize[Node: summarize]
    Summarize --> End([Render Frontend & Procurement Card])
```

---

### Step-by-Step Graph Node Responsibilities

#### Node 1: `classify_intent`
- Analyzes mechanic's input text using regex patterns and lightweight LLM classification.
- Detects whether the mechanic is answering a pending question, providing vehicle details, correcting a previously chosen field, or asking an unprompted question.
- Extracts inline hints (`_quick_hints`) such as fuel (`diesel`), transmission (`manual`), or year (`2021`) without incurring LLM latency.

#### Node 2: `clarify_or_start`
- Checks whether the requested part is a major vehicle assembly via `llm.check_major_assembly()`.
  - If user asked for `"gear box"` or `"engine"`: halts immediately, announces catalog constraints, and presents clickable component options.
  - If user asked for a concrete component (e.g. `"Swift gearbox mounting"`): passes through directly.
- Inspects the vehicle profile to verify whether Make, Model, and Part are identified. If any are missing, halts and generates a `NeedInput` prompt.

#### Node 3: `navigate`
- Executes concurrent calls to `adapter.advance()` for both Boodmo and AutoDukan.
- **Cross-Supplier Variant Synchronization**:
  - When Boodmo identifies its exact vehicle variant, the graph immediately injects the variant signature into AutoDukan's hints (`autodukan_p.hints["boodmo_variant"] = boodmo_p.variant`).
  - AutoDukan uses this signature to automatically match its corresponding variant, preventing the mechanic from having to answer the same trim question twice.

#### Node 4: `ask`
- If either website requires a user choice that cannot be inferred (e.g. Year or Variant), the graph transitions to the `ask` state.
- Emits a Server-Sent Event (`need_input`) containing the question and clickable choices (rendered as chips or a dropdown on the frontend).

#### Node 5: `collect`
- Once both supplier profiles are confirmed, the graph enters the extraction phase.
- Dispatches concurrent calls to `adapter.collect()` across both suppliers.
- **Autonomous Multi-Category Fallback (Boodmo)**:
  - If the primary category yields 0 parts on Boodmo for the selected trim, the adapter automatically checks alternate candidate categories (e.g. `Radiator Support`, `Cooling Fan`) before finalizing.
  - If no candidate category has parts, it generates a transparent notification: `"This part is not listed in Boodmo's catalogue for {vehicle}. (Checked categories: ...)"`.
- Scrapes product cards, prices, and seller information.
- Applies relevance scoring to tag each item (`EXACT_MATCH`, `COMPONENT`, `ACCESSORY`, or `IRRELEVANT`).

#### Node 6: `summarize`
- Formulates the final procurement summary comparing prices between Boodmo and AutoDukan.
- Reflects any fallback category that was used to source parts.
- Computes exact rupee savings, highlights in-stock sellers, and delivers the completion payload to the frontend.

---

## 2. Supplier Adapter Architecture & Contracts

Both adapters (`boodmo.py` and `auto_dukan.py`) implement a common interface contract:

| Method | Role | Return Type |
| :--- | :--- | :--- |
| `start()` | Initializes the Playwright browser instance and creates a fresh page context. | `None` |
| `resolve_category(profile)` | Maps the requested part string to the supplier's internal category hierarchy. | `Optional[NeedInput]` |
| `advance(profile)` | Drives the website UI controls to select Make, Model, Year, and Variant. | `Optional[NeedInput]` |
| `collect(profile)` | Extracts listings from the filtered catalog and enriches seller/stock data. | `SearchOutcome` |

---

## 3. What the Boodmo Adapter Does (`parts_agent/boodmo.py`)

Boodmo is an open marketplace hosting hundreds of independent parts distributors.

1. **Complete Offline Taxonomy Resolution (`data/boodmo_catalog.json`)**:
   - Loads from a clean, pre-indexed taxonomy file containing **450 subcategories** across all 34 top-level sections.
   - Operates **100% offline in memory**, eliminating live website scraping timeouts during category lookup.
   - Enforces verified canonical category URLs (e.g. `Radiator` -> `/catalog/3731-radiator/`, resolving the bug where it previously linked to fuel pump `3620`).
2. **Multi-Category Fallback Mechanism**:
   - If the selected vehicle variant returns 0 listings in the primary category, the adapter extracts the vehicle slug from the current URL and checks candidate alternate categories (`Radiator Support`, `Cooling Fan`, `Radiator Fan Motor`).
   - If found in an alternate category, it extracts verified listings and flags the alternate category used.
3. **Sequential Dropdown Navigation**:
   - Navigates: `Maker` ➔ `Model Line` ➔ `Year` ➔ `Modification/Variant`.
   - Normalizes whitespace and filters duplicate trim entries.
4. **Multi-Tab Product Enrichment (`_enrich`)**:
   - Opens up to 4 concurrent Playwright tabs for the top candidate listings.
   - Scrapes seller name, stock availability (`In Stock`), and dispatch timeline (`0-3 days`).
   - If a product page stalls, a 20s timeout guard logs a note and continues without blocking the batch.
5. **Part Number Unmasking**:
   - Boodmo masks OEM part numbers in the main view (e.g. `04465...090`).
   - The adapter extracts the unmasked OEM part number from the URL slug (e.g. `/part-04465_0k090-12345/`).

---

## 4. What the AutoDukan Adapter Does (`parts_agent/auto_dukan.py`)

AutoDukan is a direct automotive parts distributor utilizing a modern React/Material-UI frontend.

1. **Direct Category Fast-Path**:
   - Evaluates a regex table covering 20+ automotive categories (`TRANSMISSION`, `BRAKE PADS`, `OIL FILTER`, `CLUTCH SET`, `WIPER BLADES`).
   - If matched, directly formats the category slug without visiting the slow `/category` page.
2. **Material-UI Dynamic Combobox Interaction**:
   - AutoDukan uses dynamic React comboboxes rather than native HTML `<select>` elements.
   - The adapter clicks input containers, types search strings, waits for MUI popovers to render, and selects verified options.
3. **Multi-Stage Navigation Safeguard**:
   - Navigation timeout is set to 25s with an automatic fallback to `wait_until="commit"` (12s).
   - This ensures heavy tracking pixels or background analytics never stall the scraper.
4. **Automated Search Bar Fallback (`_search_fallback`)**:
   - If direct category routing is unavailable or times out, the adapter automatically constructs a query URL:
     `https://autodukan.com/products-list?search=Tata+Nexon+Manual+Transmission`
   - Sets `_using_search_fallback = True` and proceeds to extract listings directly from the search bar view without crashing or prompting the user.
