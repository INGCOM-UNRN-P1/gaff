"""Tests para las 8 nuevas mejoras QoL de GAFF documentadas en actual.md."""

import json
import os
from pathlib import Path
from typer.testing import CliRunner

from gaff.cli import app
from gaff.core.linter import (
    analizar_archivo,
    aplicar_autofix_archivo,
    ejecutar_linter,
)
from gaff.core.exporter import generar_github_summary
from gaff.core.config import cargar_configuracion_gaff, generar_plantilla_gaffrc_json

runner = CliRunner()


def test_qol_01_dead_store_0x2012h(tmp_path: Path):
    """Mejora 15 (Fase 3): Detección de variables declaradas o asignadas múltiples veces sin lectura intermedia (0x2012h)."""
    src_bad = tmp_path / "dead_store.c"
    src_bad.write_text(
        "int calcular(void)\n"
        "{\n"
        "    int x = 10;\n"
        "    x = 20;\n"
        "    return x;\n"
        "}\n"
    )
    viols = analizar_archivo(src_bad, reglas_habilitadas={"0x2012h"})
    assert any(v.codigo == "0x2012h" and "dead store" in v.mensaje.lower() for v in viols)

    # Caso conforme: lectura intermedia
    src_ok = tmp_path / "read_ok.c"
    src_ok.write_text(
        "int calcular_ok(void)\n"
        "{\n"
        "    int x = 10;\n"
        "    int y = x + 5;\n"
        "    x = 20;\n"
        "    return x + y;\n"
        "}\n"
    )
    viols_ok = analizar_archivo(src_ok, reglas_habilitadas={"0x2012h"})
    assert not any(v.codigo == "0x2012h" for v in viols_ok)


def test_qol_02_macro_parenthesis_0x5015h(tmp_path: Path):
    """Mejora 3 (Fase 3): Detección de macroconstantes definidas sin paréntesis de protección envolvente (0x5015h)."""
    src = tmp_path / "macro_sin_paren.c"
    src.write_text(
        "#define TAM 10 + 5\n"
        "#define BUFFER_MAX (1024 * 2)\n"
        "int main(void) { return TAM; }\n"
    )
    viols = analizar_archivo(src, reglas_habilitadas={"0x5015h"})
    assert any(v.codigo == "0x5015h" and "TAM" in v.mensaje for v in viols)
    assert not any(v.codigo == "0x5015h" and "BUFFER_MAX" in v.mensaje for v in viols)

    # Verificar autofix
    arreglos = aplicar_autofix_archivo(src)
    assert arreglos > 0
    assert "#define TAM (10 + 5)" in src.read_text()


def test_qol_03_scalar_braces_0x001Fh(tmp_path: Path):
    """Mejora 2 (Fase 3): Auditor de llaves redundantes en inicialización de escalares (0x001Fh)."""
    src = tmp_path / "escalares_llaves.c"
    src.write_text(
        "struct punto_t { int x; };\n"
        "int main(void)\n"
        "{\n"
        "    int contador = {0};\n"
        "    float tasa = {0.0};\n"
        "    struct punto_t p = {0};\n"
        "    return contador;\n"
        "}\n"
    )
    viols = analizar_archivo(src, reglas_habilitadas={"0x001Fh"})
    codigos = [v.codigo for v in viols]
    assert codigos.count("0x001Fh") == 2
    assert any("contador" in v.mensaje for v in viols)
    assert any("tasa" in v.mensaje for v in viols)
    # struct punto_t p = {0} no debe ser violacion
    assert not any("punto_t" in v.mensaje for v in viols)

    # Verificar autofix
    arreglos = aplicar_autofix_archivo(src)
    assert arreglos >= 2
    txt = src.read_text()
    assert "int contador = 0;" in txt
    assert "float tasa = 0.0;" in txt
    assert "struct punto_t p = {0};" in txt


def test_qol_04_chained_comparisons_0x1012h(tmp_path: Path):
    """Mejora 6 (Fase 3): Detección de comparaciones encadenadas no idiomáticas en C (a < b < c) (0x1012h)."""
    src = tmp_path / "chained_cmp.c"
    src.write_text(
        "int main(void)\n"
        "{\n"
        "    int a = 1, b = 2, c = 3;\n"
        "    if (a < b < c)\n"
        "    {\n"
        "        return 1;\n"
        "    }\n"
        "    return 0;\n"
        "}\n"
    )
    viols = analizar_archivo(src, reglas_habilitadas={"0x1012h"})
    assert any(v.codigo == "0x1012h" and "a < b < c" in v.mensaje for v in viols)

    # Verificar autofix
    aplicar_autofix_archivo(src)
    assert "a < b && b < c" in src.read_text()


