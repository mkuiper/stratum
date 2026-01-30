from pathlib import Path

from stratum.utils.graph_builder import build_citation_graph


def test_graph_output_conforms_to_spec() -> None:
    sample_dir = Path("tests/fixtures/graph_sample")
    graph = build_citation_graph(sample_dir)

    assert set(graph.keys()) == {"nodes", "edges", "metadata"}

    metadata = graph["metadata"]
    assert isinstance(metadata["source_dir"], str)
    assert isinstance(metadata["node_count"], int)
    assert isinstance(metadata["edge_count"], int)

    nodes = graph["nodes"]
    edges = graph["edges"]

    assert metadata["node_count"] == len(nodes)
    assert metadata["edge_count"] == len(edges)

    for node in nodes:
        assert set(node.keys()) == {"id", "title", "year", "doi"}
        assert isinstance(node["id"], str)
        assert isinstance(node["title"], (str, type(None)))
        assert isinstance(node["year"], (int, type(None)))
        assert isinstance(node["doi"], (str, type(None)))

    for edge in edges:
        assert set(edge.keys()) == {"source", "target"}
        assert isinstance(edge["source"], str)
        assert isinstance(edge["target"], str)
