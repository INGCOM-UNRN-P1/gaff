"""Suite de regresión sintáctica sobre corpus masivo (Fase P1).

Evalúa el comportamiento de analizar_archivo sobre un lote de 1.000
archivos C sintéticos representativos de entregas de alumnos con
combinaciones diversas de estructuras, antipatrones, comentarios y directivas.
"""

from __future__ import annotations

import random
from pathlib import Path
import pytest

from gaff.core.linter import analizar_archivo
from gaff.core.rules import CATALOGO_REGLAS


SNIPPETS_ESTRUCTURAS = [
    """
    struct alumno {
        int padron;
        char nombre[50];
    };
    """,
    """
    typedef struct nodo {
        int dato;
        struct nodo *sig;
    } nodo_t;
    """,
    """
    enum estado {
        ESTADO_OK = 0,
        ESTADO_ERROR = 1
    };
    """,
]

SNIPPETS_FUNCIONES = [
    """
    int sumar(int a, int b) {
        return a + b;
    }
    """,
    """
    void procesar_datos(int *arr, size_t n) {
        if (!arr) return;
        for (size_t i = 0; i < n; i++) {
            arr[i] = (int)(i * 2);
        }
    }
    """,
    """
    nodo_t *crear_nodo(int dato) {
        nodo_t *n = malloc(sizeof(nodo_t));
        if (!n) return NULL;
        n->dato = dato;
        n->sig = NULL;
        return n;
    }
    """,
    """
    int calcular_factorial(int n) {
        if (n <= 1) return 1;
        return n * calcular_factorial(n - 1);
    }
    """,
]

SNIPPETS_ANTIPATRONES = [
    "int x = 42; // numero magico",
    "char buf[100]; gets(buf);",
    "strcpy(buf, \"test\");",
    "int *ptr = (int *)malloc(sizeof(int));",
    "int *p = NULL; *p = 10;",
    "goto cleanup;",
    "if (x == 1) { return 1; } else if (x == 2) { return 2; }",
    "while (!feof(stdin)) { getchar(); }",
    "int MiVariableGlobal = 0;",
    "void fn() { int a; int b; int c; int d; }",
]

SNIPPETS_DIRECTIVAS = [
    "#include <stdio.h>",
    "#include <stdlib.h>",
    "#include <string.h>",
    "#include <stdbool.h>",
    "// gaff:ignore 0x300Dh prueba de supresion justificada",
    "/* Comentario de documentacion de cabecera */",
]


def _generar_entrega_c(rng: random.Random, idx: int) -> str:
    """Genera el contenido fuente de un archivo C combinando fragmentos."""
    lineas = []
    lineas.append(f"/* Entrega de alumno id_{idx:04d} */")

    # Inclusiones
    num_includes = rng.randint(1, 4)
    lineas.extend(rng.sample(SNIPPETS_DIRECTIVAS, k=num_includes))
    lineas.append("")

    # Estructuras opcionales
    if rng.random() > 0.4:
        lineas.append(rng.choice(SNIPPETS_ESTRUCTURAS))

    # Funciones
    num_fn = rng.randint(1, 3)
    for _ in range(num_fn):
        lineas.append(rng.choice(SNIPPETS_FUNCIONES))

    # Inyección de antipatrones ocasionales
    if rng.random() > 0.3:
        lineas.append("void auxiliar_con_detalles(void) {")
        num_bugs = rng.randint(1, 3)
        for _ in range(num_bugs):
            lineas.append("    " + rng.choice(SNIPPETS_ANTIPATRONES))
        lineas.append("}")

    # Main estándar
    lineas.append("""
int main(void) {
    return 0;
}
""")
    return "\n".join(lineas)


def test_regresion_corpus_1000_entregas(tmp_path: Path):
    """Evalúa la robustez, determinismo y completitud sobre un lote de 1.000 entregas."""
    rng = random.Random(42)
    corpus_dir = tmp_path / "corpus_1000"
    corpus_dir.mkdir()

    archivos: list[Path] = []
    total_muestras = 1000

    for i in range(total_muestras):
        fpath = corpus_dir / f"entrega_{i:04d}.c"
        fpath.write_text(_generar_entrega_c(rng, i), encoding="utf-8")
        archivos.append(fpath)

    assert len(archivos) == total_muestras

    # 1. Ejecución sobre el corpus completo sin excepciones
    codigos_validos = set(CATALOGO_REGLAS.keys())
    total_violaciones = 0

    resultados_iniciales = {}

    for fpath in archivos:
        viols = analizar_archivo(fpath)
        total_violaciones += len(viols)
        resultados_iniciales[fpath.name] = [(v.codigo, v.linea, v.columna) for v in viols]

        for v in viols:
            # Línea y columna válidas
            assert v.linea >= 1
            assert v.columna >= 1
            # Código reconocido
            cod_str = str(v.codigo)
            assert cod_str in codigos_validos or cod_str.startswith("0x")

        # Verificar ordenamiento ascendente por (linea, columna)
        posiciones = [(v.linea, v.columna) for v in viols]
        assert posiciones == sorted(posiciones), f"Violaciones desordenadas en {fpath.name}"

    assert total_violaciones > 0, "El corpus debió detectar violaciones sintácticas"

    # 2. Verificación de determinismo sobre una submuestra de 100 archivos
    submuestra = rng.sample(archivos, 100)
    for fpath in submuestra:
        segunda_pasada = analizar_archivo(fpath)
        esperado = resultados_iniciales[fpath.name]
        actual = [(v.codigo, v.linea, v.columna) for v in segunda_pasada]
        assert actual == esperado, f"Falta de determinismo detectada en {fpath.name}"