def test_qol_05_unstructured_goto_0x1013h(tmp_path: Path):
    """Mejora 8 (Fase 3): Detección de saltos no estructurados goto fuera del patrón canónico de liberación (0x1013h)."""
    src_bad = tmp_path / "goto_atras.c"
    src_bad.write_text(
        "int main(void)\n"
        "{\n"
        "bucle:\n"
        "    // bucle espagueti hacia atras\n"
        "    goto bucle;\n"
        "    return 0;\n"
        "}\n"
    )
    viols = analizar_archivo(src_bad, reglas_habilitadas={"0x1013h"})
    assert any(v.codigo == "0x1013h" and "Salto hacia atrás" in v.mensaje for v in viols)

    # Caso conforme: forward jump a etiqueta de cleanup
    src_clean = tmp_path / "goto_clean.c"
    src_clean.write_text(
        "int recurso(int x)\n"
        "{\n"
        "    if (x < 0)\n"
        "    {\n"
        "        goto cleanup;\n"
        "    }\n"
        "    return 1;\n"
        "cleanup:\n"
        "    return -1;\n"
        "}\n"
    )
    viols_clean = analizar_archivo(src_clean, reglas_habilitadas={"0x1013h"})
    assert not any(v.codigo == "0x1013h" for v in viols_clean)


def test_qol_06_void_main_0x2013h(tmp_path: Path):
    """Mejora 7 (Fase 3): Auditor de tipo de retorno en función main() (int main obligatorio) (0x2013h)."""
    src = tmp_path / "void_main.c"
    src.write_text("void main(void)\n{\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x2013h"})
    assert any(v.codigo == "0x2013h" and "void main" in v.mensaje for v in viols)

    # Verificar autofix
    aplicar_autofix_archivo(src)
    assert "int main(void)" in src.read_text()


def test_qol_07_github_summary(tmp_path: Path, monkeypatch):
    """Mejora 14 (Fase 3): Exportador de resumen de cumplimiento a formato Markdown para GitHub Actions ($GITHUB_STEP_SUMMARY)."""
    src = tmp_path / "demo_gh.c"
    src.write_text("void main(void) { int x = {0}; }\n")
    reporte = ejecutar_linter([src], recursive=False)
    summary_md = generar_github_summary(reporte)
    assert "🛡️ Gaff Linter — Resumen de Cumplimiento de Estilo" in summary_md
    assert "Total Violaciones" in summary_md
    assert "demo_gh.c" in summary_md

    # Probar CLI con --github-summary y variable de entorno GITHUB_STEP_SUMMARY
    summary_file = tmp_path / "step_summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
    res = runner.invoke(app, ["check", str(src), "--github-summary"])
    assert res.exit_code in (0, 1)
    assert summary_file.is_file()
    assert "Gaff Linter" in summary_file.read_text()


def test_qol_08_init_config_gaffrc_json(tmp_path: Path):
    """Mejora 19 (Fase 3): Generador y cargador de plantilla de configuración .gaffrc.json personalizada por TP."""
    # 1. Probar generación vía CLI
    res = runner.invoke(
        app,
        [
            "init-config",
            "--dir",
            str(tmp_path),
            "--gaffrc",
            "--tp",
            "TP1 Lista Enlazada",
            "--exclude",
            "0x0001h,0x1006h",
        ],
    )
    assert res.exit_code == 0
    cfg_file = tmp_path / ".gaffrc.json"
    assert cfg_file.is_file()

    data = json.loads(cfg_file.read_text())
    assert data["tp"] == "TP1 Lista Enlazada"
    assert "0x0001h" in data["excluded_rules"]
    assert "0x1006h" in data["excluded_rules"]

    # 2. Probar carga de configuración transparente por GAFF
    loaded_cfg = cargar_configuracion_gaff(tmp_path)
    assert "0x0001h" in loaded_cfg["excluded_rules"]
    assert "0x1006h" in loaded_cfg["excluded_rules"]
