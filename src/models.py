from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SpikingRule(BaseModel):
    id: str
    raw: str
    regex: str | None = None
    consumed_spikes: int | None = None
    produced_spikes: int | None = None
    delay: int | None = None
    rule_type: Literal["firing", "forgetting", "unknown"] = "unknown"


class Neuron(BaseModel):
    id: str
    label: str
    initial_spikes: int = 0
    rules: list[SpikingRule] = Field(default_factory=list)
    is_input: bool = False
    is_output: bool = False


class Synapse(BaseModel):
    source: str
    target: str


class SNSystem(BaseModel):
    neurons: list[Neuron] = Field(default_factory=list)
    synapses: list[Synapse] = Field(default_factory=list)
    input_neuron: str | None = None
    output_neuron: str | None = None
    raw_source: str = ""
    compilation_status: str = "not_compiled"


class CompilationResult(BaseModel):
    success: bool
    stdout: str
    stderr: str
    return_code: int
    input_path: str
    output_xml_path: str


class SimulationResult(BaseModel):
    success: bool
    stdout: str
    stderr: str
    return_code: int
    report_path: str | None = None
    step_rows: list[dict] = Field(default_factory=list)
    spike_train: str | None = None
