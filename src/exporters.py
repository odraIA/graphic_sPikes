from __future__ import annotations

from pathlib import Path
import csv
import io

import networkx as nx

from .models import SNSystem


def rules_csv_text(system: SNSystem) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["neuron_id", "initial_spikes", "rule_type", "regex", "consumed", "produced", "delay", "rule_raw"])
    writer.writeheader()
    for n in system.neurons:
        for r in n.rules:
            writer.writerow({"neuron_id": n.id, "initial_spikes": n.initial_spikes, "rule_type": r.rule_type, "regex": r.regex or "", "consumed": r.consumed_spikes, "produced": r.produced_spikes, "delay": r.delay, "rule_raw": r.raw})
    return buf.getvalue()


def system_json_text(system: SNSystem) -> str:
    return system.model_dump_json(indent=2)


def graph_html_text(g: nx.DiGraph) -> str:
    node_lines = "".join(f"<li><b>{n}</b>: spikes={d.get('initial_spikes',0)}, role={d.get('role','normal')}</li>" for n, d in g.nodes(data=True))
    edge_lines = "".join(f"<li>{u} → {v}</li>" for u, v in g.edges())
    return f"<!doctype html><html><meta charset='utf-8'><body><h2>Grafo SN P</h2><ul>{node_lines}</ul><h3>Sinapsis dirigidas</h3><ul>{edge_lines}</ul></body></html>"


def export_rules_csv(system: SNSystem, output_path: str | Path) -> str:
    Path(output_path).write_text(rules_csv_text(system), encoding="utf-8")
    return str(output_path)


def export_graph_html(g: nx.DiGraph, output_path: str | Path) -> str:
    Path(output_path).write_text(graph_html_text(g), encoding="utf-8")
    return str(output_path)
