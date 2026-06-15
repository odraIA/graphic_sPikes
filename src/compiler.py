from __future__ import annotations

import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import CompilationResult

OFFICIAL_PLINGUA_HINT = (
    "El backend oficial espera sintaxis P-Lingua, por ejemplo "
    "`@model <spiking_psystems>`. Los ejemplos simples del proyecto son para "
    "el parser parcial y pueden no compilar con pLinguaCore."
)


class LegacyPlinguaSourceError(ValueError):
    def __init__(self, line: int, column: int, char: str) -> None:
        self.line = line
        self.column = column
        self.char = char
        super().__init__(
            f"Carácter no ASCII en código real para pLinguaCore antiguo: "
            f"línea {line}, columna {column}, carácter {char!r}."
        )


def _strip_line_comment(line: str) -> str:
    in_string = False
    escaped = False
    out: list[str] = []
    i = 0
    while i < len(line):
        ch = line[i]
        nxt = line[i + 1] if i + 1 < len(line) else ""
        if ch == "\\" and in_string and not escaped:
            escaped = True
            out.append(ch)
            i += 1
            continue
        if ch == '"' and not escaped:
            in_string = not in_string
        if ch == "/" and nxt == "/" and not in_string:
            break
        out.append(ch)
        escaped = False
        i += 1
    return "".join(out)


def prepare_source_for_legacy_plingua(text: str) -> str:
    lines = [_strip_line_comment(line) for line in text.splitlines()]
    prepared = "\n".join(lines)
    for line_no, line in enumerate(prepared.splitlines(), 1):
        for col_no, char in enumerate(line, 1):
            if ord(char) > 127:
                raise LegacyPlinguaSourceError(line_no, col_no, char)
    return prepared


def _contains_fatal_plingua_error(text: str) -> bool:
    fatal_markers = [
        "Parser process finished with errors",
        "Exception in thread \"main\"",
        "Lexical error",
        "LexicalError",
        "Syntactic error",
        "Syntax error",
    ]
    lowered = text.lower()
    if "lexical" in lowered and "error" in lowered:
        return True
    if "syntactic" in lowered and "error" in lowered:
        return True
    return any(marker in text for marker in fatal_markers)


class CompilerService:
    def __init__(self, plingua_cmd: str = "plingua") -> None:
        self.plingua_cmd = plingua_cmd

    def command_parts(self) -> list[str]:
        return shlex.split(self.plingua_cmd)

    def executable_path(self) -> str | None:
        parts = self.command_parts()
        return shutil.which(parts[0]) if parts else None

    def is_available(self) -> bool:
        return self.executable_path() is not None

    def compile_to_xml(
        self, pli_source: str, timeout_ms: int = 5000
    ) -> CompilationResult:
        workdir = Path(tempfile.mkdtemp(prefix="snps_comp_"))
        input_path = workdir / "input.pli"
        output_path = workdir / "output.xml"
        input_path.write_text(pli_source, encoding="utf-8")
        cmd = self.command_parts() + [str(input_path), "-xml", str(output_path)]

        if not self.is_available():
            return CompilationResult(
                success=False,
                stdout="",
                stderr="No se encontró P-Lingua. Configura PLINGUA_CMD o revisa la instalación.",
                return_code=127,
                input_path=str(input_path),
                output_path=str(output_path),
                output_format="xml",
                command=cmd,
            )
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout_ms / 1000
            )
        except subprocess.TimeoutExpired as exc:
            return CompilationResult(
                success=False,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + "\nCompilación agotó el tiempo de espera.",
                return_code=124,
                input_path=str(input_path),
                output_path=str(output_path),
                output_format="xml",
                timed_out=True,
                command=cmd,
            )
        except OSError as exc:
            return CompilationResult(
                success=False,
                stdout="",
                stderr=f"Error al ejecutar P-Lingua: {exc}",
                return_code=126,
                input_path=str(input_path),
                output_path=str(output_path),
                output_format="xml",
                command=cmd,
            )

        xml_exists = output_path.exists()
        stderr = proc.stderr
        if not xml_exists:
            details = []
            if stderr:
                details.append(stderr)
            if proc.stdout:
                details.append(proc.stdout)
            details.append(
                "La compilación no generó XML aunque el proceso pueda devolver código 0."
            )
            if "@model" not in pli_source:
                details.append(OFFICIAL_PLINGUA_HINT)
            stderr = "\n".join(details)
        return CompilationResult(
            success=proc.returncode == 0 and xml_exists,
            stdout=proc.stdout,
            stderr=stderr,
            return_code=proc.returncode,
            input_path=str(input_path),
            output_path=str(output_path),
            output_format="xml",
            command=cmd,
        )

    def compile_official_spiking(
        self, pli_source: str, timeout_ms: int = 5000
    ) -> CompilationResult:
        workdir = Path(tempfile.mkdtemp(prefix="snps_comp_"))
        input_path = workdir / "input.pli"
        output_path = workdir / "output.bin"
        cmd = self.command_parts() + [
            str(input_path),
            "-bin",
            str(output_path),
            "-v",
            "5",
        ]

        try:
            input_path.write_text(
                prepare_source_for_legacy_plingua(pli_source), encoding="utf-8"
            )
        except LegacyPlinguaSourceError as exc:
            return CompilationResult(
                success=False,
                stdout="",
                stderr=str(exc),
                return_code=125,
                input_path=str(input_path),
                output_path=str(output_path),
                output_format="bin",
                command=cmd,
            )

        if not self.is_available():
            return CompilationResult(
                success=False,
                stdout="",
                stderr="No se encontró P-Lingua. Configura PLINGUA_CMD o revisa la instalación.",
                return_code=127,
                input_path=str(input_path),
                output_path=str(output_path),
                output_format="bin",
                command=cmd,
            )
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout_ms / 1000
            )
        except subprocess.TimeoutExpired as exc:
            return CompilationResult(
                success=False,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + "\nCompilación agotó el tiempo de espera.",
                return_code=124,
                input_path=str(input_path),
                output_path=str(output_path),
                output_format="bin",
                timed_out=True,
                command=cmd,
            )
        except OSError as exc:
            return CompilationResult(
                success=False,
                stdout="",
                stderr=f"Error al ejecutar P-Lingua: {exc}",
                return_code=126,
                input_path=str(input_path),
                output_path=str(output_path),
                output_format="bin",
                command=cmd,
            )

        combined = "\n".join(part for part in [proc.stdout, proc.stderr] if part)
        bin_exists = output_path.exists()
        has_fatal = _contains_fatal_plingua_error(combined)
        stderr = proc.stderr
        if not bin_exists:
            details = []
            if stderr:
                details.append(stderr)
            if proc.stdout:
                details.append(proc.stdout)
            details.append("La compilación no generó el artefacto BIN esperado.")
            stderr = "\n".join(details)
        elif has_fatal:
            details = []
            if stderr:
                details.append(stderr)
            if proc.stdout:
                details.append(proc.stdout)
            details.append("pLinguaCore reportó un error fatal durante la compilación.")
            stderr = "\n".join(details)

        return CompilationResult(
            success=proc.returncode == 0 and bin_exists and not has_fatal,
            stdout=proc.stdout,
            stderr=stderr,
            return_code=proc.returncode,
            input_path=str(input_path),
            output_path=str(output_path),
            output_format="bin",
            command=cmd,
        )
