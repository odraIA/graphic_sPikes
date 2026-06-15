from __future__ import annotations

import re

from .models import Neuron, SNSystem, SpikingRule, Synapse

A_TOKEN = r"a(?:\^(?P<{name}>\d+))?"
FIRING_RE = re.compile(rf"^(?P<regex>[^/]+)/\s*{A_TOKEN.format(name='c')}\s*->\s*{A_TOKEN.format(name='p')}\s*(?:;\s*(?P<d>\d+))?\s*$", re.IGNORECASE)
FORGET_RE = re.compile(rf"^{A_TOKEN.format(name='s')}\s*->\s*[λl]\s*$", re.IGNORECASE)
NEURON_HEAD_RE = re.compile(r"neuron\s+(?P<label>\w+)\s*:\s*(?P<spikes>\d+)\s*\{", re.IGNORECASE)
SYN_RE = re.compile(r"syn(?:apse)?\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)", re.IGNORECASE)
IO_RE = re.compile(r"^(input|output)\s*:\s*(\w+)\s*;?$", re.IGNORECASE)


def strip_comments(text: str) -> str:
    return "\n".join(re.sub(r"//.*$", "", ln) for ln in text.splitlines())


def parse_rule(raw: str, rid: str) -> SpikingRule:
    clean = " ".join(raw.strip().strip(";").split())
    firing = FIRING_RE.match(clean)
    if firing:
        return SpikingRule(id=rid, raw=clean, regex=firing.group("regex").strip(), consumed_spikes=int(firing.group("c") or 1), produced_spikes=int(firing.group("p") or 1), delay=int(firing.group("d") or 0), rule_type="firing")
    forgetting = FORGET_RE.match(clean)
    if forgetting:
        return SpikingRule(id=rid, raw=clean, consumed_spikes=int(forgetting.group("s") or 1), produced_spikes=0, delay=0, rule_type="forgetting")
    return SpikingRule(id=rid, raw=clean, rule_type="unknown")


def _statements(text: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    depth = 0
    for line in strip_comments(text).splitlines():
        if not line.strip():
            continue
        buf.append(line.strip())
        depth += line.count("{") - line.count("}")
        if depth <= 0 and (line.strip().endswith(";") or "}" in line):
            out.append(" ".join(buf).strip())
            buf = []
            depth = 0
    if buf:
        out.append(" ".join(buf).strip())
    return out


def parse_pli_text(text: str) -> SNSystem:
    neuron_map: dict[str, Neuron] = {}
    synapses: list[Synapse] = []
    input_neuron = None
    output_neuron = None
    warnings: list[str] = []
    recognized: list[str] = []
    ignored: list[str] = []

    for stmt in _statements(text):
        stmt_clean = stmt.strip()
        io = IO_RE.match(stmt_clean)
        if io:
            if io.group(1).lower() == "input":
                input_neuron = io.group(2)
            else:
                output_neuron = io.group(2)
            recognized.append(stmt_clean)
            continue
        syn = SYN_RE.search(stmt_clean)
        if syn:
            synapses.append(Synapse(source=syn.group(1), target=syn.group(2)))
            recognized.append(stmt_clean)
            continue
        head = NEURON_HEAD_RE.search(stmt_clean)
        if head and "}" in stmt_clean:
            label = head.group("label")
            body = stmt_clean.split("{", 1)[1].rsplit("}", 1)[0]
            raws = [r.strip() for r in re.split(r"\s*\|\s*", body) if r.strip()]
            rules = [parse_rule(raw, f"{label}_r{i}") for i, raw in enumerate(raws, 1)]
            for rule in rules:
                if rule.rule_type == "unknown":
                    warnings.append(f"Regla no reconocida en {label}: {rule.raw}")
            neuron_map[label] = Neuron(id=label, label=label, initial_spikes=int(head.group("spikes")), rules=rules)
            recognized.append(stmt_clean)
            continue
        ignored.append(stmt_clean)
        warnings.append(f"Bloque ignorado por el parser parcial: {stmt_clean[:120]}")

    for syn in synapses:
        neuron_map.setdefault(syn.source, Neuron(id=syn.source, label=syn.source))
        neuron_map.setdefault(syn.target, Neuron(id=syn.target, label=syn.target))
    if input_neuron:
        neuron_map.setdefault(input_neuron, Neuron(id=input_neuron, label=input_neuron)).is_input = True
    if output_neuron:
        neuron_map.setdefault(output_neuron, Neuron(id=output_neuron, label=output_neuron)).is_output = True
    return SNSystem(neurons=list(neuron_map.values()), synapses=synapses, input_neuron=input_neuron, output_neuron=output_neuron, raw_source=text, compilation_status="partial_from_pli", warnings=warnings, recognized_blocks=recognized, ignored_blocks=ignored)
