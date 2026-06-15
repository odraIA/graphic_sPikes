from __future__ import annotations

import re

from .models import Neuron, SNSystem, SpikingRule, Synapse

FIRING_RE = re.compile(r"^(?P<regex>[^/]+)/\s*a\^(?P<c>\d+)\s*->\s*a\^(?P<p>\d+)\s*;\s*(?P<d>\d+)\s*$")
FORGET_RE = re.compile(r"^a\^(?P<s>\d+)\s*->\s*[λl]$", re.IGNORECASE)


def parse_rule(raw: str, rid: str) -> SpikingRule:
    clean = raw.strip()
    firing = FIRING_RE.match(clean)
    if firing:
        return SpikingRule(
            id=rid,
            raw=clean,
            regex=firing.group("regex").strip(),
            consumed_spikes=int(firing.group("c")),
            produced_spikes=int(firing.group("p")),
            delay=int(firing.group("d")),
            rule_type="firing",
        )
    forgetting = FORGET_RE.match(clean)
    if forgetting:
        return SpikingRule(
            id=rid,
            raw=clean,
            consumed_spikes=int(forgetting.group("s")),
            produced_spikes=0,
            delay=0,
            rule_type="forgetting",
        )
    return SpikingRule(id=rid, raw=clean, rule_type="unknown")


def parse_pli_text(text: str) -> SNSystem:
    lines = [re.sub(r"//.*$", "", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    neuron_map: dict[str, Neuron] = {}
    synapses: list[Synapse] = []
    input_neuron = None
    output_neuron = None

    for ln in lines:
        if ln.lower().startswith("input"):
            input_neuron = ln.split(":")[-1].strip(" ;")
            continue
        if ln.lower().startswith("output"):
            output_neuron = ln.split(":")[-1].strip(" ;")
            continue

        syn_match = re.search(r"syn\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)", ln, re.IGNORECASE)
        if syn_match:
            synapses.append(Synapse(source=syn_match.group(1), target=syn_match.group(2)))
            continue

        n_match = re.search(r"neuron\s+(\w+)\s*:\s*(\d+)\s*\{(.*)\}\s*;?", ln, re.IGNORECASE)
        if n_match:
            label = n_match.group(1)
            spikes = int(n_match.group(2))
            rule_raws = [r.strip() for r in n_match.group(3).split("|") if r.strip()]
            rules = [parse_rule(raw, f"{label}_r{i}") for i, raw in enumerate(rule_raws, start=1)]
            neuron_map[label] = Neuron(id=label, label=label, initial_spikes=spikes, rules=rules)

    for syn in synapses:
        if syn.source not in neuron_map:
            neuron_map[syn.source] = Neuron(id=syn.source, label=syn.source)
        if syn.target not in neuron_map:
            neuron_map[syn.target] = Neuron(id=syn.target, label=syn.target)

    if input_neuron and input_neuron in neuron_map:
        neuron_map[input_neuron].is_input = True
    if output_neuron and output_neuron in neuron_map:
        neuron_map[output_neuron].is_output = True

    return SNSystem(
        neurons=list(neuron_map.values()),
        synapses=synapses,
        input_neuron=input_neuron,
        output_neuron=output_neuron,
        raw_source=text,
        compilation_status="partial_from_pli",
    )
