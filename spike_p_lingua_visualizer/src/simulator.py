from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import SimulationResult


class SimulationService:
    def __init__(self, sim_cmd: str = "plingua_sim") -> None:
        self.sim_cmd = sim_cmd

    def run(
        self,
        pli_source: str,
        max_steps: int,
        timeout_ms: int,
        simulator_mode: str | None = None,
        allow_alternative_steps: bool = False,
        allow_backwards: bool = False,
    ) -> SimulationResult:
        workdir = Path(tempfile.mkdtemp(prefix="snps_sim_"))
        input_path = workdir / "input.pli"
        input_path.write_text(pli_source, encoding="utf-8")

        if shutil.which(self.sim_cmd) is None:
            return SimulationResult(success=False, stdout="", stderr="No se encontró simulador P-Lingua (PLINGUA_SIM_CMD).", return_code=127)

        cmd = [self.sim_cmd, str(input_path), "--max-steps", str(max_steps)]
        if simulator_mode:
            cmd += ["--mode", simulator_mode]
        if allow_alternative_steps:
            cmd.append("--allow-alternative-steps")
        if allow_backwards:
            cmd.append("--allow-backwards")

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_ms / 1000)
        except subprocess.TimeoutExpired as exc:
            return SimulationResult(success=False, stdout=exc.stdout or "", stderr="Simulación agotó el tiempo de espera.", return_code=124)

        rows, spike_train = self._parse_report(proc.stdout)
        return SimulationResult(
            success=proc.returncode == 0,
            stdout=proc.stdout,
            stderr=proc.stderr,
            return_code=proc.returncode,
            step_rows=rows,
            spike_train=spike_train,
        )

    def _parse_report(self, report_text: str) -> tuple[list[dict], str | None]:
        rows = []
        for line in report_text.splitlines():
            m = re.match(r"step\s+(\d+)\s*:\s*(\d)", line.strip(), re.IGNORECASE)
            if m:
                rows.append({"step": int(m.group(1)), "output_spike": int(m.group(2))})
        if rows:
            return rows, "".join(str(r["output_spike"]) for r in rows)
        return [], None
