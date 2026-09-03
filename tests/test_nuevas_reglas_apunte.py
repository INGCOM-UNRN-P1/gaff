"""Pruebas exhaustivas para las nuevas reglas de cátedra agregadas a GAFF."""

import pytest
from pathlib import Path
from gaff.core.linter import analizar_archivo


def test_regla_0x0000h_exceso_lineas_blanco(tmp_path):
    fuente = tmp_path / "claridad.c"
    fuente.write_text("int main(void)\n{\n    int x = 1;\n\n\n\n\n    return 0;\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x0000h" for v in viols)


def test_regla_0x000Ah_comentario_obvio(tmp_path):
    fuente = tmp_path / "comentario.c"
    fuente.write_text("int main(void)\n{\n    int i = 0;\n    // incrementa i en 1\n    i++;\n    return 0;\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x000Ah" for v in viols)


def test_regla_0x0036h_destructor_tda_sin_null(tmp_path):
    fuente = tmp_path / "tda_dest.c"
    fuente.write_text("void cliente(void)\n{\n    cola_t *c = cola_crear();\n    cola_destruir(c);\n    printf(\"fin\\n\");\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x0036h" for v in viols)


def test_regla_0x1004h_condicion_compleja(tmp_path):
    fuente = tmp_path / "cond_comp.c"
    fuente.write_text("void f(int a, int b, int c, int d)\n{\n    if (a > 0 && b > 0 && c > 0 || d > 0)\n    {\n        return;\n    }\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x1004h" for v in viols)


def test_regla_0x1005h_truthiness_strcmp_y_ptr(tmp_path):
    fuente = tmp_path / "truthiness.c"
    fuente.write_text("void f(const char *s, int *ptr)\n{\n    if (!strcmp(s, \"test\"))\n    {\n        return;\n    }\n    if (!ptr)\n    {\n        return;\n    }\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x1005h" for v in viols)


def test_regla_0x2006h_multiples_aserciones_en_test(tmp_path):
    fuente = tmp_path / "test_fn.c"
    fuente.write_text("void test_operacion(void)\n{\n    assert(1 == 1);\n    assert(2 == 2);\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x2006h" for v in viols)


def test_regla_0x2007h_variable_iteracion_alcance_externo(tmp_path):
    fuente = tmp_path / "alcance.c"
    fuente.write_text("void f(void)\n{\n    int i;\n    for (i = 0; i < 10; i++)\n    {\n        printf(\"%d\", i);\n    }\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x2007h" for v in viols)


def test_regla_0x2008h_retorno_numero_magico(tmp_path):
    fuente = tmp_path / "ret_magico.c"
    fuente.write_text("int calcular(int x)\n{\n    if (x < 0)\n    {\n        return -1;\n    }\n    return 42;\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x2008h" for v in viols)


def test_regla_0x2009h_monolitico_en_main(tmp_path):
    fuente = tmp_path / "monolitico.c"
    body = "\n".join(f"    printf(\"linea {i}\\n\");" for i in range(40))
    fuente.write_text(f"#include <stdio.h>\nint main(void)\n{{\n{body}\n    return 0;\n}}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x2009h" for v in viols)


def test_regla_0x3001h_malloc_sin_null_check(tmp_path):
    fuente = tmp_path / "sin_check.c"
    fuente.write_text("void f(void)\n{\n    int *ptr = malloc(sizeof(int));\n    *ptr = 10;\n    free(ptr);\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x3001h" for v in viols)


def test_regla_0x3002h_free_sin_null(tmp_path):
    fuente = tmp_path / "free_no_null.c"
    fuente.write_text("void f(void)\n{\n    int *ptr = malloc(sizeof(int));\n    if (ptr == NULL) return;\n    free(ptr);\n    printf(\"listo\\n\");\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x3002h" for v in viols)


def test_regla_0x3006h_creador_sin_documentar_propiedad(tmp_path):
    fuente = tmp_path / "creator.c"
    fuente.write_text("/**\n * Crea un elemento.\n */\nint *elemento_crear(void)\n{\n    int *p = malloc(sizeof(int));\n    if (p == NULL) return NULL;\n    return p;\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x3006h" for v in viols)


def test_regla_0x3007h_readonly_ptr_sin_const(tmp_path):
    fuente = tmp_path / "readonly.c"
    fuente.write_text("void imprimir_mensaje(char *msg)\n{\n    printf(\"%s\\n\", msg);\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x3007h" for v in viols)


