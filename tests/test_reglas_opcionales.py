"""Decisión 7 de la remediación: `_e` en las enumeraciones (0x3004h) y 0x3020h como regla opcional."""

from pathlib import Path

from typer.testing import CliRunner

from gaff.api import analizar_codigo
from gaff.cli import app
from gaff.core.config import cargar_configuracion_gaff

CODIGO = """\
typedef enum estado { ACTIVO, INACTIVO } estado_t;
typedef enum color { ROJO, VERDE } color_e;
typedef struct nodo nodo_t;
struct punto { int x, y; } p1, *p2, arr[3];
struct par { int a; };
struct par q = {1};
typedef struct { int z; } zeta_t;
"""


def _codigos(viols, codigo):
    return [v for v in viols if str(v.codigo).lower().startswith(codigo)]


def test_enum_exige_sufijo_e_y_struct_sigue_con_t():
    viols = _codigos(analizar_codigo(CODIGO), "0x3004h")
    assert [v.linea for v in viols] == [1]
    assert "estado_t" in viols[0].mensaje and "'estado_e'" in viols[0].sugerencia


def test_separar_tipo_y_declaracion_no_corre_por_defecto():
    assert _codigos(analizar_codigo(CODIGO), "0x3020h") == []


def test_separar_tipo_y_declaracion_se_activa():
    viols = _codigos(analizar_codigo(CODIGO, reglas_activadas={"0x3020h"}), "0x3020h")
    assert [v.linea for v in viols] == [4]
    assert "'p1', 'p2', 'arr'" in viols[0].mensaje


def test_activar_desde_la_configuracion_y_la_cli(tmp_path: Path):
    fuente = tmp_path / "tipos.c"
    fuente.write_text(CODIGO, encoding="utf-8")
    runner = CliRunner()
    assert "0x3020h" not in runner.invoke(app, ["check", str(fuente), "--json"]).output
    assert "0x3020h" in runner.invoke(app, ["check", str(fuente), "--json", "--activar", "0x3020h"]).output

    (tmp_path / ".gaffrc.yaml").write_text("enabled_rules: [0x3020h]\n", encoding="utf-8")
    assert cargar_configuracion_gaff(tmp_path)["enabled_rules"] == ["0x3020h"]
    assert "0x3020h" in runner.invoke(app, ["check", str(fuente), "--json"]).output
