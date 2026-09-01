"""Tests unitarios para la regla 0x2003h: Documentación obligatoria de funciones y prototipos."""

from pathlib import Path
from gaff.core.linter import analizar_archivo


def test_funcion_sin_documentacion_advierte(tmp_path: Path):
    src = tmp_path / "calc.c"
    src.write_text(
        "int sumar(int a, int b) {\n"
        "    return a + b;\n"
        "}\n",
        encoding="utf-8",
    )
    viols = analizar_archivo(src, reglas_habilitadas={"0x2003h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x2003h"
    assert "sumar" in viols[0].mensaje
    assert "La función 'sumar' no incluye comentario de documentación" in viols[0].mensaje


def test_funcion_con_doxygen_valida(tmp_path: Path):
    src = tmp_path / "calc.c"
    src.write_text(
        "/**\n"
        " * @brief Suma dos números enteros.\n"
        " * @param a Primer sumando.\n"
        " * @param b Segundo sumando.\n"
        " * @return Resultado de la suma.\n"
        " */\n"
        "int sumar(int a, int b) {\n"
        "    return a + b;\n"
        "}\n",
        encoding="utf-8",
    )
    viols = analizar_archivo(src, reglas_habilitadas={"0x2003h"})
    assert len(viols) == 0


def test_prototipo_sin_documentacion_en_header(tmp_path: Path):
    hdr = tmp_path / "calc.h"
    hdr.write_text(
        "#ifndef CALC_H\n"
        "#define CALC_H\n"
        "\n"
        "int sumar(int a, int b);\n"
        "\n"
        "#endif\n",
        encoding="utf-8",
    )
    viols = analizar_archivo(hdr, reglas_habilitadas={"0x2003h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x2003h"
    assert "El prototipo de la función 'sumar' no incluye comentario de documentación" in viols[0].mensaje


def test_prototipo_con_doxygen_en_header(tmp_path: Path):
    hdr = tmp_path / "calc.h"
    hdr.write_text(
        "#ifndef CALC_H\n"
        "#define CALC_H\n"
        "\n"
        "/**\n"
        " * @brief Suma dos números enteros.\n"
        " */\n"
        "int sumar(int a, int b);\n"
        "\n"
        "#endif\n",
        encoding="utf-8",
    )
    viols = analizar_archivo(hdr, reglas_habilitadas={"0x2003h"})
    assert len(viols) == 0


def test_funcion_con_prototipo_documentado_en_mismo_archivo(tmp_path: Path):
    src = tmp_path / "prog.c"
    src.write_text(
        "/**\n"
        " * @brief Multiplica dos enteros.\n"
        " */\n"
        "int mult(int a, int b);\n"
        "\n"
        "int mult(int a, int b) {\n"
        "    return a * b;\n"
        "}\n",
        encoding="utf-8",
    )
    viols = analizar_archivo(src, reglas_habilitadas={"0x2003h"})
    assert len(viols) == 0


def test_funcion_con_prototipo_documentado_en_header_companero(tmp_path: Path):
    hdr = tmp_path / "operaciones.h"
    hdr.write_text(
        "#ifndef OPERACIONES_H\n"
        "#define OPERACIONES_H\n"
        "/**\n"
        " * @brief Divide dos números reales.\n"
        " */\n"
        "float dividir(float a, float b);\n"
        "#endif\n",
        encoding="utf-8",
    )
    src = tmp_path / "operaciones.c"
    src.write_text(
        '#include "operaciones.h"\n'
        "float dividir(float a, float b) {\n"
        "    return a / b;\n"
        "}\n",
        encoding="utf-8",
    )
    viols = analizar_archivo(src, reglas_habilitadas={"0x2003h"})
    assert len(viols) == 0


def test_main_esta_exento_de_documentacion(tmp_path: Path):
    src = tmp_path / "main.c"
    src.write_text(
        "int main(void) {\n"
        "    return 0;\n"
        "}\n",
        encoding="utf-8",
    )
    viols = analizar_archivo(src, reglas_habilitadas={"0x2003h"})
    assert len(viols) == 0


def test_comentario_descriptivo_valido(tmp_path: Path):
    src = tmp_path / "helper.c"
    src.write_text(
        "// Calcula el valor absoluto de un entero\n"
        "int modulo(int n) {\n"
        "    return n < 0 ? -n : n;\n"
        "}\n",
        encoding="utf-8",
    )
    viols = analizar_archivo(src, reglas_habilitadas={"0x2003h"})
    assert len(viols) == 0
