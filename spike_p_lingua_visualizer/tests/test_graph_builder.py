from src.graph_builder import build_nx_graph
from src.models import Neuron, SNSystem, Synapse


def test_build_nx_graph() -> None:
    system = SNSystem(
        neurons=[Neuron(id="n1", label="n1"), Neuron(id="n2", label="n2")],
        synapses=[Synapse(source="n1", target="n2")],
    )
    g = build_nx_graph(system)
    assert g.number_of_nodes() == 2
    assert g.number_of_edges() == 1
    assert g.has_edge("n1", "n2")
