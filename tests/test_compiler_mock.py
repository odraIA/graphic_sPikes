from unittest.mock import patch

from src.compiler import CompilerService


class DummyProc:
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.stdout = "ok"
        self.stderr = ""


@patch("src.compiler.shutil.which", return_value="/usr/bin/plingua")
@patch("src.compiler.subprocess.run", return_value=DummyProc(0))
def test_compiler_success(mock_run, mock_which) -> None:
    service = CompilerService("plingua")
    result = service.compile_to_xml("neuron n1: 1 {a^1 -> λ};")
    assert result.return_code == 0
    assert result.success is False  # no xml generated in mocked run


@patch("src.compiler.shutil.which", return_value=None)
def test_compiler_missing_command(mock_which) -> None:
    service = CompilerService("plingua")
    result = service.compile_to_xml("x")
    assert result.return_code == 127
    assert "No se encontró P-Lingua" in result.stderr
