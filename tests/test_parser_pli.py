from pathlib import Path

from src.parser_pli import parse_pli_text, parse_rule


def test_parse_firing_rule_with_delay() -> None:
    r = parse_rule("a+/a^2 -> a^1 ; 3", "r1")
    assert (r.rule_type, r.regex, r.consumed_spikes, r.produced_spikes, r.delay) == ("firing", "a+", 2, 1, 3)


def test_parse_firing_rule_without_explicit_exponent() -> None:
    r = parse_rule("a+/a -> a ; 0", "r1")
    assert r.rule_type == "firing" and r.consumed_spikes == 1 and r.produced_spikes == 1


def test_parse_forgetting_lambda_and_l() -> None:
    assert parse_rule("a^4 -> λ", "r").rule_type == "forgetting"
    r = parse_rule("a -> l", "r")
    assert r.rule_type == "forgetting" and r.consumed_spikes == 1


def test_parse_unknown_rule() -> None:
    assert parse_rule("esto no es regla", "r").rule_type == "unknown"


def test_parse_complete_multiline_system_comments_synapses_io() -> None:
    text = """// comentario
    INPUT: n1;
    output: n2;
    neuron n1: 2 {
      a+/a^2 -> a ; 1 | raro
    };
    neuron n2: 0 { a -> λ };
    syn(n1,n2);
    desconocido;
    """
    s = parse_pli_text(text)
    assert len(s.neurons) == 2
    assert len(s.synapses) == 1 and s.synapses[0].source == "n1" and s.synapses[0].target == "n2"
    assert s.input_neuron == "n1" and s.output_neuron == "n2"
    assert any(n.id == "n1" and n.is_input for n in s.neurons)
    assert any(r.rule_type == "unknown" for n in s.neurons for r in n.rules)
    assert s.warnings and s.ignored_blocks


def test_examples_parse() -> None:
    expectations = {"minimal_snps.pli": (1, 0, 1, {"firing"}), "multi_neuron_snps.pli": (3, 3, 5, {"firing", "forgetting"})}
    for name, (neurons, synapses, rules, types) in expectations.items():
        s = parse_pli_text(Path("examples", name).read_text(encoding="utf-8"))
        assert len(s.neurons) == neurons
        assert len(s.synapses) == synapses
        all_rules = [r for n in s.neurons for r in n.rules]
        assert len(all_rules) == rules
        assert {r.rule_type for r in all_rules} == types
        assert s.input_neuron and s.output_neuron
