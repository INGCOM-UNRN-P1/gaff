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


def test_autofix_genera_esqueleto_doxygen_con_argumentos(tmp_path: Path):
    from gaff.core.linter import aplicar_autofix_archivo

    src = tmp_path / "calc_fix.c"
    src.write_text(
        "int sumar(int a, int b)\n"
        "{\n"
        "    return a + b;\n"
        "}\n",
        encoding="utf-8",
    )
    # 1. Verificar que la violación es reportada como autofixable
    viols = analizar_archivo(src, reglas_habilitadas={"0x2003h"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x2003h"
    assert viols[0].es_autofixable is True

    # 2. Aplicar autofix
    arreglos = aplicar_autofix_archivo(src)
    assert arreglos > 0

    # 3. Comprobar que el contenido ahora incluye el esqueleto Doxygen
    contenido = src.read_text(encoding="utf-8")
    assert "/**" in contenido
    assert "@brief Descripción de la función sumar." in contenido
    assert "@param a Descripción del parámetro a." in contenido
    assert "@param b Descripción del parámetro b." in contenido
    assert "@return Descripción del valor de retorno." in contenido

    # 4. El archivo ya no debe tener violaciones de 0x2003h
    viols_post = analizar_archivo(src, reglas_habilitadas={"0x2003h"})
    assert len(viols_post) == 0


def test_autofix_prototipo_en_header(tmp_path: Path):
    from gaff.core.linter import aplicar_autofix_archivo

    hdr = tmp_path / "vector.h"
    hdr.write_text(
        "#ifndef VECTOR_H\n"
        "#define VECTOR_H\n"
        "\n"
        "void procesar_vector(int *vector, size_t longitud);\n"
        "\n"
        "#endif\n",
        encoding="utf-8",
    )
    viols = analizar_archivo(hdr, reglas_habilitadas={"0x2003h"})
    assert len(viols) == 1
    assert viols[0].es_autofixable is True

    arreglos = aplicar_autofix_archivo(hdr)
    assert arreglos > 0

    contenido = hdr.read_text(encoding="utf-8")
    assert "/**" in contenido
    assert "@brief Descripción de la función procesar_vector." in contenido
    assert "@param vector Descripción del parámetro vector." in contenido
    assert "@param longitud Descripción del parámetro longitud." in contenido
    # void no debe incluir @return
    assert "@return" not in contenido

    viols_post = analizar_archivo(hdr, reglas_habilitadas={"0x2003h"})
    assert len(viols_post) == 0


def test_autofix_funcion_void_sin_parametros(tmp_path: Path):
    from gaff.core.linter import aplicar_autofix_archivo

    src = tmp_path / "reset.c"
    src.write_text(
        "void reiniciar(void)\n"
        "{\n"
        "    return;\n"
        "}\n",
        encoding="utf-8",
    )
    arreglos = aplicar_autofix_archivo(src)
    assert arreglos > 0

    contenido = src.read_text(encoding="utf-8")
    assert "/**" in contenido
    assert "@brief Descripción de la función reiniciar." in contenido
    assert "@param" not in contenido
    assert "@return" not in contenido

    viols_post = analizar_archivo(src, reglas_habilitadas={"0x2003h"})
    assert len(viols_post) == 0
