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
                output_xml_path=str(output_path),
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
                output_xml_path=str(output_path),
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
                output_xml_path=str(output_path),
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
            output_xml_path=str(output_path),
            command=cmd,
        )
