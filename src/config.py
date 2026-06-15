from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _default_command(env_name: str, bundled_relative_path: str, fallback: str) -> str:
    env_value = os.getenv(env_name)
    if env_value:
        return env_value
    bundled_path = PROJECT_ROOT / bundled_relative_path
    if bundled_path.exists():
        return str(bundled_path)
    return fallback


class ViewConfig(BaseModel):
    show_editor: bool = True
    show_graph: bool = True
    show_xml: bool = True
    show_rules_table: bool = True
    show_simulation_table: bool = True
    show_spike_train: bool = True


class AppConfig(BaseModel):
    plingua_cmd: str = Field(
        default_factory=lambda: _default_command(
            "PLINGUA_CMD", "tools/plingua/plingua", "plingua"
        )
    )
    plingua_sim_cmd: str = Field(
        default_factory=lambda: _default_command(
            "PLINGUA_SIM_CMD", "tools/plingua/plingua_sim", "plingua_sim"
        )
    )
    max_steps: int = 50
    timeout_ms: int = 5000
    compile_timeout_ms: int = 5000
    simulator_mode: str | None = None
    allow_alternative_steps: bool = False
    allow_backwards: bool = False
    views: ViewConfig = Field(default_factory=ViewConfig)


def load_config(path: str | Path) -> tuple[AppConfig, str | None]:
    path_obj = Path(path)
    if not path_obj.exists():
        return AppConfig(), f"No existe el archivo de configuración: {path_obj}"
    try:
        content = path_obj.read_text(encoding="utf-8")
        data: Any = (
            json.loads(content)
            if path_obj.suffix == ".json"
            else yaml.safe_load(content)
        )
        if data is None:
            data = {}
        return AppConfig.model_validate(data), None
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        yaml.YAMLError,
        ValidationError,
    ) as exc:
        return AppConfig(), f"No se pudo cargar la configuración: {exc}"


def save_config(config: AppConfig, path: str | Path) -> tuple[bool, str | None]:
    path_obj = Path(path)
    try:
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        if path_obj.suffix == ".json":
            path_obj.write_text(
                json.dumps(config.model_dump(), indent=2), encoding="utf-8"
            )
        else:
            path_obj.write_text(
                yaml.safe_dump(config.model_dump(), sort_keys=False), encoding="utf-8"
            )
        return True, None
    except OSError as exc:
        return False, f"No se pudo guardar la configuración: {exc}"
