from __future__ import annotations

from pathlib import Path
import xml.etree.ElementTree as ET

from .models import Neuron, SNSystem, SpikingRule, Synapse
from .parser_pli import parse_rule


def parse_xml_file(xml_path: str | Path) -> SNSystem:
    tree = ET.parse(xml_path)
    root = tree.getroot()

    neurons: dict[str, Neuron] = {}
    synapses: list[Synapse] = []

    input_neuron = root.attrib.get("input")
    output_neuron = root.attrib.get("output")

    for n_el in root.findall(".//neuron"):
        nid = n_el.attrib.get("id") or n_el.attrib.get("label") or "unknown"
        spikes = int(n_el.attrib.get("spikes", "0"))
        rules: list[SpikingRule] = []
        for i, r_el in enumerate(n_el.findall(".//rule"), start=1):
            raw = (r_el.text or r_el.attrib.get("raw") or "").strip()
            rules.append(parse_rule(raw, f"{nid}_r{i}"))
        neurons[nid] = Neuron(id=nid, label=nid, initial_spikes=spikes, rules=rules)

    for s_el in root.findall(".//synapse"):
        src = s_el.attrib.get("source")
        tgt = s_el.attrib.get("target")
        if src and tgt:
            synapses.append(Synapse(source=src, target=tgt))

    for syn in synapses:
        neurons.setdefault(syn.source, Neuron(id=syn.source, label=syn.source))
        neurons.setdefault(syn.target, Neuron(id=syn.target, label=syn.target))

    if input_neuron and input_neuron in neurons:
        neurons[input_neuron].is_input = True
    if output_neuron and output_neuron in neurons:
        neurons[output_neuron].is_output = True

    return SNSystem(
        neurons=list(neurons.values()),
        synapses=synapses,
        input_neuron=input_neuron,
        output_neuron=output_neuron,
        raw_source=Path(xml_path).read_text(encoding="utf-8"),
        compilation_status="compiled_xml",
    )
