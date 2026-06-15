from src.plingua_dialect import (
    looks_like_official_plingua,
    looks_like_official_spiking,
)


def test_detects_official_plingua_model_header() -> None:
    assert looks_like_official_plingua("@model <spiking_psystems>\ndef MAIN() {}")
    assert looks_like_official_plingua("/* comment */\n@MODEL <spiking_psystems>")
    assert looks_like_official_spiking("@model <spiking_psystems>\ndef MAIN() {}")
    assert not looks_like_official_spiking("@model <cell_like_psystems>")


def test_partial_parser_syntax_is_not_official_plingua() -> None:
    assert not looks_like_official_plingua("""
        input: n1;
        neuron n1: 2 { a*/a -> a^2 ; 0 };
        """)
