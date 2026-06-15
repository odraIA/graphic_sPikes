from src.graph_builder import build_nx_graph
from src.models import Neuron, SNSystem, SpikingRule, Synapse


def test_build_nx_graph_metadata_and_direction() -> None:
    system = SNSystem(neurons=[Neuron(id="n1", label="n1", is_input=True, rules=[SpikingRule(id="r", raw="a -> l", rule_type="forgetting")]), Neuron(id="n2", label="n2", is_output=True)], synapses=[Synapse(source="n1", target="n2")])
    g = build_nx_graph(system)
    assert g.number_of_nodes() == 2
    assert g.number_of_edges() == 1
    assert g.has_edge("n1", "n2") and not g.has_edge("n2", "n1")
    assert g.nodes["n1"]["is_input"] is True
    assert g.nodes["n2"]["is_output"] is True
    assert "tooltip" in g.nodes["n1"] and g.nodes["n1"]["rules"]
