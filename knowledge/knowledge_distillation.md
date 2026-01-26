# Knowledge Distillation in Stratum

## Overview

Stratum performs **forensic knowledge distillation** of scientific papers - extracting the fundamental logical structure from narrative text and converting it into a machine-readable, graph-queryable format.

## The Problem: Papers as Narratives

Scientific papers are typically written as narratives:
- Chronological structure ("First we did X, then we tried Y...")
- Embedded assumptions and implicit connections
- Mixed signal-to-noise ratio (methodology details, historical context, speculation)
- Citations buried in prose without clear relationship classification

This narrative structure makes it difficult to:
- Quickly identify the core contribution
- Trace logical dependencies between claims
- Navigate citation networks programmatically
- Build knowledge graphs automatically

## Our Solution: Structure-First Extraction

Stratum applies the **Whitesides Standard** to extract papers into pure logical structures:

### 1. Hypothesis-Driven Analysis

**What we extract:**
- **Central Hypothesis**: The specific question or claim being validated
- Not "we studied X" but "we hypothesize X causes Y because Z"

**Why it matters:**
- Forces identification of the *research question*, not just activities
- Enables linking papers by shared hypotheses
- Clarifies what the paper actually tests vs. what it assumes

### 2. Data-Centric Evidence Anchoring

**What we extract:**
- **Key Points**: Atomic, verifiable claims
- **Evidence Anchors**: Direct references (Table 2, Figure 3, Equation 5)
- **Confidence Scores**: Quantified based on evidence strength

**Why it matters:**
- Separates verifiable claims from speculation
- Enables automatic fact-checking against raw data
- Allows filtering by evidence strength
- Makes papers machine-auditable

### 3. Logic Chain Mapping

**What we extract:**
- **Argument Flow**: How key points connect (KP1 → KP2 → KP3 → Conclusion)
- **Conclusion Derived**: What the argument establishes

**Why it matters:**
- Reveals the logical skeleton beneath narrative
- Identifies gaps or leaps in reasoning
- Enables automated argument strength analysis
- Shows alternative interpretations

### 4. Typed Citation Networks

**What we extract:**
- **Target Paper**: DOI and title
- **Usage Type**: Foundational / Comparison / Refuting
- **Relationship Notes**: Why this citation matters

**Why it matters:**
- Distinguishes "builds on" from "compares with" from "contradicts"
- Enables directed graph traversal (follow foundational links)
- Identifies knowledge dependencies
- Reveals scientific disagreements

## The Knowledge Table Format

Our output is a structured JSON **Knowledge Table**:

```json
{
  "kt_id": "KT_2024_Smith",
  "meta": {...},
  "core_analysis": {
    "central_hypothesis": "...",
    "methodology_summary": "...",
    "significance": "..."
  },
  "key_points": [
    {"id": "KP1", "content": "...", "evidence_anchor": "Table 2", "confidence_score": 0.95}
  ],
  "logic_chains": [
    {"name": "...", "argument_flow": "KP1 → KP2 → Conclusion", "conclusion_derived": "..."}
  ],
  "citation_network": [
    {"target_paper_doi": "...", "usage_type": "Foundational", "notes": "..."}
  ]
}
```

## Distillation Pipeline

### Stage 1: Ingestion (Librarian Agent)
- Fetch PDF from DOI or arXiv
- Extract full text with PyMuPDF
- Parse bibliography with GROBID (F1=0.89)
- Rank citations by importance

### Stage 2: Analysis (Analyst Agent)
- Apply Whitesides Standard rules
- Extract hypothesis (not narrative summary)
- Identify key points with evidence anchors
- Map logical argument chains
- Classify citation relationships
- Output strict JSON (validated by Pydantic)

### Stage 3: Archival (Archivist Agent)
- Convert JSON to Obsidian markdown
- Generate YAML frontmatter (metadata, tags)
- Create wikilinks for citations: `[[DOI|Title]]`
- Enable graph visualization

