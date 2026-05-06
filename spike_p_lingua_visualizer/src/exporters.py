from __future__ import annotations

from pathlib import Path
import csv

import networkx as nx

from .models import SNSystem


def export_rules_csv(system: SNSystem, output_path: str | Path) -> str:
    path = Path(output_path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["neuron_id", "initial_spikes", "rule_type", "rule_raw", "consumed", "produced", "delay"],
        )
        writer.writeheader()
        for n in system.neurons:
            for r in n.rules:
                writer.writerow(
                    {
                        "neuron_id": n.id,
                        "initial_spikes": n.initial_spikes,
                        "rule_type": r.rule_type,
                        "rule_raw": r.raw,
                        "consumed": r.consumed_spikes,
                        "produced": r.produced_spikes,
                        "delay": r.delay,
                    }
                )
    return str(path)


def export_graph_html(g: nx.DiGraph, output_path: str | Path) -> str:
    path = Path(output_path)
    node_lines = "".join(f"<li>{n}: {d.get('label','')}</li>" for n, d in g.nodes(data=True))
    edge_lines = "".join(f"<li>{u} -> {v}</li>" for u, v in g.edges())
    html = f"<html><body><h2>Graph</h2><ul>{node_lines}</ul><h3>Edges</h3><ul>{edge_lines}</ul></body></html>"
    path.write_text(html, encoding="utf-8")
    return str(path)
