from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import CompilationResult


class CompilerService:
    def __init__(self, plingua_cmd: str = "plingua") -> None:
        self.plingua_cmd = plingua_cmd

    def executable_path(self) -> str | None:
        return shutil.which(self.plingua_cmd)

    def is_available(self) -> bool:
        return self.executable_path() is not None

    def compile_to_xml(self, pli_source: str, timeout_ms: int = 5000) -> CompilationResult:
        workdir = Path(tempfile.mkdtemp(prefix="snps_comp_"))
        input_path = workdir / "input.pli"
        output_path = workdir / "output.xml"
        input_path.write_text(pli_source, encoding="utf-8")
        cmd = [self.plingua_cmd, str(input_path), "-output_format", "xml", str(output_path)]

        if not self.is_available():
            return CompilationResult(False, "", "No se encontró P-Lingua. Configura PLINGUA_CMD o revisa la instalación.", 127, str(input_path), str(output_path), command=cmd)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_ms / 1000)
        except subprocess.TimeoutExpired as exc:
            return CompilationResult(False, exc.stdout or "", (exc.stderr or "") + "\nCompilación agotó el tiempo de espera.", 124, str(input_path), str(output_path), timed_out=True, command=cmd)
        except OSError as exc:
            return CompilationResult(False, "", f"Error al ejecutar P-Lingua: {exc}", 126, str(input_path), str(output_path), command=cmd)

        xml_exists = output_path.exists()
        stderr = proc.stderr
        if proc.returncode == 0 and not xml_exists:
            stderr = (stderr + "\n" if stderr else "") + "La compilación terminó con código 0, pero no se generó XML."
        return CompilationResult(proc.returncode == 0 and xml_exists, proc.stdout, stderr, proc.returncode, str(input_path), str(output_path), command=cmd)
