"""`gaff explain-syntax`: equivalencias sintácticas de C, el desazucarado (revisión, 05 §3)."""

import json

from typer.testing import CliRunner

from gaff.cli import app
from gaff.core.desazucarado import explicar

runner = CliRunner()


def _equivalente(codigo: str) -> str:
    (sentencia,) = explicar(codigo)
    return sentencia.equivalente


def _tipos(codigo: str) -> list:
    return [e.tipo for s in explicar(codigo) for e in s.equivalencias]


def test_subindice_flecha_y_asignacion_compuesta():
    assert _equivalente("x = a[i];") == "x = *(a + i);"
    assert _equivalente("x = m[1][2];") == "x = *(*(m + 1) + 2);"
    assert _equivalente("p->sig->v[i] -= 1;") == "*((*(*p).sig).v + i) = *((*(*p).sig).v + i) - 1;"
    assert _equivalente("total *= a + b;") == "total = total * (a + b);"
    # Un índice con un operador de menos precedencia que + va entre paréntesis.
    assert _equivalente("x = a[i << 1];") == "x = *(a + (i << 1));"
    assert _equivalente("x = a[n - 1];") == "x = *(a + n - 1);"


def test_incrementos_como_sentencia_y_dentro_de_una_expresion():
    assert _equivalente("i++;") == "i = i + 1;"
    assert _equivalente("--k;") == "k = k - 1;"
    (sentencia,) = explicar("y = v[i++];")
    assert sentencia.equivalente == "y = *(v + i++);"
    incremento = [e for e in sentencia.equivalencias if e.tipo == "incremento"][0]
    assert "valor anterior" in incremento.advertencia


def test_for_como_while_y_el_continue():
    (sentencia,) = [s for s in explicar("for (int i = 0; i < n; i++) { if (v[i] < 0) continue; }") if "for" in s.original]
    assert sentencia.equivalente.splitlines() == [
        "{", "    int i = 0;", "    while (i < n) {", "        …cuerpo…", "        i = i + 1;", "    }", "}"]
    assert "continue" in sentencia.equivalencias[0].advertencia
    (sin_nada,) = [s for s in explicar("for (;;) { break; }") if "for" in s.original]
    assert sin_nada.equivalente.splitlines()[0] == "while (1) {"
    # Un continue de un bucle anidado no es del for de afuera.
    (afuera, _) = [s for s in explicar("for (i = 0; i < n; i++) { while (x) { continue; } }")
                   if s.original.startswith(("for", "while"))]
    assert afuera.equivalencias[0].advertencia == ""


def test_condiciones_ternario_y_direccion():
    assert [s.equivalente for s in explicar("while (p && p->sig) { }")] == ["while (p != 0 && (*p).sig != 0)"]
    assert [s.equivalente for s in explicar("if (!p) { }")] == ["if (p == 0)"]
    assert _equivalente("x = c > 0 ? a : b;") == "if (c > 0) x = a; else x = b;"
    assert _equivalente("int f(int x) { return x > 0 ? 1 : 0; }") == "if (x > 0) return 1; else return 0;"
    assert _equivalente("q = &v[n - 1];") == "q = (v + n - 1);"


def test_cadenas_y_parametros_arreglo():
    assert _equivalente('char s[] = "ok\\n";') == "char s[] = {'o', 'k', '\\n', '\\0'};"
    assert _equivalente("int f(const int v[], int m[][3], char *argv[]);") == \
        "int f(const int *v, int (*m)[3], char **argv);"
    (firma,) = explicar("int suma(int v[], int n)\n{\n    return 0;\n}\n")
    assert firma.original == "int suma(int v[], int n)" and firma.equivalente == "int suma(int *v, int n)"


def test_sin_azucar_lineas_y_fragmentos():
    assert explicar("int x = 0;\nx = x + 1;\n") == []
    assert _tipos("int a = 1;") == []
    codigo = "void f(int *v)\n{\n    int x = 0;\n    x = v[2];\n    x += 1;\n}\n"
    assert [s.linea for s in explicar(codigo)] == [4, 5]
    assert [s.linea for s in explicar(codigo, linea=5)] == [5]
    # Un fragmento suelto se analiza dentro de una función, sin correr los números de línea.
    assert [s.linea for s in explicar("x = 1;\np->x = a[i];")] == [2]


def test_cli(tmp_path):
    fuente = tmp_path / "suma.c"
    fuente.write_text("int suma(int v[], int n)\n{\n    int t = 0;\n    t += v[0];\n    return t;\n}\n",
                      encoding="utf-8")
    res = runner.invoke(app, ["explain-syntax", str(fuente)])
    assert res.exit_code == 0 and "*(v + 0)" in res.output and "Equivalencias usadas" in res.output
    res = runner.invoke(app, ["explain-syntax", "--code", "p->x = a[i];", "--json"])
    datos = json.loads(res.stdout)
    assert datos["schema_version"] == "1.0.0" and datos["sentencias"][0]["equivalente"] == "(*p).x = *(a + i);"
    assert set(datos["explicaciones"]) == {"flecha", "subindice"}
    res = runner.invoke(app, ["explain-syntax"])
    assert res.exit_code == 2
    res = runner.invoke(app, ["explain-syntax", "--code", "int x = 0;"])
    assert res.exit_code == 0 and "No hay azúcar" in res.output
