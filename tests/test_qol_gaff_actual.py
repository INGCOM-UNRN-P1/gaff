"""Tests exhaustivos para las 20 mejoras QoL de GAFF documentadas en actual.md."""

from pathlib import Path
from typer.testing import CliRunner

from gaff.cli import app
from gaff.core.linter import analizar_archivo, aplicar_autofix_archivo, ejecutar_linter
from gaff.core.badge import generar_badge_svg, guardar_badge_svg
from gaff.core.interactive_fix import ejecutar_autofix_interactivo
from gaff.ripley_plugin import GaffPlugin

runner = CliRunner()


def test_qol_01_espacios_operadores_binarios(tmp_path: Path):
    """Mejora 1: Auditor de espacios en operadores aritméticos, lógicos y de comparación."""
    src = tmp_path / "operadores.c"
    src.write_text("int main(void)\n{\n    int a = 1;\n    int b = 2;\n    if (a<b)\n    {\n        int c = a+b;\n    }\n    return 0;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0004h"})
    codigos = [v.codigo for v in viols]
    assert "0x0004h" in codigos
    mensajes = [v.mensaje for v in viols]
    assert any("Falta espacio alrededor del operador binario" in m for m in mensajes)


def test_qol_02_espacio_palabras_clave(tmp_path: Path):
    """Mejora 2: Verificación de espacio obligatorio tras palabras clave (if (, for (, while ()."""
    src = tmp_path / "keywords.c"
    src.write_text("int main(void)\n{\n    if(1)\n    {\n        return 0;\n    }\n    return 0;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0004h"})
    assert any(v.codigo == "0x0004h" and "Falta espacio entre palabra clave 'if'" in v.mensaje for v in viols)


def test_qol_03_sentencias_multiples_misma_linea(tmp_path: Path):
    """Mejora 3: Prohibición de sentencias múltiples en una sola línea (x = 1; y = 2;)."""
    src = tmp_path / "multi_stmt.c"
    src.write_text("int main(void)\n{\n    int x = 1; int y = 2;\n    x = 10; y = 20;\n    return 0;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0002h"})
    assert any(v.codigo == "0x0002h" and "sentencias múltiples" in v.mensaje.lower() for v in viols)


def test_qol_04_lineas_en_blanco_redundantes(tmp_path: Path):
    """Mejora 4: Detección de líneas en blanco redundantes consecutivas."""
    src = tmp_path / "blancos.c"
    src.write_text("int main(void)\n{\n    int x = 0;\n\n\n\n    return x;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0000h"})
    assert any(v.codigo == "0x0000h" and "redundantes" in v.mensaje.lower() for v in viols)


def test_qol_05_headers_sistema_antes_de_usuario(tmp_path: Path):
    """Mejora 5: Verificación de inclusión de cabeceras de sistema antes de cabeceras de usuario."""
    src = tmp_path / "headers_orden.c"
    src.write_text('#include "modulo_aux.h"\n#include <stdio.h>\n\nint main(void)\n{\n    return 0;\n}\n')
    viols = analizar_archivo(src, reglas_habilitadas={"0x5005h"})
    assert any(v.codigo == "0x5005h" and "cabecera de sistema '<stdio.h>' posterior" in v.mensaje for v in viols)


def test_qol_06_auditor_caracteres_no_ascii(tmp_path: Path):
    """Mejora 6: Auditor de caracteres tipográficos no ASCII (comillas curvas, guiones tipográficos)."""
    src = tmp_path / "typo.c"
    # Carácter tipográfico dash '–' en código
    src.write_text("int main(void)\n{\n    int val – 10;\n    return 0;\n}\n", encoding="utf-8")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0014h"})
    assert any(v.codigo == "0x0014h" and "Carácter tipográfico o invisible no ASCII" in v.mensaje for v in viols)


