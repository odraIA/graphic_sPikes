from __future__ import annotations

import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import SNSystem, SimulationResult, SpikingRule
from .parser_pli import parse_pli_text


def _parse_environment_spikes(environment: str) -> int | None:
    expression = environment.strip()

    if expression in {"", "0", "{}", "λ"}:
        return 0

    total = 0
    found = False

    # Admite, por ejemplo:
    # a
    # a*2
    # a^2
    # a{2}
    terms = re.split(r"\s*[,+]\s*", expression)

    for term in terms:
        term = term.strip()

        if term.lower() == "a":
            total += 1
            found = True
            continue

        match = re.fullmatch(r"a\s*\*\s*(\d+)", term, re.IGNORECASE)
        if match:
            total += int(match.group(1))
            found = True
            continue

        match = re.fullmatch(r"a\s*\^\s*(\d+)", term, re.IGNORECASE)
        if match:
            total += int(match.group(1))
            found = True
            continue

        match = re.fullmatch(r"a\s*\{\s*(\d+)\s*\}", term, re.IGNORECASE)
        if match:
            total += int(match.group(1))
            found = True

    return total if found else None


def parse_simulation_report_details(
    report_text: str,
) -> tuple[list[dict], str | None, dict, list[str]]:
    rows: list[dict] = []
    warnings: list[str] = []
    summary: dict = {}

    for line in report_text.splitlines():
        clean = line.strip()

        match = re.match(
            r"step\s+(\d+)\s*:\s*(\d)",
            clean,
            re.IGNORECASE,
        )

        if not match:
            match = re.match(
                r"(?:t|step)\s*=\s*(\d+)"
                r".*?(?:output|spike)\s*=\s*(\d)",
                clean,
                re.IGNORECASE,
            )

        if match:
            rows.append(
                {
                    "step": int(match.group(1)),
                    "output_spike": int(match.group(2)),
                }
            )

    train_match = re.search(
        r"spike\s*train\s*[:=]\s*([01\s,]+)",
        report_text,
        re.IGNORECASE,
    )

    spike_train = None

    if train_match:
        spike_train = "".join(
            re.findall(r"[01]", train_match.group(1))
        )
    elif rows:
        spike_train = "".join(
            str(row["output_spike"])
            for row in rows
        )

    environment_match = re.search(
        r"^\s*Environment\s*:\s*(.*?)\s*$",
        report_text,
        re.IGNORECASE | re.MULTILINE,
    )

    if environment_match:
        environment = environment_match.group(1).strip()
        summary["environment"] = environment
        summary["environment_spikes"] = _parse_environment_spikes(
            environment
        )

    steps_match = re.search(
        r"^\s*Steps\s*:\s*(\d+)\s*$",
        report_text,
        re.IGNORECASE | re.MULTILINE,
    )

    if steps_match:
        summary["executed_steps"] = int(steps_match.group(1))

    time_match = re.search(
        r"^\s*Time\s*:\s*([0-9.+\-Ee]+)\s*s\.?\s*$",
        report_text,
        re.IGNORECASE | re.MULTILINE,
    )

    if time_match:
        try:
            summary["elapsed_seconds"] = float(
                time_match.group(1)
            )
        except ValueError:
            warnings.append(
                f"No se pudo interpretar el tiempo: "
                f"{time_match.group(1)}"
            )

    if re.search(
        r"Halting configuration",
        report_text,
        re.IGNORECASE,
    ):
        summary["halted"] = True
    elif re.search(
        r"(?:maximum|max)\s+steps",
        report_text,
        re.IGNORECASE,
    ):
        summary["halted"] = False

    recognized = bool(rows or spike_train or summary)

    if report_text.strip() and not recognized:
        warnings.append(
            "No se pudo interpretar el reporte de simulación "
            "con las expresiones actuales."
        )

    return rows, spike_train, summary, warnings