### Stage 4: Recursion (Flow Orchestration)
- Identify "Foundational" citations
- Recursively process up to MAX_DEPTH
- Build multi-level citation graphs
- Deduplicate (don't reprocess papers)

## Key Innovations

### 1. Evidence Anchoring
Unlike traditional summarization, we require **explicit evidence references**:
- ❌ "The model performs well"
- ✅ "The model achieves 95% accuracy (Table 2, confidence: 0.95)"

### 2. Logic Over Chronology
We ignore temporal narrative:
- ❌ "First we tried method A, then we tried B, finally we used C"
- ✅ "Method C achieves superior results (KP1) because it captures non-linearities (KP2) that methods A-B miss (KP3)"

### 3. Typed Citations
We classify *how* papers cite each other:
- **Foundational**: "This work builds on Smith et al. (2020) which established the baseline architecture"
- **Comparison**: "Unlike Jones et al. (2021), our approach does not require labeled data"
- **Refuting**: "This contradicts the findings of Brown et al. (2019) who claimed X"

### 4. Recursive Knowledge Graphs
We don't just extract one paper - we recursively follow "Foundational" citations to build **knowledge dependency trees**:

```
Seed Paper (2024)
├── Foundation A (2020)
│   ├── Foundation A1 (2015)
│   └── Foundation A2 (2018)
├── Foundation B (2022)
│   └── Foundation B1 (2019)
└── Comparison C (2023)  [not recursed - not foundational]
```

## Quality Control

### Validation Layers
1. **Schema Validation**: Pydantic enforces JSON structure
2. **Evidence Requirements**: Key points without anchors rejected
3. **Logic Consistency**: Argument chains must reference existing key points
4. **Citation Validation**: DOI format checked, duplicates prevented

### Confidence Scoring
Each key point gets a confidence score (0.0-1.0) based on:
- Strength of evidence (table/figure reference vs. text claim)
- Replication (multiple experiments showing same result)
- Statistical significance (p-values, effect sizes)

## Output: Obsidian Knowledge Graph

The final output is an **Obsidian vault** where:
- Each paper = one markdown file
- Citations = wikilinks creating graph edges
- Graph view visualizes knowledge dependencies
- Tags enable filtering (by year, topic, usage type)

**Example navigation:**
1. Start with recent paper on "deep learning for climate"
2. Follow [[Foundational]] wikilink to "LSTM networks"
3. Follow [[Foundational]] wikilink to "recurrent neural networks"
4. Now understand the lineage of ideas

## Comparison to Traditional Summarization

| Traditional Summarization | Stratum Knowledge Distillation |
|---------------------------|-------------------------------|
| "This paper studies X..." | "Hypothesis: X causes Y because Z" |
| Narrative summary | Logical structure |
| Citations listed | Citations classified by type |
| Single-paper focus | Recursive knowledge graphs |
| Text output | JSON + Markdown + Graph |
| Human-readable only | Machine-queryable |

## Future Enhancements

1. **Figure/Table Extraction**: OCR and computer vision to extract actual data
2. **Automatic Fact-Checking**: Compare claims against original tables
3. **Argument Strength Scoring**: ML model to score logical soundness
4. **Contradiction Detection**: Identify conflicting claims across papers
5. **Semantic Search**: Vector embeddings for similarity queries
6. **Interactive Exploration**: Streamlit UI for graph navigation

## Why This Matters

**For Researchers:**
- Understand paper lineage faster
- Identify knowledge gaps
- Find contradictions in literature

**For AI Systems:**
- Build structured knowledge bases
- Train on validated claims (not narratives)
- Reason over scientific graphs

**For Science:**
- Increase transparency (explicit logic chains)
- Improve reproducibility (evidence anchors)
- Accelerate discovery (structured knowledge)

---

*This approach transforms scientific papers from opaque narratives into transparent, traversable knowledge structures.*
