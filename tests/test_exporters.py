from src.exporters import graph_html_text, rules_csv_text, system_json_text
from src.graph_builder import build_nx_graph
from src.models import Neuron, SNSystem, SpikingRule


def test_export_texts() -> None:
    s = SNSystem(neurons=[Neuron(id="n1", label="n1", rules=[SpikingRule(id="r", raw="a -> l", rule_type="forgetting")])])
    csv = rules_csv_text(s)
    assert "neuron_id" in csv and "n1" in csv
    html = graph_html_text(build_nx_graph(s))
    assert "<html" in html and "n1" in html
    js = system_json_text(s)
    assert '"neurons"' in js
