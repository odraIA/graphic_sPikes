from unittest.mock import patch
import subprocess

from src.simulator import SimulationService, parse_simulation_report


class DummyProc:
    returncode = 0
    stdout = "step 0: 1\nstep 1: 0\n"
    stderr = ""


@patch("src.simulator.shutil.which", return_value=None)
def test_simulator_missing(_) -> None:
    r = SimulationService("sim").run("x", 2, 1000)
    assert r.return_code == 127


@patch("src.simulator.shutil.which", return_value="/usr/bin/sim")
@patch("src.simulator.subprocess.run", return_value=DummyProc())
def test_simulator_success(mock_run, _) -> None:
    r = SimulationService("sim").run("x", 2, 1000)
    assert r.success and r.spike_train == "10" and len(r.step_rows) == 2


@patch("src.simulator.shutil.which", return_value="/usr/bin/sim")
@patch("src.simulator.subprocess.run", side_effect=subprocess.TimeoutExpired(["sim"], 1))
def test_simulator_timeout(mock_run, _) -> None:
    r = SimulationService("sim").run("x", 2, 1)
    assert r.return_code == 124 and r.timed_out


def test_report_recognized_and_unrecognized() -> None:
    rows, train, warnings = parse_simulation_report("spike train: 1,0,1")
    assert train == "101" and not warnings
    rows, train, warnings = parse_simulation_report("formato raro")
    assert warnings and rows == [] and train is None
