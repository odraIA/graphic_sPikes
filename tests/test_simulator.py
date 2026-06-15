from unittest.mock import patch
import subprocess

from src.simulator import (
    SimulationService,
    parse_simulation_report,
    run_internal_simulation,
)


class DummyProc:
    def __init__(
        self,
        returncode: int = 0,
        stdout: str = "step 0: 1\nstep 1: 0\n",
        stderr: str = "",
    ) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


@patch("src.simulator.shutil.which", return_value=None)
def test_simulator_missing(_) -> None:
    r = SimulationService("sim").run("x", 2, 1000)
    assert r.return_code == 127


@patch("src.simulator.shutil.which", return_value="/usr/bin/sim")
@patch("src.simulator.subprocess.run", return_value=DummyProc())
def test_simulator_success(mock_run, _) -> None:
    r = SimulationService("sim").run("x", 2, 1000)
    assert r.success and r.spike_train == "10" and len(r.step_rows) == 2
    assert "-pli" in r.command and "-st" in r.command and "-o" in r.command


@patch("src.simulator.shutil.which", return_value="/usr/bin/sim")
@patch(
    "src.simulator.subprocess.run",
    return_value=DummyProc(
        stdout="Syntactic error\nParser process finished with errors"
    ),
)
def test_simulator_parse_error_with_zero_return_code(mock_run, _) -> None:
    r = SimulationService("sim").run("x", 2, 1000)
    assert not r.success
    assert r.parse_warnings


@patch("src.simulator.shutil.which", return_value="/usr/bin/java")
def test_simulator_command_with_arguments(_) -> None:
    service = SimulationService(
        "java -cp tools/plingua/MeCoGUI.jar org.gcn.App plingua_sim"
    )
    assert service.executable_path() == "/usr/bin/java"
    assert service.command_parts()[:2] == ["java", "-cp"]


@patch("src.simulator.shutil.which", return_value="/usr/bin/sim")
@patch(
    "src.simulator.subprocess.run", side_effect=subprocess.TimeoutExpired(["sim"], 1)
)
def test_simulator_timeout(mock_run, _) -> None:
    r = SimulationService("sim").run("x", 2, 1)
    assert r.return_code == 124 and r.timed_out


def test_report_recognized_and_unrecognized() -> None:
    rows, train, warnings = parse_simulation_report("spike train: 1,0,1")
    assert train == "101" and not warnings
    rows, train, warnings = parse_simulation_report("formato raro")
    assert warnings and rows == [] and train is None


def test_internal_simulation_fallback() -> None:
    result = run_internal_simulation(
        """
        input: n1;
        output: n1;
        neuron n1: 1 { a/a -> a ; 0 };
        """,
        3,
    )
    assert result.success
    assert result.command == ["internal-simulator"]
    assert result.spike_train == "100"
