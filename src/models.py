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
    warnings: list[str] = Field(default_factory=list)
    recognized_blocks: list[str] = Field(default_factory=list)
    ignored_blocks: list[str] = Field(default_factory=list)


class CompilationResult(BaseModel):
    success: bool
    stdout: str
    stderr: str
    return_code: int
    input_path: str
    output_path: str
    output_format: str
    timed_out: bool = False
    command: list[str] = Field(default_factory=list)


class SimulationResult(BaseModel):
    success: bool
    stdout: str
    stderr: str
    return_code: int
    report_path: str | None = None

    step_rows: list[dict] = Field(default_factory=list)
    spike_train: str | None = None

    environment: str | None = None
    environment_spikes: int | None = None
    executed_steps: int | None = None
    elapsed_seconds: float | None = None
    halted: bool | None = None

    timed_out: bool = False
    parse_warnings: list[str] = Field(default_factory=list)
    command: list[str] = Field(default_factory=list)
