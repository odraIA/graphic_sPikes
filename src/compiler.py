from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import CompilationResult


class CompilerService:
    def __init__(self, plingua_cmd: str = "plingua") -> None:
        self.plingua_cmd = plingua_cmd

    def compile_to_xml(self, pli_source: str) -> CompilationResult:
        workdir = Path(tempfile.mkdtemp(prefix="snps_comp_"))
        input_path = workdir / "input.pli"
        output_path = workdir / "output.xml"
        input_path.write_text(pli_source, encoding="utf-8")

        if shutil.which(self.plingua_cmd) is None:
            return CompilationResult(
                success=False,
                stdout="",
                stderr="No se encontró P-Lingua. Configura PLINGUA_CMD o revisa la instalación.",
                return_code=127,
                input_path=str(input_path),
                output_xml_path=str(output_path),
            )

        cmd = [self.plingua_cmd, str(input_path), "-output_format", "xml", str(output_path)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        xml_exists = output_path.exists()
        return CompilationResult(
            success=proc.returncode == 0 and xml_exists,
            stdout=proc.stdout,
            stderr=proc.stderr,
            return_code=proc.returncode,
            input_path=str(input_path),
            output_xml_path=str(output_path),
        )