# Se mantiene esta función para no romper los tests existentes.
def parse_simulation_report(
    report_text: str,
) -> tuple[list[dict], str | None, list[str]]:
    rows, spike_train, _, warnings = (
        parse_simulation_report_details(report_text)
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
        
        report_text = ""

        if report_path.exists():
            report_text = report_path.read_text(
                encoding="utf-8",
                errors="replace",
            )

        summary = parse_plingua_summary(proc.stdout or "")

        rows = parse_plingua_configuration_rows(
            report_text
        )

        spike_train = None

        if rows:
            spike_train = "".join(
                str(row["output_spike"])
                for row in rows
            )
        else:
            rows, spike_train, _ = parse_simulation_report(
                report_text or proc.stdout
            )

        warnings: list[str] = []

        valid_completed_simulation = bool(
            rows
            and summary.get("halted")
            and summary.get("executed_steps") is not None
        )

        hard_parser_error = any(
            marker.lower() in (
                (proc.stdout or "")
                + "\n"
                + (proc.stderr or "")
            ).lower()
            for marker in [
                "Syntactic error",
                "Parser process finished with errors",
            ]
        )

        astrocyte_warning = (
            "AstrocyteFunction.storeFunction"
            in (proc.stderr or "")
            and "Unparsable Expression"
            in (proc.stderr or "")
        )

        if astrocyte_warning and valid_completed_simulation:
            warnings.append(
                "pLinguaCore notificó errores internos al inicializar "
                "funciones de astrocitos, pero el sistema fue construido, "
                "simulado y alcanzó una configuración de parada."
            )

        success = (
            proc.returncode == 0
            and not hard_parser_error
            and (
                not astrocyte_warning
                or valid_completed_simulation
            )
        )

        if not rows:
            warnings.append(
                "No se pudieron reconstruir las configuraciones "
                "de la simulación."
            )

        return SimulationResult(
            success=success,
            stdout=report_text,
            stderr=proc.stderr,
            return_code=proc.returncode,
            report_path=(
                str(report_path)
                if report_path.exists()
                else None
            ),
            step_rows=rows,
            spike_train=spike_train,
            environment=summary.get("environment"),
            environment_spikes=summary.get(
                "environment_spikes"
            ),
            executed_steps=summary.get(
                "executed_steps"
            ),
            elapsed_seconds=summary.get(
                "elapsed_seconds"
            ),
            halted=summary.get("halted"),
            parse_warnings=warnings,
            command=cmd,
        )


def _rule_applies(rule: SpikingRule, spikes: int, warnings: list[str]) -> bool:
    consumed = rule.consumed_spikes or 0

    # Una regla de olvido a^s -> λ solo se aplica si hay exactamente s spikes.
    if rule.rule_type == "forgetting":
        return spikes == consumed

    if rule.rule_type != "firing" or spikes < consumed:
        return False

    if not rule.regex:
        return True

    try:
        return re.fullmatch(rule.regex, "a" * spikes) is not None
    except re.error as exc:
        warnings.append(
            f"Regex no soportada en simulador interno ({rule.raw}): {exc}"
        )
        return False


def _select_rule(
    rules: list[SpikingRule],
    spikes: int,
    warnings: list[str],
    choice_index: int = 0,
) -> SpikingRule | None:
    applicable = [
        rule
        for rule in rules
        if _rule_applies(rule, spikes, warnings)
    ]

    if not applicable:
        return None

    if choice_index < 0 or choice_index >= len(applicable):
        warnings.append(
            f"Elección de regla {choice_index} no válida. "
            "Se utilizará la primera regla aplicable."
        )
        choice_index = 0

    return applicable[choice_index]


def run_internal_simulation_system(
    system: SNSystem,
    max_steps: int,
    rule_choices: dict[tuple[int, str], int] | None = None,
) -> SimulationResult:
    rule_choices = rule_choices or {}

    spikes = {
        neuron.id: neuron.initial_spikes
        for neuron in system.neurons
    }

    outgoing = {
        neuron.id: [
            syn.target
            for syn in system.synapses
            if syn.source == neuron.id
        ]
        for neuron in system.neurons
    }

    # Spikes pendientes hacia otras neuronas:
    # (paso de llegada, neurona destino, cantidad)
    pending: list[tuple[int, str, int]] = []

    # Spikes pendientes de llegar al entorno:
    # (paso de llegada, cantidad)
    output_pending: list[tuple[int, int]] = []

    rows: list[dict] = []
    warnings = list(system.warnings)

    stdout_lines = [
        "Simulación interna parcial para el subconjunto reconocido por el parser."
    ]

    halted = False

    for step in range(max_steps):
        # Llegadas a neuronas en este paso.
        due = [
            item
            for item in pending
            if item[0] == step
        ]

        pending = [
            item
            for item in pending
            if item[0] != step
        ]

        for _, target, count in due:
            spikes[target] = spikes.get(target, 0) + count

        # Llegadas al entorno en este paso.
        output_due = sum(
            count
            for arrival_step, count in output_pending
            if arrival_step == step
        )

        output_pending = [
            item
            for item in output_pending
            if item[0] != step
        ]

        output_spike = 1 if output_due > 0 else 0

        # Selección de reglas.
        selected: dict[str, SpikingRule] = {}

        for neuron in system.neurons:
            choice_index = rule_choices.get(
                (step, neuron.id),
                0,
            )

            rule = _select_rule(
                neuron.rules,
                spikes.get(neuron.id, 0),
                warnings,
                choice_index,
            )

            if rule:
                selected[neuron.id] = rule

        # Guardamos la configuración al comienzo del paso.
        row = {
            "step": step,
            "output_spike": output_spike,
        }

        for neuron in system.neurons:
            row[neuron.id] = spikes.get(neuron.id, 0)

        rows.append(row)

        state_text = ", ".join(
            f"{neuron.id}={spikes.get(neuron.id, 0)}"
            for neuron in system.neurons
        )

        stdout_lines.append(
            f"step {step}: {output_spike} | {state_text}"
        )

        # El sistema se detiene si no hay reglas aplicables
        # ni spikes pendientes de llegar.
        if not selected and not pending and not output_pending:
            stdout_lines.append(f"halt at step {step}")
            halted = True
            break

        # Aplicación paralela de las reglas seleccionadas.
        for neuron in system.neurons:
            rule = selected.get(neuron.id)

            if not rule:
                continue

            consumed = rule.consumed_spikes or 0
            spikes[neuron.id] -= consumed

            if rule.rule_type != "firing":
                continue

            produced = rule.produced_spikes or 0
            arrival_step = step + (rule.delay or 0) + 1

            # La emisión de la neurona de salida llega al entorno
            # en el paso siguiente, no en el mismo paso.
            if neuron.id == system.output_neuron or neuron.is_output:
                output_pending.append(
                    (arrival_step, produced)
                )

            for target in outgoing.get(neuron.id, []):
                pending.append(
                    (arrival_step, target, produced)
                )

    spike_train = "".join(
        str(row["output_spike"])
        for row in rows
    )

    stdout_lines.append(
        f"spike train: {','.join(spike_train)}"
    )

    if not halted:
        warnings.append(
            f"La simulación alcanzó el máximo de {max_steps} pasos "
            "sin detectar una configuración de parada."
        )

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


def run_internal_simulation(
    pli_source: str,
    max_steps: int,
    rule_choices: dict[tuple[int, str], int] | None = None,
) -> SimulationResult:
    system = parse_pli_text(pli_source)

    return run_internal_simulation_system(
        system,
        max_steps,
        rule_choices,
    )


def _multiset_spike_count(expression: str) -> int:
    expression = expression.strip()

    if expression in {"", "#", "0", "λ"}:
        return 0

    if expression == "a":
        return 1

    match = re.fullmatch(
        r"a\s*(?:\*|\^)\s*(\d+)",
        expression,
        re.IGNORECASE,
    )

    if match:
        return int(match.group(1))

    match = re.fullmatch(
        r"a\s*\{\s*(\d+)\s*\}",
        expression,
        re.IGNORECASE,
    )

    if match:
        return int(match.group(1))

    return 0


def parse_plingua_summary(stdout: str) -> dict:
    summary: dict = {}

    environment_match = re.search(
        r"^Environment\s*:\s*(.*?)\s*$",
        stdout,
        re.IGNORECASE | re.MULTILINE,
    )

    if environment_match:
        environment = environment_match.group(1).strip()
        summary["environment"] = environment
        summary["environment_spikes"] = _multiset_spike_count(
            environment
        )

    steps_match = re.search(
        r"^Steps\s*:\s*(\d+)\s*$",
        stdout,
        re.IGNORECASE | re.MULTILINE,
    )

    if steps_match:
        summary["executed_steps"] = int(
            steps_match.group(1)
        )

    time_match = re.search(
        r"^Time\s*:\s*([0-9.+\-Ee]+)\s*s\.?\s*$",
        stdout,
        re.IGNORECASE | re.MULTILINE,
    )

    if time_match:
        summary["elapsed_seconds"] = float(
            time_match.group(1)
        )

    summary["halted"] = bool(
        re.search(
            r"Halting configuration",
            stdout,
            re.IGNORECASE,
        )
    )

    return summary


def parse_plingua_configuration_rows(
    report_text: str,
) -> list[dict]:
    environment_by_step: dict[int, int] = {}

    current_step: int | None = None
    reading_environment = False

    for raw_line in report_text.splitlines():
        line = raw_line.strip()

        configuration_match = re.match(
            r"CONFIGURATION\s*:\s*(\d+)",
            line,
            re.IGNORECASE,
        )

        if configuration_match:
            current_step = int(configuration_match.group(1))
            reading_environment = False
            continue

        if current_step is None:
            continue

        if re.search(
            r"NEURON ID\s*:\s*0.*Label\s*:\s*environment",
            line,
            re.IGNORECASE,
        ):
            reading_environment = True
            continue

        if reading_environment:
            multiset_match = re.match(
                r"Multiset\s*:\s*(.*)",
                line,
                re.IGNORECASE,
            )

            if multiset_match:
                environment_by_step[current_step] = (
                    _multiset_spike_count(
                        multiset_match.group(1)
                    )
                )
                reading_environment = False

        # P-Lingua repite después la misma configuración
        # hasta alcanzar max_steps. Nos quedamos con la primera parada.
        if (
            "Halting configuration" in line
            and environment_by_step
        ):
            break

    rows: list[dict] = []
    previous_environment = 0

    for step in sorted(environment_by_step):
        environment_spikes = environment_by_step[step]

        emitted = max(
            0,
            environment_spikes - previous_environment,
        )

        rows.append(
            {
                "step": step,
                "output_spike": 1 if emitted > 0 else 0,
                "output_count": emitted,
                "environment_spikes": environment_spikes,
            }
        )

        previous_environment = environment_spikes

    return rows