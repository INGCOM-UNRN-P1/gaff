"""Tests para las 20 nuevas mejoras QoL e integración de GAFF documentadas en actual.md."""

import json
from pathlib import Path
from typer.testing import CliRunner

from gaff.cli import app
from gaff.core.linter import (
    analizar_archivo,
    aplicar_autofix_archivo,
    ejecutar_linter,
    convertir_pragma_once_a_guardas,
    detectar_inclusiones_ciclicas,
    auditar_guardas_proyecto,
)
from gaff.core.exporter import generar_sarif_210
from gaff.ripley_plugin import GaffPlugin

runner = CliRunner()


def test_qol_01_memset_argument_order(tmp_path: Path):
    """Mejora 1: Auditor de orden de argumentos en funciones de memoria estándar (memset(ptr, size, val))."""
    src = tmp_path / "memset_bad.c"
    src.write_text("int main(void)\n{\n    char buf[100];\n    memset(buf, sizeof(buf), 0);\n    return 0;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x3016h"})
    assert any(v.codigo == "0x3016h" and "memset" in v.mensaje.lower() for v in viols)


def test_qol_02_yoda_condition(tmp_path: Path):
    """Mejora 2: Detección de comparaciones contra constantes con orden Yoda (NULL == ptr)."""
    src = tmp_path / "yoda.c"
    src.write_text("int foo(int *p)\n{\n    if (NULL == p)\n    {\n        return 0;\n    }\n    return 1;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x100Ch"})
    assert any(v.codigo == "0x100Ch" and "Yoda" in v.mensaje for v in viols)


def test_qol_03_bloques_extensos_comentario_cierre(tmp_path: Path):
    """Mejora 3: Verificación de comentarios de cierre en bloques extensos (> 25 líneas)."""
    src = tmp_path / "bloque_largo.c"
    lineas = ["void funcion_larga(void)", "{"]
    for i in range(30):
        lineas.append(f"    int x_{i} = {i};")
    lineas.append("}")  # sin comentario // end
    src.write_text("\n".join(lineas) + "\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x200Eh"})
    assert any(v.codigo == "0x200Eh" and "sin comentario explicativo" in v.mensaje for v in viols)


def test_qol_04_colision_guardas_headers(tmp_path: Path):
    """Mejora 4: Auditor de colisión de nombres de macros de guarda entre archivos distintos."""
    h1 = tmp_path / "header1.h"
    h2 = tmp_path / "header2.h"
    h1.write_text("#ifndef __COMUN_H__\n#define __COMUN_H__\nvoid f1(void);\n#endif\n")
    h2.write_text("#ifndef __COMUN_H__\n#define __COMUN_H__\nvoid f2(void);\n#endif\n")
    colisiones = auditar_guardas_proyecto([h1, h2])
    assert len(colisiones) == 1
    assert colisiones[0]["guarda"] == "__COMUN_H__"


def test_qol_05_explicit_void(tmp_path: Path):
    """Mejora 5: Verificación de uso de explicit void en prototipos (int f() vs int f(void))."""
    src = tmp_path / "proto_vacio.c"
    src.write_text("int contador();\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x200Fh"})
    assert any(v.codigo == "0x200Fh" and "sin 'void' explícito" in v.mensaje for v in viols)


def test_qol_06_cast_redundante(tmp_path: Path):
    """Mejora 6: Detector de casts de tipo innecesarios en variables o literales compatibles."""
    src = tmp_path / "cast_innecesario.c"
    src.write_text("int main(void)\n{\n    int x = (int)0;\n    return x;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x100Dh"})
    assert any(v.codigo == "0x100Dh" and "Cast de tipo redundante" in v.mensaje for v in viols)


def test_qol_07_espaciado_operador_ternario(tmp_path: Path):
    """Mejora 7: Validador de espaciado en operadores ternarios (cond ? a : b)."""
    src = tmp_path / "ternario.c"
    src.write_text("int main(void)\n{\n    int a = 1, b = 2;\n    int m = (a < b)?a:b;\n    return m;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x100Eh"})
    assert any(v.codigo == "0x100Eh" and "operador ternario" in v.mensaje for v in viols)


def test_qol_08_orden_calificadores_const(tmp_path: Path):
    """Mejora 8: Auditor de consistencia en el orden de calificadores (const int vs int const)."""
    src = tmp_path / "calificadores.c"
    src.write_text("int main(void)\n{\n    int const MAXIMO = 100;\n    return MAXIMO;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x3017h"})
    assert any(v.codigo == "0x3017h" and "const int" in v.sugerencia for v in viols)


def test_qol_09_pragma_no_estandar(tmp_path: Path):
    """Mejora 9: Detección de directivas #pragma no estándar o dependientes de compiladores cerrados."""
    src = tmp_path / "pragma.c"
    src.write_text('#pragma warning(disable: 4996)\n#include <stdio.h>\nint main(void) { return 0; }\n')
    viols = analizar_archivo(src, reglas_habilitadas={"0x5012h"})
    assert any(v.codigo == "0x5012h" and "MSVC" in v.mensaje for v in viols)


def test_qol_10_convert_guards(tmp_path: Path):
    """Mejora 10: Autofix de conversión automática de guardas #pragma once a guardas #ifndef canónicas."""
    hdr = tmp_path / "modulo.h"
    hdr.write_text("#pragma once\n\nint sumar(int a, int b);\n")
    converted, changed = convertir_pragma_once_a_guardas(hdr.read_text(), hdr.stem)
    assert changed is True
    assert "#ifndef __MODULO_H__" in converted
    assert "#define __MODULO_H__" in converted
    assert "#endif // __MODULO_H__" in converted


