# Critical Review by Codex (Stratum)

Date: 2026-01-27
Scope (sequential):
1) `src/stratum/flow.py`, `src/stratum/crew.py`
2) `src/stratum/agents/`
3) `src/stratum/tools/`
4) `src/stratum/utils/recursion.py`
5) `tests/`

This project is incomplete; findings focus on gaps/risks, not polish.

---

## 1) Flow + Crew Orchestration

### Critical issues
- **Pipeline still uses placeholders rather than real task outputs**: `process_paper()` wires tasks but feeds `paper_text`, `title`, `authors`, `year`, and `knowledge_table_json` as placeholders. That means the Analyst is not consuming fetched text, and the Archivist is not consuming real KnowledgeTable output. (`src/stratum/crew.py`, `src/stratum/tasks/*.py`)
- **Crew result parsing is heuristic and string-based**: `_parse_crew_result()` scrapes DOIs from raw output with regex, and optionally infers a markdown path from string matching. There is no structured extraction from task outputs, so results are brittle and could miss citations or hallucinate DOIs. (`src/stratum/crew.py`)

### High/medium issues
- **Flow state type mismatch**: `StratumFlow.get_state()` advertises `StratumFlowState` but returns `self.state`, which is a dict managed by CrewAI Flow. This can confuse callers and tests. (`src/stratum/flow.py`)
- **Recursion limits are inconsistent with stats**: `RecursionState.should_process()` allows `current_depth == max_depth`, but `get_stats()` only counts depths `0..max_depth-1`. If `max_depth` is intended inclusive, stats omit the max depth bucket. (`src/stratum/models/state.py`)
- **Error handling is still mostly print-and-continue**: Flow errors are printed but not surfaced in results, so failures could be silent downstream. (`src/stratum/flow.py`)

### Improvements since last review
- Task dependencies are now wired via `Task.context`, and flow state uses `default_factory` to avoid shared mutable defaults.

---

## 2) Agents

### High/medium issues
- **Analyst system prompt still not enforced**: The system prompt helper is defined but not injected into task or agent configuration, so strict JSON output isn’t guaranteed. (`src/stratum/agents/analyst.py`, `src/stratum/tasks/analyze_paper.py`)
- **Agents hard-require `config/agents.yaml`** with no fallback; missing/malformed config will hard-fail. (`src/stratum/agents/*.py`)

---

## 3) Tools

### Critical issues
- **Citation enrichment can silently mis-attribute DOIs**: CrossRef lookup uses a simple title match and takes the top result. For partial titles or ambiguous matches, this can assign incorrect DOIs. There’s no confidence score or provenance recorded. (`src/stratum/tools/citation_finder.py`)

### High/medium issues
- **CrossRef lookup is on by default** and will generate network traffic during runs and tests unless explicitly disabled; no clear config path is surfaced in CLI. (`src/stratum/tools/citation_finder.py`)
- **Foundational ranking still biases toward recent papers** which conflicts with “foundational” in many fields. (`src/stratum/tools/citation_finder.py`)
- **`PDFTextExtractorTool` page count bug remains**: it still uses `len(doc)` after closing the document (if unchanged). Consider storing page count before close. (`src/stratum/tools/pdf_extractor.py`)

---

## 4) Recursion Utilities

### Medium issues
- **Non-atomic state writes**: state is rewritten on each `mark_processed()` without atomic write or lock; crashes can corrupt state. (`src/stratum/utils/recursion.py`)

---

## 5) Tests

### Improvements since last review
- Added integration tests for CLI (`tests/integration/test_cli.py`) and workflow scaffolding (`tests/integration/test_workflow.py`).
- Added an integration test asserting that tasks are chained in `StratumCrew.process_paper()`.

### Remaining gaps
- **End-to-end workflow test is skipped** and no tests validate real task outputs flowing between agents. (`tests/integration/test_workflow.py`)
- **No test covers DOI enrichment logic** (CrossRef), or potential false positives.
- **No tests validate that `CrewOutput` parsing yields correct citations/markdown paths**.

---

## Overall assessment (agreeing with the intended model?)

The architecture still aligns with the intended model, and the scaffolding is improved (task chaining, state defaults, CLI validation). However, **the core dataflow is still not real**: fetch output is not actually consumed by the Analyst, and KnowledgeTable output is not actually consumed by the Archivist. The crew result parsing is string-based and fragile. The model is sound, but the implementation remains a prototype.

---

## Suggested next focus (if you want a follow-up)
1) Replace placeholders with real task output binding (fetch → analyze → archive).
2) Parse structured `tasks_output` instead of regex scraping.
3) Add a small, mocked end-to-end test that asserts actual data flow between tasks.
4) Decide on CrossRef lookup strategy (opt-in, confidence threshold, provenance).