def test_qol_07_nombres_variables_iteradoras_y_afijos(tmp_path: Path):
    """Mejora 7: Verificación de nombres de variables iteradoras y prohibición de variaciones como n1, num1."""
    src = tmp_path / "iteradores.c"
    src.write_text("int main(void)\n{\n    int numero1 = 10;\n    int num_2 = 20;\n    return numero1 + num_2;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0037h"})
    assert any(v.codigo == "0x0037h" for v in viols)


def test_qol_08_tamano_arreglo_sin_define_o_enum(tmp_path: Path):
    """Mejora 8: Auditor de constantes de tamaño de arreglo sin #define o enum (número mágico)."""
    src = tmp_path / "arreglo_tam.c"
    src.write_text("void foo(void)\n{\n    char buffer[256];\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x5001h"})
    assert any(v.codigo == "0x5001h" and "número mágico '256'" in v.mensaje for v in viols)


def test_qol_09_switch_sin_clausula_default(tmp_path: Path):
    """Mejora 9: Verificación de presencia de cláusula default en todos los switch."""
    src = tmp_path / "switch_no_def.c"
    src.write_text("void foo(int x)\n{\n    switch (x)\n    {\n    case 1:\n        break;\n    }\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x1008h"})
    assert any(v.codigo == "0x1008h" for v in viols)


def test_qol_10_funcion_static_en_header(tmp_path: Path):
    """Mejora 10: Detección de funciones static con cuerpo de implementación en headers .h."""
    hdr = tmp_path / "modulo.h"
    hdr.write_text("#ifndef __MODULO_H__\n#define __MODULO_H__\n\nstatic int suma(int a, int b)\n{\n    return a + b;\n}\n\n#endif\n")
    viols = analizar_archivo(hdr, reglas_habilitadas={"0x5003h"})
    assert any(v.codigo == "0x5003h" and "Función 'static' con cuerpo" in v.mensaje for v in viols)


def test_qol_11_archivo_sin_newline_final(tmp_path: Path):
    """Mejora 11: Verificación de que los archivos terminen siempre con una nueva línea (\\n)."""
    src = tmp_path / "sin_newline.c"
    src.write_text("int main(void)\n{\n    return 0;\n}")  # Sin salto de línea al final
    viols = analizar_archivo(src, reglas_habilitadas={"0x0000h"})
    assert any(v.codigo == "0x0000h" and "no termina con una nueva línea" in v.mensaje for v in viols)

    # Verificar autofix
    arreglos = aplicar_autofix_archivo(src)
    assert arreglos > 0
    assert src.read_text().endswith("\n")


def test_qol_12_tamano_de_funciones_40_lineas(tmp_path: Path):
    """Mejora 12: Auditor de tamaño de funciones (Máximo 40 líneas por función)."""
    src = tmp_path / "fn_larga.c"
    lineas = ["int funcion_muy_larga(void)", "{"] + [f"    int v_{i} = {i};" for i in range(45)] + ["    return 0;", "}\n"]
    src.write_text("\n".join(lineas))
    viols = analizar_archivo(src, reglas_habilitadas={"0x2005h"})
    assert any(v.codigo == "0x2005h" and "40" in v.mensaje for v in viols)


def test_qol_13_nombres_estructuras_sufijo_t(tmp_path: Path):
    """Mejora 13: Verificación de nombres de estructuras y types con sufijo _t."""
    src = tmp_path / "tipos.c"
    src.write_text("typedef struct\n{\n    int x;\n} Punto;\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x3004h"})
    assert any(v.codigo == "0x3004h" for v in viols)


def test_qol_14_auditor_comentarios_todo_fixme(tmp_path: Path):
    """Mejora 14: Auditor de comentarios TODO y FIXME pendientes antes de la entrega."""
    src = tmp_path / "pendientes.c"
    src.write_text("int main(void)\n{\n    // TODO: implementar calculo de hash\n    /* FIXME: corregir posible desbordamiento */\n    return 0;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x000Fh"})
    mensajes = [v.mensaje for v in viols if v.codigo == "0x000Fh"]
    assert any("TODO/FIXME" in m for m in mensajes)


