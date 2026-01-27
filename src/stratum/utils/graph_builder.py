"""Utilities for building citation graphs from Obsidian-style markdown output."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional, Tuple

import yaml


@dataclass(frozen=True)
class CitationNode:
    """Representation of a paper node extracted from output markdown."""

    node_id: str
    title: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        payload: Dict[str, Optional[str]] = {
            "id": self.node_id,
            "title": self.title,
            "year": self.year,
            "doi": self.doi,
        }
        return payload


@dataclass(frozen=True)
class CitationEdge:
    """Directed edge between papers in the citation network."""

    source: str
    target: str

    def to_dict(self) -> Dict[str, str]:
        return {"source": self.source, "target": self.target}


WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
FRONTMATTER_BOUNDARY_RE = re.compile(r"^---\s*$", re.MULTILINE)
HEADING_RE = re.compile(r"^(#{2,6})\s+(.*)$")
TITLE_RE = re.compile(r"^#\s+(.*)$")
YEAR_LINE_RE = re.compile(r"\*\*Year\*\*:\s*(\d{4})")
DOI_LINE_RE = re.compile(r"\*\*DOI\*\*:\s*\[([^\]]+)\]")


def build_citation_graph(output_dir: Path | str = Path("output/papers")) -> Dict[str, object]:
    """
    Build a citation graph from existing Obsidian-style markdown output.

    Args:
        output_dir: Directory containing markdown output files.

    Returns:
        JSON-serializable dict with nodes, edges, and metadata.
    """
    output_path = Path(output_dir)
    nodes: List[CitationNode] = []
    edges: List[CitationEdge] = []

    for markdown_path in sorted(output_path.rglob("*.md")):
        text = markdown_path.read_text(encoding="utf-8")
        frontmatter, body = _split_frontmatter(text)
        node = _parse_node(markdown_path, frontmatter, body)
        nodes.append(node)
        edges.extend(_parse_edges(node.node_id, body))

    graph = {
        "nodes": [node.to_dict() for node in nodes],
        "edges": [edge.to_dict() for edge in edges],
        "metadata": {
            "source_dir": str(output_path),
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
    }
    return graph


def _split_frontmatter(text: str) -> Tuple[Dict[str, object], str]:
    """Split YAML frontmatter from markdown body."""
    matches = list(FRONTMATTER_BOUNDARY_RE.finditer(text))
    if len(matches) >= 2 and matches[0].start() == 0:
        start = matches[0].end()
        end = matches[1].start()
        frontmatter_text = text[start:end].strip()
        body = text[matches[1].end():]
        try:
            data = yaml.safe_load(frontmatter_text) or {}
        except yaml.YAMLError:
            data = {}
        return data, body.lstrip("\n")
    return {}, text


def _parse_node(markdown_path: Path, frontmatter: Dict[str, object], body: str) -> CitationNode:
    kt_id = _get_string(frontmatter.get("kt_id"))
    doi = _get_string(frontmatter.get("doi")) or _extract_doi(body)
    title = _get_string(frontmatter.get("title")) or _extract_title(body)
    year = _get_int(frontmatter.get("year")) or _extract_year(body)

    if kt_id:
        node_id = kt_id
    elif doi:
        node_id = doi
    else:
        node_id = markdown_path.stem

    return CitationNode(node_id=node_id, title=title, year=year, doi=doi)


def _parse_edges(source_id: str, body: str) -> Iterable[CitationEdge]:
    section_lines = _extract_citation_section(body)
    edges: List[CitationEdge] = []
    for line in section_lines:
        for target, _title in _extract_wikilinks(line):
            edges.append(CitationEdge(source=source_id, target=target))
    return edges


def _extract_citation_section(body: str) -> List[str]:
    lines = body.splitlines()
    collecting = False
    collected: List[str] = []
    for line in lines:
        heading_match = HEADING_RE.match(line.strip())
        if heading_match:
            heading_text = heading_match.group(2).strip().lower()
            if heading_match.group(1) == "##" and "citation" in heading_text:
                collecting = True
                continue
            if collecting and heading_match.group(1) == "##":
                break
        if collecting:
            collected.append(line)
    return collected


def _extract_wikilinks(line: str) -> List[Tuple[str, Optional[str]]]:
    return [(match.group(1), match.group(2)) for match in WIKILINK_RE.finditer(line)]


def _extract_title(body: str) -> Optional[str]:
    for line in body.splitlines():
        match = TITLE_RE.match(line.strip())
        if match:
            return match.group(1).strip()
    return None


def _extract_year(body: str) -> Optional[int]:
    for line in body.splitlines():
        match = YEAR_LINE_RE.search(line)
        if match:
            return int(match.group(1))
    return None


def _extract_doi(body: str) -> Optional[str]:
    for line in body.splitlines():
        bracket_match = DOI_LINE_RE.search(line)
        if bracket_match:
            return bracket_match.group(1).strip()
    return None


def _get_string(value: object) -> Optional[str]:
    if isinstance(value, str):
        return value.strip() or None
    return None


def _get_int(value: object) -> Optional[int]:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None
