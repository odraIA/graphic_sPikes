from src.parser_official_spiking import (
    is_official_spiking_pli,
    parse_official_spiking_pli,
)


OFFICIAL_SPIKING_SOURCE = """
@model<spiking_psystems>

def main()
{
    call spiking_init_conf();
    call spiking_rules();
}

def spiking_init_conf()
{
    @mu = 1,2,3,4,5;

    @ms(1) = a;

    @marcs = (1,3), (1,4), (1,5);
    @marcs += (2,1), (3,1);
    @marcs += (4,2), (5,2);
    @marcs += (4,3), (5,3);
    @marcs += (4,5), (5,4);

    @mout = 1;

    @moutres_binary;
}

def spiking_rules()
{
    [a --> a]'1;
    [a*2 --> #]'1;

    [a*4 --> a]'2;
    [a*3 --> a]'2 "a{4}";

    [a*4 --> a]'3;
    [a --> #]'3;

    [a --> a]'4;
    [a --> a]'5;
}
"""


def _neuron(system, neuron_id: str):
    return next(n for n in system.neurons if n.id == neuron_id)


def test_detects_official_spiking_model() -> None:
    assert is_official_spiking_pli(OFFICIAL_SPIKING_SOURCE)
    assert not is_official_spiking_pli("@model<cell_like_psystems>")


def test_parse_reference_official_spiking_file() -> None:
    system = parse_official_spiking_pli(OFFICIAL_SPIKING_SOURCE)

    assert len(system.neurons) == 5
    assert len(system.synapses) == 11
    assert _neuron(system, "1").initial_spikes == 1
    assert system.output_neuron == "1"
    assert system.input_neuron is None
    assert _neuron(system, "1").is_output

    assert len(_neuron(system, "1").rules) == 2
    assert len(_neuron(system, "2").rules) == 2
    assert len(_neuron(system, "3").rules) == 2
    assert len(_neuron(system, "4").rules) == 1
    assert len(_neuron(system, "5").rules) == 1

    first = _neuron(system, "1").rules[0]
    assert first.rule_type == "firing"
    assert first.consumed_spikes == 1
    assert first.produced_spikes == 1
    assert first.delay == 0

    forgetting = _neuron(system, "1").rules[1]
    assert forgetting.rule_type == "forgetting"
    assert forgetting.consumed_spikes == 2
    assert forgetting.produced_spikes == 0

    regex_rule = _neuron(system, "2").rules[1]
    assert regex_rule.rule_type == "firing"
    assert regex_rule.consumed_spikes == 3
    assert regex_rule.produced_spikes == 1
    assert regex_rule.regex == "a{4}"
    assert "[a*3 --> a]'2" in regex_rule.raw


def test_unknown_official_rule_is_preserved_with_warning() -> None:
    system = parse_official_spiking_pli(
        """
        @model<spiking_psystems>
        @mu = 1;
        [a+ --> a]'1;
        """
    )
    rule = _neuron(system, "1").rules[0]
    assert rule.rule_type == "unknown"
    assert rule.raw == "[a+ --> a]'1;"
    assert system.warnings
