"""Tests para la configuración de reglas por EXCLUSIÓN en GAFF."""

from pathlib import Path
from typer.testing import CliRunner

from gaff.cli import app
from gaff.core.config import cargar_configuracion_gaff, obtener_reglas_excluidas
from gaff.core.linter import analizar_archivo, ejecutar_linter

runner = CliRunner()


def test_obtener_reglas_excluidas():
    """Valida la extracción y normalización de exclusiones desde diversas claves."""
    cfg = {
        "excluded_rules": ["0x0001h", "0x0003h"],
        "disabled_rules": ["0x0005h"],
        "exclude": "0x0007h, 0x0008h",
    }
    excluidas = obtener_reglas_excluidas(cfg)
    assert "0x0001h" in excluidas
    assert "0x0003h" in excluidas
    assert "0x0005h" in excluidas
    assert "0x0007h" in excluidas
    assert "0x0008h" in excluidas


def test_exclusion_directa_en_analizar_archivo(tmp_path: Path):
    """Verifica que una regla excluida no genere violaciones pero las demás sí."""
    codigo = """
    void procesar(int numero1)
    {
        int x = 10;
        int y = 20;
    }
    """
    fuente = tmp_path / "test.c"
    fuente.write_text(codigo, encoding="utf-8")

    # Sin exclusión: numero1 dispara 0x0037h
    viols_todas = analizar_archivo(fuente)
    codigos_todas = [v.codigo for v in viols_todas]
    assert "0x0037h" in codigos_todas

    # Con exclusión de 0x0037h
    viols_excluidas = analizar_archivo(fuente, reglas_excluidas={"0x0037h"})
    codigos_excluidas = [v.codigo for v in viols_excluidas]
    assert "0x0037h" not in codigos_excluidas


def test_exclusion_desde_archivo_config_yaml(tmp_path: Path):
    """Verifica que ejecutar_linter cargue automáticamente .gaffrc.yaml con exclusiones."""
    cfg_file = tmp_path / ".gaffrc.yaml"
    cfg_file.write_text("excluded_rules:\n  - 0x0037h\n  - 0x0005h\n", encoding="utf-8")

    codigo = "void fn(int numero1) { int a=1; }\n"
    fuente = tmp_path / "fuente.c"
    fuente.write_text(codigo, encoding="utf-8")

    reporte = ejecutar_linter([fuente])
    viols = [v.codigo for r in reporte.archivos for v in r.violaciones]

    assert "0x0037h" not in viols


def test_cli_check_con_flag_exclude(tmp_path: Path):
    """Verifica el comando CLI check con el flag --exclude."""
    fuente = tmp_path / "codigo.c"
    fuente.write_text("void calcular(int num1) {}\n", encoding="utf-8")

    # Sin excluir: debe advertir sobre num1
    result_sin = runner.invoke(app, ["check", str(fuente)])
    assert "0x010Eh" in result_sin.stdout or "0x0037h" in result_sin.stdout

    # Con --exclude 0x010Eh: no debe advertir sobre 0x010Eh
    result_con = runner.invoke(app, ["check", str(fuente), "--exclude", "0x010Eh"])
    assert "0x010Eh" not in result_con.stdout and "0x0037h" not in result_con.stdout
