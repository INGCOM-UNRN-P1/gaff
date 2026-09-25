"""0x2011h (dead store) no debe confundir las ramas de un switch con asignaciones sucesivas (N-GAFF-05)."""

from __future__ import annotations

from pathlib import Path

from gaff.core.linter import analizar_archivo


def _dead_stores(tmp_path: Path, cuerpo: str) -> list[int]:
    fuente = tmp_path / "prueba.c"
    fuente.write_text(f"int f(int comando, int x)\n{{\n{cuerpo}\n}}\n", encoding="utf-8")
    return [v.linea for v in analizar_archivo(fuente, reglas_habilitadas={"0x2011h"})
            if "dead store" in v.mensaje]


def test_switch_con_resultado_unico_no_es_dead_store(tmp_path: Path):
    cuerpo = """    int resultado = 0;
    switch (comando)
    {
        case 1:
            resultado = 10;
            break;
        case 2:
            resultado = 20;
            break;
        default:
            resultado = -1;
            break;
    }
    return resultado;"""
    assert _dead_stores(tmp_path, cuerpo) == []


def test_case_sin_break_con_retorno_tampoco(tmp_path: Path):
    cuerpo = """    int resultado = 0;
    switch (comando)
    {
        case 1:
            resultado = 10;
            return resultado;
        case 2:
            resultado = 20;
            return resultado;
    }
    return x;"""
    assert _dead_stores(tmp_path, cuerpo) == []


def test_dead_store_real_se_sigue_detectando(tmp_path: Path):
    cuerpo = """    int total;
    total = x;
    total = x + 1;
    return total;"""
    assert _dead_stores(tmp_path, cuerpo) == [5]
