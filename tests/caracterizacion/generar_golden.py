"""Genera golden.json: las violaciones que da gaff sobre sus ejemplos (examples/) (N-GAFF-04).

Se generó antes de partir cada `verificar` de 270–458 líneas en una función por regla, para que
test_caracterizacion.py verifique que el refactor no cambió ninguna violación ni su orden. Regenerarlo
solo cuando un cambio de comportamiento sea intencional:
uv run python tests/caracterizacion/generar_golden.py
"""

from __future__ import annotations

import json
from pathlib import Path

from gaff.core.linter import ejecutar_linter

RAIZ = Path(__file__).resolve().parents[2]
AQUI = Path(__file__).resolve().parent


def ejemplos() -> list[Path]:
    return sorted(p for p in (RAIZ / "examples").rglob("*") if p.suffix in (".c", ".h"))


def violaciones(ruta: Path) -> list[list]:
    reporte = ejecutar_linter([ruta], config={})
    return [[str(v.codigo), v.linea, v.columna, v.mensaje, v.sugerencia, bool(v.es_autofixable)]
            for archivo in reporte.archivos for v in archivo.violaciones]


def main() -> None:
    golden = {r.relative_to(RAIZ).as_posix(): violaciones(r) for r in ejemplos()}
    (AQUI / "golden.json").write_text(json.dumps(golden, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(golden)} ejemplos, {sum(len(v) for v in golden.values())} violaciones")


if __name__ == "__main__":
    main()
