# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Stratum is a CrewAI-based multi-agent system for recursive forensic audits of scientific research papers. It follows the Whitesides Standard: papers are organized descriptions of hypotheses, data, and conclusions.

### Technology Stack

- **Framework**: CrewAI 1.8+ (multi-agent orchestration)
- **LLM**: Model-agnostic via LiteLLM (OpenAI, Anthropic, Ollama)
- **Data Validation**: Pydantic v2
- **PDF Processing**: PyMuPDF
- **Citation Parsing**: GROBID (Docker service)
- **Output Format**: Obsidian markdown with wikilinks
- **CLI**: Typer with Rich formatting
- **Testing**: pytest with coverage

### Build and Test Commands

```bash
# Install dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=src/stratum --cov-report=html

# Run specific test file
pytest tests/unit/test_models.py -v

# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Start GROBID service (required for citation parsing)
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0
```

## Architecture

### Three-Agent System

1. **Librarian Agent** (`agents/librarian.py`)
   - Fetches papers via Semantic Scholar API or arXiv
   - Extracts bibliographies using GROBID
   - Ranks citations by importance (Foundational > Comparison > Refuting)
   - Determines which papers to recursively analyze

2. **Analyst Agent** (`agents/analyst.py`)
   - Core logic engine following Whitesides Standard
   - Extracts central hypothesis, methodology, significance
   - Identifies key points with evidence anchors (Table X, Figure Y)
   - Builds logical argument chains
   - **CRITICAL**: Must output strict JSON matching KnowledgeTable schema

3. **Archivist Agent** (`agents/archivist.py`)
   - Converts JSON to Obsidian markdown
   - Generates YAML frontmatter
   - Creates wikilinks for citation network
   - Enables graph visualization

### Data Flow

```
DOI/PDF Input
    ↓
Librarian: Fetch + Parse Citations
    ↓
Analyst: Extract KnowledgeTable (JSON)
    ↓
Archivist: Generate Markdown
    ↓
output/papers/KT_YYYY_XXX.md
    ↓
[Recurse on Foundational Citations until MAX_DEPTH]
```

### Key Directories

- `src/stratum/models/` - Pydantic schemas (KnowledgeTable, PaperMetadata, etc.)
- `src/stratum/agents/` - Agent definitions
- `src/stratum/tasks/` - CrewAI task definitions
- `src/stratum/tools/` - Custom tools (PDF extraction, citation parsing, paper fetching)
- `src/stratum/llm/` - LLM abstraction layer (LiteLLM wrapper)
- `src/stratum/config/` - Settings (agents.yaml, tasks.yaml, settings.py)
- `src/stratum/utils/` - Utilities (recursion management, Obsidian formatting)
- `output/papers/` - Generated Obsidian markdown files
- `data/` - Cache (PDFs, processed papers, recursion state)
- `knowledge/` - RAG knowledge base for agents
- `tests/` - Unit and integration tests

## Critical Design Patterns

### 1. Strict Schema Validation

All agent outputs MUST validate against the KnowledgeTable Pydantic model:
- Use `model_validate()` to parse LLM JSON responses
- Retry with schema errors if validation fails
- Never allow unvalidated data to pass between agents

### 2. Model-Agnostic LLM

Switch LLM providers via `.env`:
```bash
LLM_MODEL=gpt-4o                      # OpenAI
LLM_MODEL=claude-3-5-sonnet-20241022  # Anthropic
LLM_MODEL=ollama/llama3.2             # Ollama (local)
```

LiteLLM handles all provider-specific differences.

### 3. Recursion with Deduplication

- `RecursionState` tracks processed DOIs in `data/state/processed_papers.json`
- `RecursionManager.should_process(doi, depth)` prevents:
  - Reprocessing same paper
  - Exceeding MAX_DEPTH
- State persists across runs (resume support)

### 4. Whitesides Standard Enforcement

The Analyst agent MUST follow these rules:
1. **Hypothesis-Driven**: Identify what was TESTED, not just what was done
2. **Data-Centric**: Anchor every Key Point to evidence (Table X, Figure Y)
3. **Structure over Time**: Organize by logic, not chronology
4. **Strict JSON**: Output must match KnowledgeTable schema

See `knowledge/whitesides_standard.txt` for detailed guidance.

## Development Workflow

### Phase 1: Foundation ✅ COMPLETE
- [x] Project structure
- [x] Pydantic models (KnowledgeTable, PaperMetadata, Citation, State)
- [x] Settings management (pydantic-settings)
- [x] Unit tests (35 tests, all passing)

### Phase 2: Tools (IN PROGRESS)
- [ ] `tools/base.py` - Abstract tool base class
- [ ] `tools/pdf_extractor.py` - PyMuPDF wrapper
- [ ] `tools/citation_finder.py` - GROBID integration
- [ ] `tools/paper_fetcher.py` - Semantic Scholar API
- [ ] `tools/obsidian_formatter.py` - Markdown generator

### Phase 3: LLM & Agents
- [ ] `llm/provider.py` - LiteLLM wrapper
- [ ] `config/agents.yaml` - Agent configurations
- [ ] `config/tasks.yaml` - Task definitions
- [ ] Agent implementations (librarian, analyst, archivist)

### Phase 4: Orchestration
- [ ] `crew.py` - CrewAI crew setup
- [ ] `utils/recursion.py` - RecursionManager
- [ ] `flow.py` - Recursive workflow with Flow

### Phase 5: CLI & Polish
- [ ] `main.py` - Typer CLI
- [ ] Error handling and retry logic
- [ ] Integration tests
- [ ] Documentation

## Important Notes for Claude

1. **Never modify the KnowledgeTable schema** without updating tests
2. **Always validate LLM outputs** with Pydantic before proceeding
3. **Test with multiple LLM providers** when changing llm/provider.py
4. **Check recursion state** before processing papers
5. **Use PyMuPDF** for PDF extraction (best for scientific papers)
6. **GROBID service must be running** on port 8070 for citation parsing
7. **Maintain backward compatibility** with existing .md files in output/

## Getting Started

1. Clone repository and create virtual environment
2. Install: `pip install -e ".[dev]"`
3. Copy `.env.example` to `.env` and configure
4. Start GROBID: `docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0`
5. Run tests: `pytest`
6. Analyze a paper: `stratum analyze <DOI> --max-depth 3`
