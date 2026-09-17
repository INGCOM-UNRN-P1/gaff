"""Tests unitarios para el modo --idkfa en GAFF (preservación intacta de comentarios)."""

import pytest
from pathlib import Path
from typer.testing import CliRunner
from gaff.cli import app
from gaff.core.linter import enmascarar_comentarios_idkfa, desenmascarar_comentarios_idkfa, aplicar_autofix_archivo

runner = CliRunner()


def test_enmascarar_desenmascarar_idkfa():
    codigo = """/*name: Test 1*/
/*var
int a = 10;
int mat[2][2] = { {1, 2}, {3, 4} };
*/
// Comentario de linea con caracteres especiales: // /* " '
char *s = "cadena con /*comentario falso*/ y // tambien";
char c = '"';
/* Comentario multilínea
   con espacios y tabs
	en varias líneas */
"""
    enm, phs = enmascarar_comentarios_idkfa(codigo)
    # Las cadenas literales no deben ser enmascaradas como comentarios
    assert '"cadena con /*comentario falso*/ y // tambien"' in enm
    assert "'\"'" in enm
    # Comentarios deben haberse reemplazado
    assert "/*name: Test 1*/" not in enm
    # Restauración exacta
    restaurado = desenmascarar_comentarios_idkfa(enm, phs)
    assert restaurado == codigo


def test_cli_fix_idkfa_preserva_comentarios(tmp_path: Path):
    archivo = tmp_path / "idkfa_test.c"
    contenido_orig = """/*name: Ejercicio de matrices y punteros*/
/*var
int arr[3] = {10, 20, 30};
int *p = arr;
*/
/*distractors:
    - Opcion A: valor 10
    - Opcion B: error de compilacion
*/
int main(void){
if(1){
return (0);
}
// Comentario extenso que sobrepasa largamente el limite de ochenta columnas para probar clang-format y evitar cualquier reenvuelto o particion de lineas.
return 1;
}
"""
    archivo.write_text(contenido_orig, encoding="utf-8")

    res = runner.invoke(app, ["fix", str(archivo), "--idkfa"])
    assert res.exit_code == 0

    contenido_post = archivo.read_text(encoding="utf-8")

    # El código C adyacente debe haberse corregido (ej: if (1) con Allman)
    assert "if (1)" in contenido_post

    # Los comentarios deben permanecer idénticos byte a byte
    assert "/*name: Ejercicio de matrices y punteros*/" in contenido_post
    assert "/*var\nint arr[3] = {10, 20, 30};\nint *p = arr;\n*/" in contenido_post
    assert "/*distractors:\n    - Opcion A: valor 10\n    - Opcion B: error de compilacion\n*/" in contenido_post
    assert "// Comentario extenso que sobrepasa largamente el limite de ochenta columnas para probar clang-format y evitar cualquier reenvuelto o particion de lineas." in contenido_post


def test_cli_format_idkfa_preserva_comentarios(tmp_path: Path):
    archivo = tmp_path / "idkfa_fmt.c"
    comentario_complejo = """/*STDIN
10 20 30
40 50
*/"""
    comentario_largo = "// " + ("X" * 120)
    codigo = f"""{comentario_complejo}
int suma(int a,int b){{
return a+b;
}}
{comentario_largo}
"""
    archivo.write_text(codigo, encoding="utf-8")

    res = runner.invoke(app, ["format", str(archivo), "--idkfa"])
    assert res.exit_code == 0

    post = archivo.read_text(encoding="utf-8")
    assert comentario_complejo in post
    assert comentario_largo in post


def test_cli_check_fix_idkfa(tmp_path: Path):
    archivo = tmp_path / "check_fix_idkfa.c"
    codigo = """/*name: Solo Check Fix*/
/*opciones
a: uno
b: dos
*/
int main(void){
    if(1){
        return 0;
    }
}
"""
    archivo.write_text(codigo, encoding="utf-8")

    res = runner.invoke(app, ["check", str(archivo), "--fix", "--idkfa"])
    post = archivo.read_text(encoding="utf-8")

    assert "/*name: Solo Check Fix*/" in post
    assert "/*opciones\na: uno\nb: dos\n*/" in post
