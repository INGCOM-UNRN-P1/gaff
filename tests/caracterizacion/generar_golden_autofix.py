"""Genera golden_autofix.json: el resultado de `aplicar_autofix_archivo` sobre cada ejemplo de
examples/ (sin clang-format, que depende del entorno). Se generó ANTES de partir la función: si
test_caracterizacion_autofix.py falla, el refactor cambió alguna corrección."""

import hashlib
import json
import tempfile
from pathlib import Path
from unittest import mock

AQUI = Path(__file__).parent
EJEMPLOS = AQUI.parents[1] / "examples"


def ejemplos():
    return sorted(p for p in EJEMPLOS.rglob("*") if p.suffix in (".c", ".h"))


def corregir(fuente: Path):
    from gaff.core import linter

    with tempfile.TemporaryDirectory() as tmp:
        copia = Path(tmp) / fuente.name
        # Fin de línea LF en la entrada y en el hash: en Windows el checkout trae CRLF.
        copia.write_bytes(fuente.read_bytes().replace(b"\r\n", b"\n"))
        with mock.patch.object(linter.subprocess, "run", side_effect=FileNotFoundError("sin clang-format")):
            arreglos = linter.aplicar_autofix_archivo(copia, reglas_excluidas=set())
        return arreglos, hashlib.sha256(copia.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def golden():
    return {p.relative_to(EJEMPLOS).as_posix(): list(corregir(p)) for p in ejemplos()}


if __name__ == "__main__":
    (AQUI / "golden_autofix.json").write_text(json.dumps(golden(), indent=1, sort_keys=True) + "\n", encoding="utf-8")
