"""Tests para la categorización canónica de severidades y RuleCode enriquecido (GAFF-D0202, GAFF-D0302, GAFF-D0601)."""

from pathlib import Path
from gaff.core.models import RuleCode, ViolacionRegla, ReglaInfo
from gaff.core.contexto import ContextoAnalisis
from gaff.core.rules import (
    obtener_severidad,
    REGLAS_SEVERIDAD_ERROR,
    REGLAS_SEVERIDAD_ADVERTENCIA,
    CATALOGO_REGLAS,
)
from gaff.core.exporter import generar_sarif_210, generar_github_summary
from gaff.core.models import ReporteLinting, ReporteArchivo


def test_rule_code_properties():
    # Regla de error
    rc_err = RuleCode("0x3001h", alias="GAFF_0x3001h", codigo_anterior="0x3001h", severidad="ERROR")
    assert rc_err.es_error is True
    assert rc_err.es_advertencia is False
    assert rc_err.es_estilo is False
    assert rc_err.familia == "0x30XX"
    assert rc_err.alias == "GAFF_0x3001h"

    # Regla de advertencia
    rc_warn = RuleCode("0x1001h", severidad="ADVERTENCIA")
    assert rc_warn.es_error is False
    assert rc_warn.es_advertencia is True
    assert rc_warn.familia == "0x10XX"

    # Regla de estilo
    rc_style = RuleCode("0x0007h")
    assert rc_style.es_estilo is True
    assert rc_style.familia == "0x00XX"


def test_contexto_regla_info_namedtuple():
    ctx = ContextoAnalisis(
        ruta=Path("test.c"),
        contenido_original="int main(void) { return 0; }",
        lineas=["int main(void) { return 0; }"],
        codigo_sin_comentarios="int main(void) { return 0; }",
        lineas_sin_comentarios=["int main(void) { return 0; }"],
        codigo_sin_cadenas="int main(void) { return 0; }",
        lineas_sin_cadenas=["int main(void) { return 0; }"],
        es_header=False,
    )

    info = ctx.regla_info("0x3001h")
    assert isinstance(info, ReglaInfo)
    assert info.severidad == "ERROR"
    assert info.codigo.es_error is True

    # Desempaquetado retrocompatible (cod, titulo)
    cod, titulo = ctx.regla_info("0x3001h")
    assert cod == "0x3001h"
    assert isinstance(cod, RuleCode)
    assert cod.es_error is True
    assert isinstance(titulo, str)


def test_violacion_regla_adopta_severidad_automatica():
    # Violación con regla crítica (0x3001h): sin severidad explícita debe adoptar ERROR
    v_err = ViolacionRegla(
        codigo="0x3001h",
        titulo="Malloc sin verificar",
        archivo=Path("test.c"),
        linea=10,
        columna=5,
        mensaje="Falta verificar NULL",
        sugerencia="Validar retorno",
    )
    assert v_err.severidad == "ERROR"

    # Violación con regla de advertencia (0x1001h): debe adoptar ADVERTENCIA
    v_warn = ViolacionRegla(
        codigo="0x1001h",
        titulo="Uso de goto",
        archivo=Path("test.c"),
        linea=15,
        columna=5,
        mensaje="Goto detectado",
        sugerencia="Estructurar flujo",
    )
    assert v_warn.severidad == "ADVERTENCIA"

    # Violación con regla de formato (0x0007h): debe mantener ESTILO
    v_style = ViolacionRegla(
        codigo="0x0007h",
        titulo="Allman style",
        archivo=Path("test.c"),
        linea=2,
        columna=1,
        mensaje="Llave en misma línea",
        sugerencia="Bajar llave",
    )
    assert v_style.severidad == "ESTILO"


def test_sarif_y_github_summary_con_severidades():
    v1 = ViolacionRegla(
        codigo="0x3001h",
        titulo="Malloc",
        archivo=Path("src/main.c"),
        linea=10,
        columna=1,
        mensaje="Error de memoria",
        sugerencia="Validar",
    )
    v2 = ViolacionRegla(
        codigo="0x0007h",
        titulo="Allman",
        archivo=Path("src/main.c"),
        linea=20,
        columna=1,
        mensaje="Estilo Allman",
        sugerencia="Separar",
    )
    rep_arch = ReporteArchivo(archivo=Path("src/main.c"), violaciones=[v1, v2])
    rep = ReporteLinting(archivos=[rep_arch])

    sarif = generar_sarif_210(rep)
    results = sarif["runs"][0]["results"]
    assert len(results) == 2
    # El primer resultado es 0x3001h con ERROR -> level "error"
    assert results[0]["level"] == "error"
    # El segundo resultado es 0x0007h con ESTILO -> level "warning"
    assert results[1]["level"] == "warning"

    summary = generar_github_summary(rep)
    assert "Errores Críticos" in summary
    assert "Advertencias de Estilo" in summary
    assert "🔴 ERROR" in summary
    assert "🟡 WARN" in summary
