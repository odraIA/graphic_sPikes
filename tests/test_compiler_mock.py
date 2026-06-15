from pathlib import Path
from unittest.mock import patch
import subprocess

from src.compiler import CompilerService


class DummyProc:
    def __init__(self, returncode: int = 0, stdout: str = "ok", stderr: str = "") -> None:
        self.returncode = returncode; self.stdout = stdout; self.stderr = stderr


@patch("src.compiler.shutil.which", return_value=None)
def test_compiler_missing_command(_) -> None:
    result = CompilerService("plingua").compile_to_xml("x")
    assert result.return_code == 127 and not result.success


@patch("src.compiler.shutil.which", return_value="/usr/bin/plingua")
def test_compiler_success_with_xml(_, tmp_path) -> None:
    def fake_run(cmd, **kwargs):
        Path(cmd[-1]).write_text("<root />", encoding="utf-8")
        return DummyProc(0)
    with patch("src.compiler.subprocess.run", side_effect=fake_run):
        result = CompilerService("plingua").compile_to_xml("x")
    assert result.success and Path(result.output_xml_path).exists()


@patch("src.compiler.shutil.which", return_value="/usr/bin/plingua")
@patch("src.compiler.subprocess.run", return_value=DummyProc(2, stderr="bad"))
def test_compiler_nonzero(mock_run, _) -> None:
    result = CompilerService("plingua").compile_to_xml("x")
    assert not result.success and result.return_code == 2


@patch("src.compiler.shutil.which", return_value="/usr/bin/plingua")
@patch("src.compiler.subprocess.run", return_value=DummyProc(0))
def test_compiler_zero_without_xml(mock_run, _) -> None:
    result = CompilerService("plingua").compile_to_xml("x")
    assert not result.success and "no se generó XML" in result.stderr


@patch("src.compiler.shutil.which", return_value="/usr/bin/plingua")
@patch("src.compiler.subprocess.run", side_effect=subprocess.TimeoutExpired(["plingua"], 1))
def test_compiler_timeout(mock_run, _) -> None:
    result = CompilerService("plingua").compile_to_xml("x", timeout_ms=1)
    assert result.return_code == 124 and result.timed_out


@patch("src.compiler.shutil.which", return_value="/usr/bin/plingua")
@patch("src.compiler.subprocess.run", side_effect=OSError("boom"))
def test_compiler_oserror(mock_run, _) -> None:
    result = CompilerService("plingua").compile_to_xml("x")
    assert result.return_code == 126 and "boom" in result.stderr