def test_qol_11_alineacion_vertical(tmp_path: Path):
    """Mejora 11: Validador de alineación vertical en declaraciones y asignaciones consecutivas."""
    src = tmp_path / "alineacion.c"
    src.write_text("int main(void)\n{\nint a = 1;\n  int b = 2;\n    int c = 3;\n    return a + b + c;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0015h"})
    assert any(v.codigo == "0x0015h" and "desalineada" in v.mensaje for v in viols)


def test_qol_12_inicializador_idiomatico_vs_memset(tmp_path: Path):
    """Mejora 12: Auditor de inicializadores idiomáticos de arreglos y structs ({0} vs memset)."""
    src = tmp_path / "memset_struct.c"
    src.write_text("struct punto_t\n{\n    int x;\n    int y;\n};\n\nvoid foo(void)\n{\n    struct punto_t p;\n    memset(&p, 0, sizeof(p));\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x3018h"})
    assert any(v.codigo == "0x3018h" and "{0}" in v.sugerencia for v in viols)


def test_qol_13_constante_magica_indice_arreglo(tmp_path: Path):
    """Mejora 13: Detección de constantes numéricas mágicas en índices fijos de arreglos (vec[7])."""
    src = tmp_path / "indice_magico.c"
    src.write_text("void foo(int *vec)\n{\n    vec[7] = 42;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0038h"})
    assert any(v.codigo == "0x0038h" and "índice numérico mágico literal '7'" in v.mensaje for v in viols)


def test_qol_14_exportador_sarif_210(tmp_path: Path):
    """Mejora 14: Exportador nativo a formato SARIF 2.1.0 (gaff check --sarif)."""
    src = tmp_path / "demo.c"
    src.write_text("int foo() { return (0); }\n")
    reporte = ejecutar_linter([src], recursive=False)
    sarif = generar_sarif_210(reporte)
    assert sarif["version"] == "2.1.0"
    assert sarif["runs"][0]["tool"]["driver"]["name"] == "gaff"

    # Verificar integración con CLI --sarif
    res = runner.invoke(app, ["check", str(src), "--sarif"])
    assert res.exit_code in (0, 1)
    sarif_cli = json.loads(res.stdout)
    assert sarif_cli["version"] == "2.1.0"


def test_qol_15_parentesis_superfluos_return(tmp_path: Path):
    """Mejora 15: Auditor de espacios y paréntesis superfluos en sentencias return (return (x); vs return x;)."""
    src = tmp_path / "return_paren.c"
    src.write_text("int main(void)\n{\n    int x = 42;\n    return (x);\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x2010h"})
    assert any(v.codigo == "0x2010h" and "Paréntesis superfluos" in v.mensaje for v in viols)

    # Verificar autofix
    arreglos = aplicar_autofix_archivo(src)
    assert arreglos > 0
    assert "return x;" in src.read_text()


def test_qol_16_espaciado_doble_puntero(tmp_path: Path):
    """Mejora 16: Validador de espaciado en declaraciones de tipos puntero a puntero (char **argv)."""
    src = tmp_path / "doble_ptr.c"
    src.write_text("int main(int argc, char** argv)\n{\n    return 0;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0017h"})
    assert any(v.codigo == "0x0017h" and "doble puntero" in v.mensaje for v in viols)

    # Verificar autofix
    aplicar_autofix_archivo(src)
    assert "char **argv" in src.read_text()


def test_qol_17_inclusiones_ciclicas(tmp_path: Path):
    """Mejora 17: Detección de inclusiones cíclicas locales entre archivos de cabecera."""
    ha = tmp_path / "alpha.h"
    hb = tmp_path / "beta.h"
    ha.write_text('#include "beta.h"\n')
    hb.write_text('#include "alpha.h"\n')
    ciclos = detectar_inclusiones_ciclicas([ha, hb])
    assert len(ciclos) == 1
    assert set(ciclos[0]) == {"alpha.h", "beta.h"}


def test_qol_18_extern_en_archivo_c(tmp_path: Path):
    """Mejora 18: Auditor de declaraciones extern sin archivo de cabecera asociado en .c."""
    src = tmp_path / "modulo.c"
    src.write_text("extern int g_contador;\n\nint main(void) { return g_contador; }\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x5013h"})
    assert any(v.codigo == "0x5013h" and "extern" in v.mensaje for v in viols)


def test_qol_19_diff_cmd(tmp_path: Path):
    """Mejora 19: Reporte diferencial interactivo (gaff diff)."""
    res = runner.invoke(app, ["diff", str(tmp_path)])
    assert res.exit_code == 0
    assert "No se encontraron" in res.stdout or "cumplen" in res.stdout


def test_qol_20_lsp_quickfix(tmp_path: Path):
    """Mejora 20: Integración nativa con Ripley LSP Server para code actions rápidas (quickfix)."""
    src = tmp_path / "quickfix_test.c"
    src.write_text("int main(void)\n{\n    int x = 42;\n    return (x);\n}\n")
    plugin = GaffPlugin()
    actions = plugin.get_quickfixes(tmp_path, src)
    assert len(actions) > 0
    assert any(a["kind"] == "quickfix" for a in actions)

    # Probar comando lsp-quickfix en CLI
    res = runner.invoke(app, ["lsp-quickfix", str(src)])
    assert res.exit_code == 0
    data = json.loads(res.stdout)
    assert isinstance(data, list)
    assert any(a["kind"] == "quickfix" for a in data)
