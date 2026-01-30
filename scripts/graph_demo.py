#!/usr/bin/env python3
"""Generate a citation graph JSON + HTML viewer from a fixture directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import textwrap
import webbrowser

from stratum.utils.graph_builder import build_citation_graph


HTML_TEMPLATE = """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
    <title>Stratum Citation Graph Viewer</title>
    <style>
      :root {
        color-scheme: light;
        font-family: \"IBM Plex Sans\", \"Segoe UI\", sans-serif;
        --bg: #f5f3ef;
        --card: #ffffff;
        --ink: #1b1b1b;
        --muted: #5c5c5c;
        --accent: #2f4f4f;
        --edge: #8d8d8d;
      }
      body {
        margin: 0;
        background: radial-gradient(circle at top, #ffffff 0, #f5f3ef 40%, #efe9e1 100%);
        color: var(--ink);
      }
      header {
        padding: 32px 24px 12px;
      }
      h1 {
        margin: 0 0 8px;
        font-weight: 600;
      }
      .meta {
        color: var(--muted);
        font-size: 14px;
      }
      .layout {
        display: grid;
        grid-template-columns: minmax(280px, 1fr) minmax(320px, 1fr);
        gap: 20px;
        padding: 12px 24px 32px;
      }
      .panel {
        background: var(--card);
        border-radius: 16px;
        padding: 16px;
        box-shadow: 0 12px 24px rgba(0, 0, 0, 0.08);
      }
      #graph {
        width: 100%;
        height: 520px;
        border-radius: 12px;
        background: #faf8f5;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
      }
      th, td {
        text-align: left;
        padding: 6px 4px;
        border-bottom: 1px solid #ece6dc;
      }
      th {
        color: var(--muted);
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.05em;
      }
      @media (max-width: 960px) {
        .layout {
          grid-template-columns: 1fr;
        }
        #graph {
          height: 420px;
        }
      }
    </style>
  </head>
  <body>
    <header>
      <h1>Stratum Citation Graph</h1>
      <div class=\"meta\">Nodes: {node_count} · Edges: {edge_count} · Source: {source_dir}</div>
    </header>
    <section class=\"layout\">
      <div class=\"panel\">
        <svg id=\"graph\" viewBox=\"0 0 800 520\" preserveAspectRatio=\"xMidYMid meet\"></svg>
      </div>
      <div class=\"panel\">
        <h2>Nodes</h2>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Title</th>
              <th>Year</th>
            </tr>
          </thead>
          <tbody id=\"node-table\"></tbody>
        </table>
      </div>
      <div class=\"panel\">
        <h2>Edges</h2>
        <table>
          <thead>
            <tr>
              <th>Source</th>
              <th>Target</th>
            </tr>
          </thead>
          <tbody id=\"edge-table\"></tbody>
        </table>
      </div>
    </section>
    <script>
      const graph = {graph_json};
      const nodeTable = document.getElementById("node-table");
      const edgeTable = document.getElementById("edge-table");

      for (const node of graph.nodes) {
        const row = document.createElement("tr");
        row.innerHTML = `<td>${node.id}</td><td>${node.title ?? ""}</td><td>${node.year ?? ""}</td>`;
        nodeTable.appendChild(row);
      }

      for (const edge of graph.edges) {
        const row = document.createElement("tr");
        row.innerHTML = `<td>${edge.source}</td><td>${edge.target}</td>`;
        edgeTable.appendChild(row);
      }

      const svg = document.getElementById("graph");
      const width = 800;
      const height = 520;
      const nodes = graph.nodes.map((node) => ({ ...node }));
      const links = graph.edges.map((edge) => ({ ...edge }));

      function fallbackMessage() {
        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute("x", "24");
        text.setAttribute("y", "48");
        text.setAttribute("fill", "#5c5c5c");
        text.textContent = "Graph preview requires D3.js (loaded from CDN).";
        svg.appendChild(text);
      }

      const script = document.createElement("script");
      script.src = "https://cdn.jsdelivr.net/npm/d3@7";
      script.onload = () => {
        const d3 = window.d3;
        const simulation = d3.forceSimulation(nodes)
          .force("link", d3.forceLink(links).id((d) => d.id).distance(140))
          .force("charge", d3.forceManyBody().strength(-360))
          .force("center", d3.forceCenter(width / 2, height / 2));

        const link = d3.select(svg)
          .append("g")
          .attr("stroke", "#8d8d8d")
          .attr("stroke-opacity", 0.6)
          .selectAll("line")
          .data(links)
          .join("line")
          .attr("stroke-width", 1.4);

        const node = d3.select(svg)
          .append("g")
          .selectAll("circle")
          .data(nodes)
          .join("circle")
          .attr("r", 10)
          .attr("fill", "#2f4f4f")
          .call(d3.drag()
            .on("start", (event, d) => {
              if (!event.active) simulation.alphaTarget(0.3).restart();
              d.fx = d.x;
              d.fy = d.y;
            })
            .on("drag", (event, d) => {
              d.fx = event.x;
              d.fy = event.y;
            })
            .on("end", (event, d) => {
              if (!event.active) simulation.alphaTarget(0);
              d.fx = null;
              d.fy = null;
            }));

        const label = d3.select(svg)
          .append("g")
          .selectAll("text")
          .data(nodes)
          .join("text")
          .text((d) => d.title || d.id)
          .attr("font-size", 11)
          .attr("fill", "#1b1b1b")
          .attr("dx", 12)
          .attr("dy", 4);

        simulation.on("tick", () => {
          link
            .attr("x1", (d) => d.source.x)
            .attr("y1", (d) => d.source.y)
            .attr("x2", (d) => d.target.x)
            .attr("y2", (d) => d.target.y);

          node
            .attr("cx", (d) => d.x)
            .attr("cy", (d) => d.y);

          label
            .attr("x", (d) => d.x)
            .attr("y", (d) => d.y);
        });
      };
      script.onerror = fallbackMessage;
      document.head.appendChild(script);
    </script>
  </body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a citation graph demo viewer.")
    parser.add_argument(
        "--input-dir",
        default="tests/fixtures/graph_sample",
        help="Directory containing sample markdown output.",
    )
    parser.add_argument(
        "--output-dir",
        default="output/graph_demo",
        help="Directory where graph JSON/HTML should be written.",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not attempt to open the HTML viewer automatically.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    graph = build_citation_graph(args.input_dir)
    graph_path = output_dir / "citation_graph.json"
    graph_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")

    html_path = output_dir / "citation_graph.html"
    html_payload = HTML_TEMPLATE.format(
        graph_json=json.dumps(graph),
        node_count=graph["metadata"]["node_count"],
        edge_count=graph["metadata"]["edge_count"],
        source_dir=graph["metadata"]["source_dir"],
    )
    html_path.write_text(textwrap.dedent(html_payload), encoding="utf-8")

    print(f"[graph-demo] Wrote {graph_path}")
    print(f"[graph-demo] Wrote {html_path}")

    if not args.no_open:
        webbrowser.open(html_path.resolve().as_uri())
        print("[graph-demo] Opening viewer in your default browser...")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
