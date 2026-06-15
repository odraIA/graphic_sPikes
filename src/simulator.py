from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import SimulationResult


def parse_simulation_report(report_text: str) -> tuple[list[dict], str | None, list[str]]:
    rows: list[dict] = []
    for line in report_text.splitlines():
        clean = line.strip()
        m = re.match(r"step\s+(\d+)\s*:\s*(\d)", clean, re.IGNORECASE) or re.match(r"(?:t|step)\s*=\s*(\d+).*?(?:output|spike)\s*=\s*(\d)", clean, re.IGNORECASE)
        if m:
            rows.append({"step": int(m.group(1)), "output_spike": int(m.group(2))})
    train_match = re.search(r"spike\s*train\s*[:=]\s*([01\s,]+)", report_text, re.IGNORECASE)
    spike_train = None
    if train_match:
        spike_train = "".join(re.findall(r"[01]", train_match.group(1)))
    elif rows:
        spike_train = "".join(str(r["output_spike"]) for r in rows)
    warnings = [] if rows or spike_train or not report_text.strip() else ["No se pudo interpretar el reporte de simulación con las expresiones heurísticas actuales."]
    return rows, spike_train, warnings


class SimulationService:
    def __init__(self, sim_cmd: str = "plingua_sim") -> None:
        self.sim_cmd = sim_cmd

    def executable_path(self) -> str | None:
        return shutil.which(self.sim_cmd)

    def is_available(self) -> bool:
        return self.executable_path() is not None

    def run(self, pli_source: str, max_steps: int, timeout_ms: int, simulator_mode: str | None = None, allow_alternative_steps: bool = False, allow_backwards: bool = False) -> SimulationResult:
        workdir = Path(tempfile.mkdtemp(prefix="snps_sim_"))
        input_path = workdir / "input.pli"
        input_path.write_text(pli_source, encoding="utf-8")
        cmd = [self.sim_cmd, str(input_path), "--max-steps", str(max_steps)]
        if simulator_mode:
            cmd += ["--mode", simulator_mode]
        if allow_alternative_steps:
            cmd.append("--allow-alternative-steps")
        if allow_backwards:
            cmd.append("--allow-backwards")
        if not self.is_available():
            return SimulationResult(False, "", "No se encontró simulador P-Lingua (PLINGUA_SIM_CMD).", 127, command=cmd)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_ms / 1000)
        except subprocess.TimeoutExpired as exc:
            return SimulationResult(False, exc.stdout or "", (exc.stderr or "") + "\nSimulación agotó el tiempo de espera.", 124, timed_out=True, command=cmd)
        except OSError as exc:
            return SimulationResult(False, "", f"Error al ejecutar el simulador P-Lingua: {exc}", 126, command=cmd)
        rows, spike_train, warnings = parse_simulation_report(proc.stdout)
        return SimulationResult(proc.returncode == 0, proc.stdout, proc.stderr, proc.returncode, step_rows=rows, spike_train=spike_train, parse_warnings=warnings, command=cmd)
