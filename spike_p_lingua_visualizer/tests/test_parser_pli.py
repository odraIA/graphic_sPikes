from src.parser_pli import parse_rule


def test_parse_firing_rule() -> None:
    r = parse_rule("a+/a^2 -> a^1 ; 3", "r1")
    assert r.rule_type == "firing"
    assert r.regex == "a+"
    assert r.consumed_spikes == 2
    assert r.produced_spikes == 1
    assert r.delay == 3


def test_parse_forgetting_rule() -> None:
    r = parse_rule("a^4 -> λ", "r2")
    assert r.rule_type == "forgetting"
    assert r.consumed_spikes == 4
    assert r.produced_spikes == 0
