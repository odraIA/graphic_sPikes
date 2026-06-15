from __future__ import annotations

import re

from .models import Neuron, SNSystem, SpikingRule, Synapse

MODEL_SPIKING_RE = re.compile(
    r"^\s*@model\s*<\s*spiking_psystems\s*>", re.IGNORECASE | re.MULTILINE
)
MU_RE = re.compile(r"@mu\s*=\s*([^;]+);", re.IGNORECASE | re.DOTALL)
MS_RE = re.compile(r"@ms\s*\(\s*([^)]+?)\s*\)\s*=\s*([^;]+);", re.IGNORECASE)
MARCS_RE = re.compile(r"@marcs\s*(?:\+=|=)\s*([^;]+);", re.IGNORECASE | re.DOTALL)
MOUT_RE = re.compile(r"@mout\s*=\s*([^;]+);", re.IGNORECASE)
MIN_RE = re.compile(r"@min\s*=\s*([^;]+);", re.IGNORECASE)
ARC_RE = re.compile(r"\(\s*([^,\s()]+)\s*,\s*([^,\s()]+)\s*\)")
RULE_RE = re.compile(
    r"(?P<raw>\[\s*(?P<body>.*?)\s*\]\s*'\s*(?P<neuron>[A-Za-z0-9_]+)"
    r"(?:\s*\"(?P<regex>[^\"]*)\")?\s*;)",
    re.IGNORECASE | re.DOTALL,
)


def strip_line_comments(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        in_string = False
        escaped = False
        out: list[str] = []
        i = 0
        while i < len(line):
            ch = line[i]
            nxt = line[i + 1] if i + 1 < len(line) else ""
            if ch == "\\" and in_string and not escaped:
                escaped = True
                out.append(ch)
                i += 1
                continue
            if ch == '"' and not escaped:
                in_string = not in_string
            if ch == "/" and nxt == "/" and not in_string:
                break
            out.append(ch)
            escaped = False
            i += 1
        lines.append("".join(out))
    return "\n".join(lines)


def is_official_spiking_pli(text: str) -> bool:
    return MODEL_SPIKING_RE.search(strip_line_comments(text)) is not None


def _split_ids(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _spike_count(expr: str) -> int | None:
    clean = " ".join(expr.strip().split())
    if clean == "#":
        return 0
    if clean == "a":
        return 1
    match = re.fullmatch(r"a\s*(?:\*|\^)\s*(\d+)", clean)
    if match:
        return int(match.group(1))
    return None


def _parse_delay(rhs: str) -> tuple[str, int]:
    match = re.fullmatch(r"(.+?)\s*;\s*(\d+)", rhs.strip(), re.DOTALL)
    if not match:
        return rhs.strip(), 0
    return match.group(1).strip(), int(match.group(2))


def _parse_rule(raw: str, body: str, regex: str | None, rid: str) -> SpikingRule:
    clean_body = " ".join(body.split())
    if "-->" not in clean_body:
        return SpikingRule(id=rid, raw=" ".join(raw.split()), regex=regex, rule_type="unknown")

    lhs, rhs = [part.strip() for part in clean_body.split("-->", 1)]
    rhs, delay = _parse_delay(rhs)
    consumed = _spike_count(lhs)
    produced = _spike_count(rhs)
    rule_raw = " ".join(raw.split())

    if consumed is None or produced is None:
        return SpikingRule(id=rid, raw=rule_raw, regex=regex, delay=delay, rule_type="unknown")
    if rhs == "#":
        return SpikingRule(
            id=rid,
            raw=rule_raw,
            regex=regex,
            consumed_spikes=consumed,
            produced_spikes=0,
            delay=0,
            rule_type="forgetting",
        )
    return SpikingRule(
        id=rid,
        raw=rule_raw,
        regex=regex,
        consumed_spikes=consumed,
        produced_spikes=produced,
        delay=delay,
        rule_type="firing",
    )


def parse_official_spiking_pli(text: str) -> SNSystem:
    source = strip_line_comments(text)
    if not is_official_spiking_pli(source):
        raise ValueError("El texto no declara @model<spiking_psystems>.")

    neuron_map: dict[str, Neuron] = {}
    synapses: list[Synapse] = []
    warnings: list[str] = []
    recognized: list[str] = []
    ignored: list[str] = []

    mu = MU_RE.search(source)
    if mu:
        for neuron_id in _split_ids(mu.group(1)):
            neuron_map[neuron_id] = Neuron(id=neuron_id, label=neuron_id)
        recognized.append("@mu")
    else:
        warnings.append("No se encontró declaración @mu.")

    for match in MS_RE.finditer(source):
        neuron_id = match.group(1).strip()
        count = _spike_count(match.group(2))
        if count is None:
            warnings.append(f"No se pudo interpretar @ms({neuron_id}) = {match.group(2).strip()}.")
            count = 0
        neuron = neuron_map.setdefault(neuron_id, Neuron(id=neuron_id, label=neuron_id))
        neuron.initial_spikes = count
        recognized.append(match.group(0).strip())

    for match in MARCS_RE.finditer(source):
        for source_id, target_id in ARC_RE.findall(match.group(1)):
            synapses.append(Synapse(source=source_id, target=target_id))
            neuron_map.setdefault(source_id, Neuron(id=source_id, label=source_id))
            neuron_map.setdefault(target_id, Neuron(id=target_id, label=target_id))
        recognized.append(match.group(0).strip())

    output_neuron = None
    mout = MOUT_RE.search(source)
    if mout:
        values = _split_ids(mout.group(1))
        output_neuron = values[0] if values else None
        if output_neuron:
            neuron_map.setdefault(
                output_neuron, Neuron(id=output_neuron, label=output_neuron)
            ).is_output = True
            recognized.append(mout.group(0).strip())

    input_neuron = None
    min_match = MIN_RE.search(source)
    if min_match:
        values = _split_ids(min_match.group(1))
        input_neuron = values[0] if values else None
        if input_neuron:
            neuron_map.setdefault(
                input_neuron, Neuron(id=input_neuron, label=input_neuron)
            ).is_input = True
            recognized.append(min_match.group(0).strip())

    rule_counts: dict[str, int] = {}
    for match in RULE_RE.finditer(source):
        neuron_id = match.group("neuron").strip()
        rule_counts[neuron_id] = rule_counts.get(neuron_id, 0) + 1
        rule = _parse_rule(
            match.group("raw"),
            match.group("body"),
            match.group("regex"),
            f"{neuron_id}_r{rule_counts[neuron_id]}",
        )
        if rule.rule_type == "unknown":
            warnings.append(f"Regla oficial no soportada en {neuron_id}: {rule.raw}")
        neuron_map.setdefault(neuron_id, Neuron(id=neuron_id, label=neuron_id)).rules.append(rule)
        recognized.append(rule.raw)

    return SNSystem(
        neurons=list(neuron_map.values()),
        synapses=synapses,
        input_neuron=input_neuron,
        output_neuron=output_neuron,
        raw_source=text,
        compilation_status="parsed_official_spiking",
        warnings=warnings,
        recognized_blocks=recognized,
        ignored_blocks=ignored,
    )
