# Stratum TODO - Post-Reboot Tasks

## Priority 1: Improve Human Readability

Currently, the system only shows DOIs which are not human-readable for researchers.

**Changes needed:**
- Store paper titles alongside DOIs in recursion state
- Display titles in verbose output (e.g., "Processing: AlphaFold2 reveals... (10.1038/...)")
- Add title to markdown frontmatter
- Show titles in `stratum status` command

**Files to modify:**
- `src/stratum/models/state.py` - Add title to depth_map (make it store {doi: (depth, title)})
- `src/stratum/flow.py` - Extract and store titles when processing papers
- `src/stratum/main.py` - Display titles in status output

## Priority 2: Multi-Model Configuration

Different tasks have different complexity levels. We should use:
- **Expensive models (GPT-4o, Claude Opus)** for analysis (creating Knowledge Tables)
- **Cheap models (GPT-4o-mini, Claude Haiku)** for extraction tasks (citations, metadata)

**Changes needed:**
- Add separate model configs to `.env`:
  ```
  LLM_MODEL_ANALYST=gpt-4o           # For Knowledge Table extraction (complex)
  LLM_MODEL_LIBRARIAN=gpt-4o-mini   # For citation extraction (simple)
  LLM_MODEL_ARCHIVIST=gpt-4o-mini   # For markdown formatting (simple)
  ```
- Update `Settings` to support per-agent models
- Update agent creation to use agent-specific models
- Document cost savings in README

**Files to modify:**
- `src/stratum/config/settings.py` - Add per-agent model fields
- `src/stratum/agents/*.py` - Accept model parameter
- `src/stratum/crew.py` - Pass agent-specific models
- `.env.example` - Document model configuration

## Priority 3: Test Recursion

With the fixes committed, test:
```bash
stratum analyze "10.1038/s41586-020-2649-2" --max-depth 1 --max-citations 3 --fresh
```

Should process:
- Depth 0: NumPy paper (1 paper)
- Depth 1: Top 3 foundational citations (3 papers)
- Total: 4 papers

**Verify:**
- Citations are extracted with verbose logging
- Papers at depth 1 are queued and processed
- Output directory has 4 markdown files
- `stratum status` shows papers at both depths

## Priority 4: Obsidian Integration

Test opening the output in Obsidian to visualize the citation network graph.

**Questions to answer:**
- Do wikilinks work correctly?
- Does the graph view show citation relationships?
- Are node labels readable (titles vs DOIs)?
