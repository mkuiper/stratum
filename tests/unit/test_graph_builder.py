from pathlib import Path

from stratum.utils.graph_builder import build_citation_graph


def _write_markdown(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_build_citation_graph_parses_nodes_and_edges(tmp_path: Path) -> None:
    output_dir = tmp_path / "papers"
    output_dir.mkdir()

    _write_markdown(
        output_dir / "KT_2024_Smith.md",
        """---
kt_id: KT_2024_Smith
title: Machine Learning for Climate Science
authors:
  - Smith, J.
year: 2024
doi: 10.1000/climate.2024.001
---

# Machine Learning for Climate Science

## Citation Network

- [[10.1000/foundational.2020|Deep Learning Fundamentals]]
- [[KT_2019_Baseline|Baseline Methods]]

## Other Section

- [[should_not_count|Not a citation]]
""",
    )

    _write_markdown(
        output_dir / "baseline.md",
        """---
title: Baseline Methods
year: 2019
doi: 10.5555/baseline.2019
---

# Baseline Methods

## Citation Network

- [[10.7777/related.2018|Related Work]]
""",
    )

    graph = build_citation_graph(output_dir)

    assert graph["metadata"]["node_count"] == 2
    assert graph["metadata"]["edge_count"] == 3

    nodes_by_id = {node["id"]: node for node in graph["nodes"]}
    assert "KT_2024_Smith" in nodes_by_id
    assert nodes_by_id["KT_2024_Smith"]["doi"] == "10.1000/climate.2024.001"
    assert nodes_by_id["KT_2024_Smith"]["title"] == "Machine Learning for Climate Science"
    assert nodes_by_id["KT_2024_Smith"]["year"] == 2024

    assert "10.5555/baseline.2019" in nodes_by_id
    assert nodes_by_id["10.5555/baseline.2019"]["title"] == "Baseline Methods"

    edges = {(edge["source"], edge["target"]) for edge in graph["edges"]}
    assert ("KT_2024_Smith", "10.1000/foundational.2020") in edges
    assert ("KT_2024_Smith", "KT_2019_Baseline") in edges
    assert ("10.5555/baseline.2019", "10.7777/related.2018") in edges
    assert ("KT_2024_Smith", "should_not_count") not in edges


def test_build_citation_graph_falls_back_to_filename(tmp_path: Path) -> None:
    output_dir = tmp_path / "papers"
    output_dir.mkdir()

    _write_markdown(
        output_dir / "no_frontmatter.md",
        """# Untitled

## Citation Network

- [[10.0000/example|Example]]
""",
    )

    graph = build_citation_graph(output_dir)
    assert graph["nodes"][0]["id"] == "no_frontmatter"
