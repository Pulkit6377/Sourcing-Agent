# Practical Agentic AI: A Complete Guide for Junior Engineers & Freshers

Welcome to the **AutoParts Sourcing Agent** codebase! If you are new to Agentic AI, this document is designed to give you a foundational understanding of what makes a software system "Agentic", how it differs from traditional LLM chatbots, and how this production system operates in the real world.

---

## 1. What is "Agentic AI"? (Chatbot vs. Agent)

Many developers first encounter AI as a simple chatbot: you send a prompt, and the LLM returns text. 

```
Traditional LLM:  User Prompt ──────────▶ [ LLM ] ──────────▶ Text Response
```

A chatbot cannot check real-time stock on a website, cannot click dropdowns, and cannot verify if a part actually exists in a distributor's warehouse. If you ask a chatbot: *"What is the price of an oil filter for a 2021 Tata Nexon?"*, it may guess or hallucinate a price based on outdated training data.

### An **Agentic AI System**, by contrast, has:
1. **Perception**: It reads user input (audio, text, Hinglish) and observes external digital environments (Playwright browser DOM).
2. **State & Memory**: It tracks what it knows (car model, year, engine, chosen part) across multi-turn conversations using a formal State Graph.
3. **Tools & Agency**: It autonomously takes actions in the real world—opening web browsers, navigating e-commerce portals, clicking dropdown menus, and extracting live prices.
4. **Guardrails & Determinism**: It does not rely on the LLM for everything. Critical logic (such as price calculations, timeout mitigation, and assembly disambiguation) is enforced using deterministic rules and state machines.
5. **Self-Healing & Fallbacks**: When external websites hang or change, the agent recovers gracefully rather than crashing.

```
Agentic Architecture:
                     ┌──────────────────┐
                     │   Mechanic / UI  │
                     └────────┬─────────┘
                              │
                              ▼
                   ┌──────────────────────┐
                   │  LangGraph Workflow  │ ◀── State Memory (Profile, History)
                   └──────────┬───────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ Gemini LLM    │     │ Boodmo Browser│     │ AutoDukan     │
│ Intent & STT  │     │ Adapter       │     │ Adapter       │
└───────────────┘     └───────────────┘     └───────────────┘
```

---

## 2. Core Architectural Concepts in This Project

### A. The State Graph (`parts_agent/graph.py`)
Instead of a giant `while True:` loop or an unstructured prompt, this agent uses a **Directed Acyclic Graph (DAG) state machine** powered by LangGraph:
- **`classify_intent`**: Understands whether the mechanic is providing vehicle info, answering a question, changing car details, or greeting.
- **`clarify_or_start`**: Checks if the vehicle details are complete. If not, it halts and poses a single, clear question (`NeedInput`).
- **`navigate`**: Directs both supplier adapters (Boodmo and AutoDukan) to advance concurrently on their respective websites.
- **`collect`**: Once the vehicle and category are locked, it scrapes product listings, seller names, dispatch times, and stock levels.
- **`summarize`**: Synthesizes the results into an actionable recommendation for the procurement manager.

### B. Dynamic Multi-Turn Slot Filling
Mechanics speak naturally and rarely provide all required details up front:
- User says: *"I need brake pads for a Swift"*
- The agent extracts: `Make: Maruti Suzuki`, `Model: Swift`, `Part: Brake Pads`.
- Missing slots: `Year`, `Fuel/Variant`.
- Rather than overwhelming the user with a questionnaire, the graph asks **one question at a time**, dynamically generating clickable chip options from the live website dropdowns.

### C. Fast-Path Regex vs. LLM Routing
- **Cost & Latency Optimization**: Never call a remote LLM API if a regex or local string match can do the job in 0.1 milliseconds.
- In `parts_agent/auto_dukan.py` and `parts_agent/boodmo.py`, we use deterministic regex tables for common parts (`brake pads`, `oil filter`, `clutch kit`, `transmission`).
- The LLM is reserved for ambiguous cases, natural language understanding, and audio transcription.

### D. Multi-Tier Model Fallback
In `parts_agent/llm.py`, we utilize a primary model (`gemini-3.8-flash`) for fast reasoning, with an automatic fallback to `gemini-3.5-flash-lite` if the primary service experiences gateway latency (e.g., HTTP 504). This ensures the application remains online even during external API downtime.

### E. Offline Taxonomy & Multi-Category Fallback (`data/boodmo_catalog.json`)
A common failure mode in web-scraping agents is scraping category trees live during user requests. E-commerce portals frequently update scripts, hang on tracking analytics, or time out when navigating deep category trees.
- In this codebase, we solved this with an **offline taxonomy file** (`data/boodmo_catalog.json`) containing **450 pre-indexed subcategories** with verified canonical URLs (e.g. `Radiator` -> `/catalog/3731-radiator/`).
- Category matching runs completely offline in memory, eliminating 25-45 second page timeouts.
- If a vehicle variant lists 0 parts under the primary category, the agent autonomously executes a **multi-category fallback**, searching related candidate categories (e.g. `Radiator Support`, `Cooling Fan`) before concluding. If none are found, it honestly tells the user: *"This part is not listed in Boodmo's catalogue for this vehicle."*

---

## 3. Real-World Engineering: The "Gearbox" Problem

To truly understand Agentic AI, examine the **Gearbox Problem** we solved in this codebase:

### The Problem:
Online auto parts marketplaces (like Boodmo and AutoDukan) **do not sell complete crate gearboxes or complete engines**. They only sell replacement parts (mountings, cables, clutch kits, sync rings, fluids).
Previously, when a user queried `"Tata Nexon gear Box"`, the naive search scraped items containing the word "gear". It returned ₹124 rubber dust boots (`Gear Lever Bellow`) and claimed: *"Found 4 gearboxes starting at ₹124!"*

### The Agentic Solution:
1. **Major Assembly Guard** (`parts_agent/llm.py`):
   Detects broad requests for crate assemblies (`gearbox`, `engine`).
2. **Proactive Clarification**:
   Immediately informs the mechanic:
   > *"Boodmo and AutoDukan do not sell complete gearbox assemblies online; they only stock individual gearbox components and repair parts. Boodmo lists 12 replacement categories. Which one do you need?"*
3. **Component Passthrough**:
   If the user already specified a concrete component (e.g. `"Swift gearbox mounting"` or `"Honda City clutch kit"`), the guard automatically detects the subcomponent and **passes it through directly** without unnecessary questions.

---

## 4. Key Rules for Freshers Working on This Codebase

1. **Never Hallucinate Availability or Price**:
   Every price and stock status displayed must come directly from verified DOM extraction on Boodmo or AutoDukan. If stock cannot be checked, mark it `available=None` (unchecked), never assume `True`.
2. **Always Handle Network Timeouts**:
   E-commerce sites are unpredictable. Never call Playwright's `page.goto` without timeout guards and multi-stage fallbacks (`commit` fallback).
3. **Keep State Independent**:
   Boodmo and AutoDukan have different vehicle hierarchies. Keep their selector profiles isolated, sharing only mechanic-verified hints (make, model, year, fuel).
4. **Run Unit Tests Before Submitting Code**:
   Every feature in this codebase is covered by automated, deterministic tests (115 backend unit/scenario tests and 8 React component tests with zero network dependency):
   ```bash
   # Run full Python backend test suite (runs in < 0.5s)
   python3 -m unittest discover -s tests -p 'test_*.py' -v

   # Run frontend component test suite (runs in ~3s)
   cd frontend && npm run test
   ```