def test_qol_15_generador_badges_svg(tmp_path: Path):
    """Mejora 15: Generador de badges SVG de cumplimiento de estilo (Shields.io standard)."""
    badge_file = tmp_path / "estilo.svg"
    svg_perfect = generar_badge_svg(total_violaciones=0)
    assert "<svg" in svg_perfect
    assert "100% passing" in svg_perfect
    assert "#4c1" in svg_perfect

    svg_warn = generar_badge_svg(total_violaciones=6)
    assert "<svg" in svg_warn
    assert "issues" in svg_warn

    guardar_badge_svg(badge_file, total_violaciones=0)
    assert badge_file.is_file()
    assert "<svg" in badge_file.read_text(encoding="utf-8")


def test_qol_16_interactive_fix_step_by_step(tmp_path: Path):
    """Mejora 16/17: Corrector interactivo paso a paso con confirmación."""
    src = tmp_path / "tabs.c"
    src.write_text("int main(void)\n{\n\tif(1)\n\t{\n\t\treturn 0;\n\t}\n}\n")
    # Con auto_confirmar=True
    res = ejecutar_autofix_interactivo([src], auto_confirmar=True)
    assert res[str(src)] > 0
    assert "\t" not in src.read_text()


def test_qol_17_guardas_canonicas_headers(tmp_path: Path):
    """Mejora 17/18: Modo de linting de archivos de encabezado con verificación de guardas canónicas."""
    hdr = tmp_path / "pila.h"
    # Guarda que no coincide con el nombre del archivo
    hdr.write_text("#ifndef __OTRO_MODULO_H__\n#define __OTRO_MODULO_H__\n\nvoid push(int x);\n\n#endif\n")
    viols = analizar_archivo(hdr, reglas_habilitadas={"0x5003h"})
    assert any(v.codigo == "0x5003h" and "no sigue el formato canónico derivado de 'pila.h'" in v.mensaje for v in viols)


def test_qol_18_llaves_superfluas_o_bloques_vacios(tmp_path: Path):
    """Mejora 18/19: Detección de llaves superfluas o estructuras de control vacías."""
    src = tmp_path / "vacio.c"
    src.write_text("int main(void)\n{\n    if (1) {}\n    while (0);\n    return 0;\n}\n")
    viols = analizar_archivo(src, reglas_habilitadas={"0x100Bh"})
    assert any(v.codigo == "0x100Bh" for v in viols)


def test_qol_19_homoglifos_y_no_ascii_identificadores(tmp_path: Path):
    """Mejora 19/20: Validador de tipografía y caracteres no ASCII u homoglíficos en identificadores."""
    src = tmp_path / "homoglifo.c"
    # Usar letra cirílica 'а' (U+0430) en identificador 'vаr'
    src.write_text("int main(void)\n{\n    int vаr = 10;\n    return vаr;\n}\n", encoding="utf-8")
    viols = analizar_archivo(src, reglas_habilitadas={"0x0014h"})
    assert any(v.codigo == "0x0014h" and "homoglíficos" in v.mensaje for v in viols)


def test_qol_20_integracion_transversal_cli_y_ripley(tmp_path: Path):
    """Mejora 20: Comandos transversales (badge, doctor) e integración como plugin de Ripley."""
    # 1. CLI gaff badge
    src = tmp_path / "ok.c"
    src.write_text("int main(void)\n{\n    return 0;\n}\n")
    out_svg = tmp_path / "badge.svg"
    res_badge = runner.invoke(app, ["badge", str(src), "-o", str(out_svg)])
    assert res_badge.exit_code == 0
    assert out_svg.is_file()

    # 2. CLI gaff check --badge
    out_svg2 = tmp_path / "badge2.svg"
    res_check = runner.invoke(app, ["check", str(src), "--badge", str(out_svg2)])
    assert res_check.exit_code == 0
    assert out_svg2.is_file()

    # 3. Ripley Plugin
    plugin = GaffPlugin()
    assert plugin.is_available()
    res_plug = plugin.execute(tmp_path, {})
    assert "ok" in res_plug
    assert "total_violaciones" in res_plug
