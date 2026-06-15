from __future__ import annotations

import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import SNSystem, SimulationResult, SpikingRule
from .parser_pli import parse_pli_text


def parse_simulation_report(
    report_text: str,
) -> tuple[list[dict], str | None, list[str]]:
    rows: list[dict] = []
    for line in report_text.splitlines():
        clean = line.strip()
        m = re.match(r"step\s+(\d+)\s*:\s*(\d)", clean, re.IGNORECASE) or re.match(
            r"(?:t|step)\s*=\s*(\d+).*?(?:output|spike)\s*=\s*(\d)",
            clean,
            re.IGNORECASE,
        )
        if m:
            rows.append({"step": int(m.group(1)), "output_spike": int(m.group(2))})
    train_match = re.search(
        r"spike\s*train\s*[:=]\s*([01\s,]+)", report_text, re.IGNORECASE
    )
    spike_train = None
    if train_match:
        spike_train = "".join(re.findall(r"[01]", train_match.group(1)))
    elif rows:
        spike_train = "".join(str(r["output_spike"]) for r in rows)
    warnings = (
        []
        if rows or spike_train or not report_text.strip()
        else [
            "No se pudo interpretar el reporte de simulación con las expresiones heurísticas actuales."
        ]
    )
    return rows, spike_train, warnings


class SimulationService:
    def __init__(self, sim_cmd: str = "plingua_sim") -> None:
        self.sim_cmd = sim_cmd

    def command_parts(self) -> list[str]:
        return shlex.split(self.sim_cmd)

    def executable_path(self) -> str | None:
        parts = self.command_parts()
        return shutil.which(parts[0]) if parts else None

    def is_available(self) -> bool:
        return self.executable_path() is not None

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
        return self.run_input_file(
            input_path,
            max_steps,
            timeout_ms,
            simulator_mode,
            allow_alternative_steps,
            allow_backwards,
            input_format="-pli",
        )

    def run_input_file(
        self,
        input_path: Path,
        max_steps: int,
        timeout_ms: int,
        simulator_mode: str | None = None,
        allow_alternative_steps: bool = False,
        allow_backwards: bool = False,
        input_format: str | None = None,
    ) -> SimulationResult:
        workdir = input_path.parent
        report_path = workdir / "simulation_report.txt"
        cmd = self.command_parts()
        if input_format:
            cmd.append(input_format)
        cmd += [
            str(input_path),
            "-o",
            str(report_path),
            "-to",
            str(timeout_ms),
            "-st",
            str(max_steps),
        ]
        if simulator_mode:
            cmd += ["-mode", simulator_mode]
        if allow_alternative_steps:
            cmd.append("-a")
        if allow_backwards:
            cmd.append("-b")
        if not self.is_available():
            return SimulationResult(
                success=False,
                stdout="",
                stderr="No se encontró simulador P-Lingua (PLINGUA_SIM_CMD).",
                return_code=127,
                command=cmd,
            )
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout_ms / 1000
            )
        except subprocess.TimeoutExpired as exc:
            return SimulationResult(
                success=False,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + "\nSimulación agotó el tiempo de espera.",
                return_code=124,
                timed_out=True,
                command=cmd,
            )
        except OSError as exc:
            return SimulationResult(
                success=False,
                stdout="",
                stderr=f"Error al ejecutar el simulador P-Lingua: {exc}",
                return_code=126,
                command=cmd,
            )
        report_text = (
            report_path.read_text(encoding="utf-8")
            if report_path.exists()
            else proc.stdout
        )
        rows, spike_train, warnings = parse_simulation_report(report_text)
        success = (
            proc.returncode == 0
            and "Syntactic error" not in proc.stdout
            and "Parser process finished with errors" not in proc.stdout
        )
        if proc.returncode == 0 and not success:
            warnings.append(
                "El simulador externo devolvió código 0, pero pLinguaCore reportó errores de parseo."
            )
        return SimulationResult(
            success=success,
            stdout=proc.stdout,
            stderr=proc.stderr,
            return_code=proc.returncode,
            report_path=str(report_path) if report_path.exists() else None,
            step_rows=rows,
            spike_train=spike_train,
            parse_warnings=warnings,
            command=cmd,
        )


def _rule_applies(rule: SpikingRule, spikes: int, warnings: list[str]) -> bool:
    consumed = rule.consumed_spikes or 0
    if rule.rule_type not in {"firing", "forgetting"} or spikes < consumed:
        return False
    if not rule.regex:
        return True
    try:
        return re.fullmatch(rule.regex, "a" * spikes) is not None
    except re.error as exc:
        warnings.append(f"Regex no soportada en simulador interno ({rule.raw}): {exc}")
        return False


def _select_rule(
    rules: list[SpikingRule], spikes: int, warnings: list[str]
) -> SpikingRule | None:
    for rule in rules:
        if _rule_applies(rule, spikes, warnings):
            return rule
    return None


def run_internal_simulation(pli_source: str, max_steps: int) -> SimulationResult:
    system: SNSystem = parse_pli_text(pli_source)
    spikes = {neuron.id: neuron.initial_spikes for neuron in system.neurons}
    outgoing = {
        neuron.id: [syn.target for syn in system.synapses if syn.source == neuron.id]
        for neuron in system.neurons
    }
    pending: list[tuple[int, str, int]] = []
    rows: list[dict] = []
    warnings = list(system.warnings)
    stdout_lines = [
        "Simulación interna parcial para el subconjunto reconocido por el parser."
    ]

    for step in range(max_steps):
        due = [item for item in pending if item[0] == step]
        pending = [item for item in pending if item[0] != step]
        for _, target, count in due:
            spikes[target] = spikes.get(target, 0) + count

        selected: dict[str, SpikingRule] = {}
        for neuron in system.neurons:
            rule = _select_rule(neuron.rules, spikes.get(neuron.id, 0), warnings)
            if rule:
                selected[neuron.id] = rule

        output_spikes = 0
        for neuron in system.neurons:
            rule = selected.get(neuron.id)
            if not rule:
                continue
            consumed = rule.consumed_spikes or 0
            spikes[neuron.id] = max(0, spikes.get(neuron.id, 0) - consumed)
            if rule.rule_type != "firing":
                continue
            produced = rule.produced_spikes or 0
            if neuron.id == system.output_neuron or neuron.is_output:
                output_spikes += produced
            for target in outgoing.get(neuron.id, []):
                pending.append((step + (rule.delay or 0) + 1, target, produced))

        output_spike = 1 if output_spikes > 0 else 0
        rows.append({"step": step, "output_spike": output_spike})
        stdout_lines.append(f"step {step}: {output_spike}")

    spike_train = "".join(str(row["output_spike"]) for row in rows)
    stdout_lines.append(f"spike train: {','.join(spike_train)}")
    warnings.append(
        "Simulación interna parcial: no sustituye al simulador P-Lingua oficial."
    )
    return SimulationResult(
        success=True,
        stdout="\n".join(stdout_lines),
        stderr="",
        return_code=0,
        step_rows=rows,
        spike_train=spike_train,
        parse_warnings=warnings,
        command=["internal-simulator"],
    )
