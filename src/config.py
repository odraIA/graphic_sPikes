from __future__ import annotations

import json
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ViewConfig(BaseModel):
    show_editor: bool = True
    show_graph: bool = True
    show_xml: bool = True
    show_rules_table: bool = True
    show_simulation_table: bool = True
    show_spike_train: bool = True


class AppConfig(BaseModel):
    plingua_cmd: str = Field(default_factory=lambda: os.getenv("PLINGUA_CMD", "plingua"))
    plingua_sim_cmd: str = Field(default_factory=lambda: os.getenv("PLINGUA_SIM_CMD", "plingua_sim"))
    max_steps: int = 50
    timeout_ms: int = 5000
    simulator_mode: str | None = None
    allow_alternative_steps: bool = False
    allow_backwards: bool = False
    views: ViewConfig = Field(default_factory=ViewConfig)


def load_config(path: str | Path) -> AppConfig:
    content = Path(path).read_text(encoding="utf-8")
    if str(path).endswith(".json"):
        return AppConfig.model_validate(json.loads(content))
    return AppConfig.model_validate(yaml.safe_load(content))


def save_config(config: AppConfig, path: str | Path) -> None:
    path_obj = Path(path)
    if str(path).endswith(".json"):
        path_obj.write_text(json.dumps(config.model_dump(), indent=2), encoding="utf-8")
    else:
        path_obj.write_text(yaml.safe_dump(config.model_dump(), sort_keys=False), encoding="utf-8")
