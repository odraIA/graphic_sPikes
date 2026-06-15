from pathlib import Path
from unittest.mock import patch
import subprocess

import pytest

from src.compiler import (
    CompilerService,
    LegacyPlinguaSourceError,
    prepare_source_for_legacy_plingua,
)


class DummyProc:
    def __init__(
        self, returncode: int = 0, stdout: str = "ok", stderr: str = ""
    ) -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


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
    assert result.success and Path(result.output_path).exists()
    assert result.output_format == "xml"


@patch("src.compiler.shutil.which", return_value="/usr/bin/plingua")
@patch("src.compiler.subprocess.run", return_value=DummyProc(2, stderr="bad"))
def test_compiler_nonzero(mock_run, _) -> None:
    result = CompilerService("plingua").compile_to_xml("x")
    assert not result.success and result.return_code == 2


@patch("src.compiler.shutil.which", return_value="/usr/bin/plingua")
@patch(
    "src.compiler.subprocess.run", return_value=DummyProc(0, stdout="Syntactic error")
)
def test_compiler_zero_without_xml(mock_run, _) -> None:
    result = CompilerService("plingua").compile_to_xml("x")
    assert not result.success and "no generó XML" in result.stderr
    assert "Syntactic error" in result.stderr
    assert "@model" in result.stderr


@patch("src.compiler.shutil.which", return_value="/usr/bin/plingua")
@patch(
    "src.compiler.subprocess.run", side_effect=subprocess.TimeoutExpired(["plingua"], 1)
)
def test_compiler_timeout(mock_run, _) -> None:
    result = CompilerService("plingua").compile_to_xml("x", timeout_ms=1)
    assert result.return_code == 124 and result.timed_out


@patch("src.compiler.shutil.which", return_value="/usr/bin/plingua")
@patch("src.compiler.subprocess.run", side_effect=OSError("boom"))
def test_compiler_oserror(mock_run, _) -> None:
    result = CompilerService("plingua").compile_to_xml("x")
    assert result.return_code == 126 and "boom" in result.stderr


def test_prepare_source_removes_non_ascii_line_comments_only() -> None:
    prepared = prepare_source_for_legacy_plingua(
        '@model<spiking_psystems>\n// comentario con tildes áéí\n[a --> a]\'1 "a{4}";'
    )
    assert "á" not in prepared
    assert '"a{4}"' in prepared
    assert "[a --> a]'1" in prepared


def test_prepare_source_rejects_non_ascii_in_real_code() -> None:
    with pytest.raises(LegacyPlinguaSourceError) as exc:
        prepare_source_for_legacy_plingua("@ms(ñ) = a; // comentario")
    assert exc.value.line == 1
    assert exc.value.char == "ñ"


@patch("src.compiler.shutil.which", return_value="/usr/bin/plingua")
def test_official_spiking_uses_bin_not_xml(_, tmp_path) -> None:
    def fake_run(cmd, **kwargs):
        assert "-bin" in cmd
        assert "-xml" not in cmd
        Path(cmd[cmd.index("-bin") + 1]).write_bytes(b"bin")
        return DummyProc(0)

    with patch("src.compiler.subprocess.run", side_effect=fake_run):
        result = CompilerService("plingua").compile_official_spiking(
            "@model<spiking_psystems>\n// válido con tilde\n"
        )
    assert result.success
    assert result.output_format == "bin"
    assert result.command[-2:] == ["-v", "5"]


@patch("src.compiler.shutil.which", return_value="/usr/bin/plingua")
def test_official_spiking_detects_parser_finished_with_errors(_) -> None:
    def fake_run(cmd, **kwargs):
        Path(cmd[cmd.index("-bin") + 1]).write_bytes(b"bin")
        return DummyProc(0, stdout="Parser process finished with errors")

    with patch("src.compiler.subprocess.run", side_effect=fake_run):
        result = CompilerService("plingua").compile_official_spiking(
            "@model<spiking_psystems>"
        )
    assert not result.success
    assert "error fatal" in result.stderr


@patch("src.compiler.shutil.which", return_value="/usr/bin/plingua")
def test_official_spiking_ignores_astrocyte_trace_when_bin_exists(_) -> None:
    def fake_run(cmd, **kwargs):
        Path(cmd[cmd.index("-bin") + 1]).write_bytes(b"bin")
        return DummyProc(
            0,
            stderr="java.lang.IllegalArgumentException: Unparsable Expression.\n"
            "at AstrocyteFunction.storeFunction(...)",
        )

    with patch("src.compiler.subprocess.run", side_effect=fake_run):
        result = CompilerService("plingua").compile_official_spiking(
            "@model<spiking_psystems>"
        )
    assert result.success


@patch("src.compiler.shutil.which", return_value="/usr/bin/plingua")
def test_official_spiking_fails_on_exception_in_main_thread(_) -> None:
    def fake_run(cmd, **kwargs):
        Path(cmd[cmd.index("-bin") + 1]).write_bytes(b"bin")
        return DummyProc(
            0,
            stderr='Exception in thread "main" java.lang.ClassCastException',
        )

    with patch("src.compiler.subprocess.run", side_effect=fake_run):
        result = CompilerService("plingua").compile_official_spiking(
            "@model<spiking_psystems>"
        )
    assert not result.success
