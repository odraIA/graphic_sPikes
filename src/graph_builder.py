from __future__ import annotations

import networkx as nx
import plotly.graph_objects as go

from .models import SNSystem

ROLE_COLORS = {"normal": "#74c0fc", "input": "#51cf66", "output": "#ff922b", "input_output": "#cc5de8"}


def _role(is_input: bool, is_output: bool) -> str:
    if is_input and is_output:
        return "input_output"
    if is_input:
        return "input"
    if is_output:
        return "output"
    return "normal"


def build_nx_graph(system: SNSystem) -> nx.DiGraph:
    g = nx.DiGraph()
    for n in system.neurons:
        tooltip = "<br>".join([f"<b>{n.label}</b>", f"Spikes iniciales: {n.initial_spikes}", f"Input: {n.is_input}", f"Output: {n.is_output}", "Reglas:"] + [f"- {r.raw} ({r.rule_type})" for r in n.rules])
        g.add_node(n.id, label=n.label, initial_spikes=n.initial_spikes, is_input=n.is_input, is_output=n.is_output, role=_role(n.is_input, n.is_output), tooltip=tooltip, rules=[r.model_dump() for r in n.rules])
    for s in system.synapses:
        g.add_edge(s.source, s.target)
    return g


def build_plotly_figure(g: nx.DiGraph) -> go.Figure:
    pos = nx.spring_layout(g, seed=7) if g.nodes else {}
    traces: list[go.BaseTraceType] = []
    for u, v in g.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        traces.append(go.Scatter(x=[x0, x1], y=[y0, y1], mode="lines", line=dict(width=1.5, color="#495057"), hoverinfo="none", showlegend=False))
        ax = x0 + 0.82 * (x1 - x0)
        ay = y0 + 0.82 * (y1 - y0)
        traces.append(go.Scatter(x=[ax], y=[ay], mode="markers", marker=dict(symbol="triangle-right", size=12, color="#495057", angle=0), hoverinfo="none", showlegend=False))

    for role, name in [("normal", "Neurona"), ("input", "Entrada"), ("output", "Salida"), ("input_output", "Entrada y salida")]:
        xs, ys, texts, hovers = [], [], [], []
        for n, data in g.nodes(data=True):
            if data.get("role") == role:
                x, y = pos[n]
                xs.append(x); ys.append(y)
                texts.append(f"{data.get('label', n)}<br>a={data.get('initial_spikes', 0)}")
                hovers.append(data.get("tooltip", n))
        if xs:
            traces.append(go.Scatter(x=xs, y=ys, mode="markers+text", text=texts, textposition="top center", marker=dict(size=28, color=ROLE_COLORS[role], line=dict(width=1, color="#212529")), hovertext=hovers, hoverinfo="text", name=name))
    fig = go.Figure(data=traces)
    fig.update_layout(showlegend=True, margin=dict(l=10, r=10, t=30, b=10), xaxis=dict(visible=False), yaxis=dict(visible=False), title="Grafo dirigido de sinapsis")
    return fig