def test_regla_0x3009h_retorno_null_sin_documentar(tmp_path):
    fuente = tmp_path / "ret_null.c"
    fuente.write_text("/**\n * Busca el registro.\n * @return El registro encontrado.\n */\nint *buscar_registro(int id)\n{\n    if (id < 0) return NULL;\n    return NULL;\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x3009h" for v in viols)


def test_regla_0x300Ah_cast_explicito_puntero(tmp_path):
    fuente = tmp_path / "cast_ptr.c"
    fuente.write_text("void f(void *mem)\n{\n    int *p = mem;\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x300Ah" for v in viols)


def test_regla_0x300Ch_fuera_de_limites(tmp_path):
    fuente = tmp_path / "oob.c"
    fuente.write_text("void f(void)\n{\n    int arr[5];\n    arr[10] = 42;\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x300Ch" for v in viols)


def test_regla_0x300Eh_punteros_sin_doc_null(tmp_path):
    fuente = tmp_path / "doc_null.c"
    fuente.write_text("/**\n * Procesa los datos del cliente.\n * @param datos Puntero a la estructura.\n */\nvoid procesar_cliente(int *datos)\n{\n    *datos = 10;\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x300Eh" for v in viols)


def test_regla_0x300Fh_liberacion_orden_inverso(tmp_path):
    fuente = tmp_path / "orden_free.c"
    fuente.write_text("void liberar_matriz(int **matriz, int n)\n{\n    free(matriz);\n    for (int i = 0; i < n; i++) {\n        free(matriz[i]);\n    }\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x300Fh" for v in viols)


def test_regla_0x3010h_variable_tamano_int(tmp_path):
    fuente = tmp_path / "size_int.c"
    fuente.write_text("void f(const char *str)\n{\n    int tamano = 100;\n    int longitud = strlen(str);\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x3010h" for v in viols)


def test_regla_0x3011h_void_ptr_sin_const(tmp_path):
    fuente = tmp_path / "void_ro.c"
    fuente.write_text("void imprimir_bytes(void *datos, size_t n)\n{\n    printf(\"%p\", datos);\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x3011h" for v in viols)


def test_regla_0x4001h_fopen_sin_validar(tmp_path):
    fuente = tmp_path / "fopen_novalid.c"
    fuente.write_text("void f(void)\n{\n    FILE *arch = fopen(\"data.txt\", \"r\");\n    char buf[10];\n    fgets(buf, 10, arch);\n    fclose(arch);\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x4001h" for v in viols)


def test_regla_0x4002h_io_return_descartado(tmp_path):
    fuente = tmp_path / "io_ignored.c"
    fuente.write_text("void f(FILE *arch)\n{\n    int buf[5];\n    fwrite(buf, sizeof(int), 5, arch);\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x4002h" for v in viols)


def test_regla_0x4003h_fopen_error_sin_perror(tmp_path):
    fuente = tmp_path / "no_perror.c"
    fuente.write_text("void f(void)\n{\n    FILE *arch = fopen(\"data.txt\", \"r\");\n    if (arch == NULL) {\n        printf(\"Error al abrir archivo\\n\");\n        return;\n    }\n    fclose(arch);\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x4003h" for v in viols)


def test_regla_0x4004h_fopen_sin_fclose(tmp_path):
    fuente = tmp_path / "sin_fclose.c"
    fuente.write_text("void f(void)\n{\n    FILE *arch = fopen(\"data.txt\", \"r\");\n    if (arch == NULL) return;\n    printf(\"abierto\\n\");\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x4004h" for v in viols)


def test_regla_0x4005h_fseek_offset_magico(tmp_path):
    fuente = tmp_path / "fseek_magic.c"
    fuente.write_text("void f(FILE *arch)\n{\n    fseek(arch, 512, SEEK_SET);\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x4005h" for v in viols)


def test_regla_0x5002h_pragma_silenciador(tmp_path):
    fuente = tmp_path / "pragma.c"
    fuente.write_text("#pragma GCC diagnostic ignored \"-Wunused-variable\"\nint main(void)\n{\n    int x;\n    return 0;\n}\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x5002h" for v in viols)


def test_regla_0x5005h_include_despues_de_funciones(tmp_path):
    fuente = tmp_path / "desorden.c"
    fuente.write_text("void funcion_uno(void)\n{\n    return;\n}\n#include <stdio.h>\n")
    viols = analizar_archivo(fuente)
    assert any(v.codigo == "0x5005h" for v in viols)
