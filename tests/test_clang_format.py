"""`gaff format` aplica el estilo de la cátedra sin archivos de configuración (ola R4)."""

import shutil

import pytest
from typer.testing import CliRunner

from gaff.cli import app
from gaff.core.config import CLANG_FORMAT_ARCHIVO, CLANG_FORMAT_STYLE
from gaff.core.linter import ejecutar_linter

con_clang_format = pytest.mark.skipif(shutil.which("clang-format") is None, reason="hace falta clang-format")

SIN_FORMATO = """#include <stdio.h>
int main(void){
  int x=1;
  switch(x){
  case 1: printf("uno\\n"); break;
  default: break;
  }
  if(x>0){ x=x+1; }
  return 0;
}
"""


def _formatear(tmp_path, nombre="prog.c"):
    fuente = tmp_path / nombre
    fuente.write_text(SIN_FORMATO, encoding="utf-8")
    res = CliRunner().invoke(app, ["format", str(fuente)])
    assert res.exit_code == 0
    return fuente.read_text(encoding="utf-8")


@con_clang_format
def test_el_estilo_es_el_de_la_catedra_sin_ningun_archivo(tmp_path):
    texto = _formatear(tmp_path)

    assert "int main(void)\n{\n" in texto  # llaves en su línea (0x000Bh)
    assert "\n    int x = 1;\n" in texto  # cuatro espacios
    assert "if (x > 0)\n" in texto


@con_clang_format
def test_el_case_va_indentado_como_pide_el_apunte(tmp_path):
    assert "\n        case 1:\n" in _formatear(tmp_path)


@con_clang_format
def test_un_clang_format_ajeno_no_cambia_el_resultado(tmp_path):
    sin_archivo = _formatear(tmp_path)
    (tmp_path / ".clang-format").write_text("BasedOnStyle: GNU\nIndentWidth: 8\n", encoding="utf-8")

    assert _formatear(tmp_path) == sin_archivo


@con_clang_format
def test_no_deja_archivos(tmp_path):
    _formatear(tmp_path)

    assert [p.name for p in tmp_path.iterdir()] == ["prog.c"]


@con_clang_format
def test_lo_formateado_no_tiene_hallazgos_de_formato(tmp_path):
    _formatear(tmp_path)

    reporte = ejecutar_linter([tmp_path / "prog.c"], config={})
    codigos = {str(v.codigo) for a in reporte.archivos for v in a.violaciones}

    assert not codigos & {"0x0003h", "0x0004h", "0x0005h", "0x0007h", "0x000Bh"}


def test_el_archivo_y_el_estilo_en_linea_dicen_lo_mismo():
    for linea in CLANG_FORMAT_ARCHIVO.splitlines()[1:]:
        assert linea in CLANG_FORMAT_STYLE


def test_el_estilo_respeta_las_reglas_de_la_catedra():
    assert "BreakBeforeBraces: Allman" in CLANG_FORMAT_STYLE
    assert "ColumnLimit: 80" in CLANG_FORMAT_STYLE
    assert "IndentCaseLabels: true" in CLANG_FORMAT_STYLE
