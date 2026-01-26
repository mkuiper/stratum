# Stratum

A CrewAI-based multi-agent system for recursive forensic audits of scientific research papers.

## Overview

Stratum performs deep analysis of scientific papers by extracting their fundamental structure: hypotheses, data, and conclusions. Based on George Whitesides' definition of a scientific paper, Stratum deconstructs research into Knowledge Tables and builds citation networks for graph visualization in Obsidian.

## Features

- **Three-Agent Architecture**
  - **Librarian Agent**: Fetches papers, extracts citations, ranks for recursive analysis
  - **Analyst Agent**: Deconstructs papers following the Whitesides Standard (hypothesis-driven, data-centric)
  - **Archivist Agent**: Converts analysis to Obsidian markdown with wikilinks

- **Model-Agnostic LLM Support**
  - Switch between OpenAI, Anthropic, or Ollama (local) by changing one config variable
  - Powered by LiteLLM for unified LLM interface

- **Recursive Paper Analysis**
  - Automatically analyzes foundational citations up to configurable MAX_DEPTH
  - Deduplication prevents reprocessing papers
  - State persistence enables resume after crashes

- **Knowledge Graph Output**
  - Generates Obsidian markdown files with YAML frontmatter
  - Wikilinks create navigable citation networks
  - Graph view visualizes paper dependencies

## Installation

### Prerequisites

- Python 3.10-3.13
- Docker (for GROBID citation parser)
- LLM API key (OpenAI/Anthropic) OR Ollama installed locally

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd stratum
```

2. Create virtual environment and install:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

4. Start GROBID (citation parser):
```bash
docker run -t --rm -p 8070:8070 lfoppiano/grobid:0.8.0
```

## Configuration

Edit `.env` to configure:

```bash
# LLM - Switch between providers
# Supported: OpenAI (gpt-4o), Anthropic (claude-3-5-sonnet-20241022),
#            Google Gemini (gemini/gemini-2.0-flash-exp), Ollama (ollama/llama3.2)
LLM_MODEL=gpt-4o
LLM_API_KEY=your_api_key_here

# Recursion settings
MAX_DEPTH=3
MAX_CITATIONS_PER_PAPER=5

# Paths
OUTPUT_DIR=./output
CACHE_DIR=./data
```

## Usage

### Check Dependencies

Before running, verify all dependencies are available:

```bash
stratum doctor
```

### Analyze a Paper

Analyze a paper recursively:

```bash
stratum analyze <DOI> --max-depth 3 --max-citations 5
```

Example:
```bash
stratum analyze 10.1000/example.2024 --max-depth 2 --max-citations 3
```

Options:
- `--max-depth, -d`: Maximum recursion depth (default: 3)
- `--max-citations, -c`: Max citations per paper (default: 5)
- `--output-dir, -o`: Output directory (default: ./output)
- `--model, -m`: LLM model to use (overrides .env)
- `--verbose/--quiet, -v/-q`: Enable/disable verbose output

### Check Status

View analysis progress and statistics:

```bash
stratum status
```

Shows:
- Total papers processed
- Papers by depth level
- List of processed DOIs

### Reset State

Clear analysis state to reprocess papers:

```bash
stratum reset --force
```

### Version Info

```bash
stratum version
```

## Project Structure

```
Stratum/
├── src/stratum/
│   ├── models/           # Pydantic data models
│   ├── agents/           # CrewAI agents
│   ├── tasks/            # CrewAI tasks
│   ├── tools/            # Custom tools (PDF, citations, etc.)
│   ├── llm/              # LLM abstraction (LiteLLM)
│   ├── config/           # Settings and agent configs
│   ├── utils/            # Utilities (recursion, obsidian)
│   ├── crew.py           # Crew orchestration
│   ├── flow.py           # Recursive workflow
│   └── main.py           # CLI entry point
│
├── output/papers/        # Generated Obsidian markdown
├── data/                 # Cache and state
└── tests/                # Unit and integration tests
```

## Development Status

- [x] **Phase 1**: Project foundation and data models ✅
- [x] **Phase 2**: Agent tools (PDF, citations, paper fetcher) ✅
- [x] **Phase 3**: LLM abstraction and agent definitions ✅
- [x] **Phase 4**: Crew orchestration and recursive flow ✅
- [x] **Phase 5**: CLI and production polish ✅

**🎉 MVP Complete!** All core functionality implemented and tested.

### Future Enhancements (Post-MVP)
- [ ] **Streamlit Web Interface**: Interactive UI for exploring papers and citation graphs
  - Paper upload and real-time analysis
  - Interactive Obsidian graph visualization
  - Citation network navigation with filtering
  - Evidence strength visualization
- [ ] **Figure/Table Extraction**: Computer vision for data extraction
- [ ] **Semantic Search**: Vector embeddings for similarity queries
- [ ] **Collaboration Features**: Shared vaults, annotations, discussions

## Data Contract

All agents communicate using the KnowledgeTable schema:

```json
{
  "kt_id": "KT_YYYY_XXX",
  "meta": {
    "title": "Paper Title",
    "authors": ["Author1", "Author2"],
    "year": 2024,
    "doi": "10.1000/example"
  },
  "core_analysis": {
    "central_hypothesis": "What question is being answered?",
    "methodology_summary": "How was it tested?",
    "significance": "Why does it matter?"
  },
  "key_points": [
    {
      "id": "KP1",
      "content": "Specific claim or finding",
      "evidence_anchor": "Table 2",
      "confidence_score": 0.95
    }
  ],
  "logic_chains": [
    {
      "name": "Argument Name",
      "argument_flow": "Step 1 -> Step 2 -> Conclusion",
      "conclusion_derived": "Final conclusion"
    }
  ],
  "citation_network": [
    {
      "target_paper_doi": "10.1000/cited",
      "target_paper_title": "Cited Paper",
      "usage_type": "Foundational",
      "notes": "Why this citation matters"
    }
  ]
}
```

## Testing

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=src/stratum --cov-report=html
```

Run specific test file:
```bash
pytest tests/unit/test_models.py -v
```

## Architecture Principles

### Whitesides Standard

Papers are organized descriptions of:
1. **Hypothesis** - What question is being tested?
2. **Data** - What evidence supports the answer?
3. **Conclusions** - What was learned?

### Analyst Agent Rules

1. **Hypothesis-Driven**: Identify what was TESTED, not just what was done
2. **Data-Centric**: Anchor every claim to specific evidence (Table X, Figure Y)
3. **Structure over Time**: Organize by logic, not chronology
4. **Strict JSON**: Output must validate against KnowledgeTable schema

## Contributing

Contributions welcome! Please ensure:
- All tests pass: `pytest`
- Code is formatted: `black src/ tests/`
- Linting passes: `ruff check src/ tests/`

## License

MIT

## Knowledge Distillation

Stratum performs **forensic knowledge distillation** - extracting the logical structure from narrative papers. See [knowledge/knowledge_distillation.md](knowledge/knowledge_distillation.md) for details on:
- The Whitesides Standard approach
- Evidence anchoring and logic chain mapping
- Typed citation networks (Foundational/Comparison/Refuting)
- Recursive knowledge graph construction

## Acknowledgments

- Based on the Whitesides Standard for scientific writing
- Powered by CrewAI, LiteLLM, and GROBID
- Designed for Obsidian graph visualization
- Supports OpenAI, Anthropic, Google Gemini, and Ollama (local) models
