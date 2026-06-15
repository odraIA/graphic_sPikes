from __future__ import annotations

import networkx as nx
import plotly.graph_objects as go

from .models import SNSystem


def build_nx_graph(system: SNSystem) -> nx.DiGraph:
    g = nx.DiGraph()
    for n in system.neurons:
        rules_summary = " | ".join(r.raw for r in n.rules[:2])
        role = ""
        if n.is_input:
            role += " [INPUT]"
        if n.is_output:
            role += " [OUTPUT]"
        g.add_node(n.id, label=f"{n.label}{role}\nspikes={n.initial_spikes}\n{rules_summary}")
    for s in system.synapses:
        g.add_edge(s.source, s.target)
    return g


def build_plotly_figure(g: nx.DiGraph) -> go.Figure:
    pos = nx.spring_layout(g, seed=7)
    edge_x, edge_y = [], []
    for u, v in g.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=1), hoverinfo="none")

    node_x, node_y, texts = [], [], []
    for n, data in g.nodes(data=True):
        x, y = pos[n]
        node_x.append(x)
        node_y.append(y)
        texts.append(data.get("label", n))

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=texts,
        textposition="top center",
        marker=dict(size=20, color="#74c0fc"),
        hovertext=texts,
        hoverinfo="text",
    )
    return go.Figure(data=[edge_trace, node_trace]).update_layout(showlegend=False)
