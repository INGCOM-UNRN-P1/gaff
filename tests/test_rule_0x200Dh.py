"""Tests unitarios para la regla 0x200Ch (prohibición de múltiples sentencias return por función)."""

import json
from pathlib import Path
from typer.testing import CliRunner

from gaff.cli import app
from gaff.core.linter import analizar_archivo, ejecutar_linter
from gaff.core.rules import CATALOGO_REGLAS, obtener_regla

runner = CliRunner()


def test_regla_0x200Ch_catalogo():
    """Verifica que la regla 0x200Ch esté correctamente registrada en el catálogo de reglas."""
    assert "0x200Ch" in CATALOGO_REGLAS
    info = obtener_regla("0x200Ch")
    assert info is not None
    assert info["codigo"] == "0x200Ch"
    assert "return" in info["titulo"].lower()
    assert info["categoria"] == "Funciones y Modularización (0x20XX)"


def test_regla_0x200Ch_detecta_dos_returns(tmp_path: Path):
    """Verifica que una función con dos sentencias return genere una violación 0x200Ch."""
    src = tmp_path / "dos_returns.c"
    src.write_text("""
int modulo(int x)
{
    if (x < 0)
    {
        return -x;
    }
    return x;
}
""")
    viols = analizar_archivo(src, reglas_habilitadas={"0x200Ch"})
    assert len(viols) == 1
    v = viols[0]
    assert v.codigo == "0x200Ch"
    assert "modulo" in v.mensaje
    assert "más de un return" in v.mensaje
    assert "2 sentencias 'return'" in v.mensaje
    assert "int modulo(int x)" in v.codigo_linea


def test_regla_0x200Ch_tres_returns(tmp_path: Path):
    """Verifica la detección cuando hay tres sentencias return en la misma función."""
    src = tmp_path / "tres_returns.c"
    src.write_text("""
int clasificar(int x)
{
    if (x > 0)
    {
        return 1;
    }
    if (x < 0)
    {
        return -1;
    }
    return 0;
}
""")
    viols = analizar_archivo(src, reglas_habilitadas={"0x200Ch"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x200Ch"
    assert "clasificar" in viols[0].mensaje
    assert "3 sentencias 'return'" in viols[0].mensaje


def test_regla_0x200Ch_un_solo_return_ok(tmp_path: Path):
    """Verifica que una función con un único return no genere violaciones."""
    src = tmp_path / "un_return.c"
    src.write_text("""
int modulo_con_variable(int x)
{
    int resultado = x;
    if (x < 0)
    {
        resultado = -x;
    }
    return resultado;
}
""")
    viols = analizar_archivo(src, reglas_habilitadas={"0x200Ch"})
    assert len(viols) == 0


def test_regla_0x200Ch_funcion_void_sin_return(tmp_path: Path):
    """Verifica que una función void sin sentencias return no genere violaciones."""
    src = tmp_path / "void_sin_return.c"
    src.write_text("""
void imprimir_mensaje(const char *msg)
{
    // Función sin ningún return
}
""")
    viols = analizar_archivo(src, reglas_habilitadas={"0x200Ch"})
    assert len(viols) == 0


def test_regla_0x200Ch_ignora_comentarios_y_cadenas(tmp_path: Path):
    """Verifica que la palabra 'return' en comentarios o literales de cadena no se compute."""
    src = tmp_path / "comentarios.c"
    src.write_text("""
int test_falso_positivo(void)
{
    // return -1;
    /* return -2; */
    const char *mensaje = "return from function";
    return 0;
}
""")
    viols = analizar_archivo(src, reglas_habilitadas={"0x200Ch"})
    assert len(viols) == 0


def test_regla_0x200Ch_multiples_funciones_aisladas(tmp_path: Path):
    """Verifica que el cómputo de retornos sea aislado por función."""
    src = tmp_path / "multiples_funciones.c"
    src.write_text("""
int funcion_ok(int a, int b)
{
    int suma = a + b;
    return suma;
}

int funcion_invalida(int x)
{
    if (x > 10)
    {
        return 1;
    }
    return 0;
}

void otra_ok(void)
{
    // void
}
""")
    viols = analizar_archivo(src, reglas_habilitadas={"0x200Ch"})
    assert len(viols) == 1
    assert viols[0].codigo == "0x200Ch"
    assert "funcion_invalida" in viols[0].mensaje
    assert "funcion_ok" not in viols[0].mensaje


def test_regla_0x200Ch_exclusion(tmp_path: Path):
    """Verifica que la regla 0x200Ch pueda desactivarse mediante exclusión."""
    src = tmp_path / "excluido.c"
    src.write_text("""
int test(int x)
{
    if (x) return 1;
    return 0;
}
""")
    viols = analizar_archivo(src, reglas_excluidas={"0x200Ch"})
    assert not any(v.codigo == "0x200Ch" for v in viols)


def test_regla_0x200Ch_cli_json(tmp_path: Path):
    """Verifica la ejecución mediante CLI con salida JSON para 0x200Ch."""
    src = tmp_path / "cli_test.c"
    src.write_text("""
int evaluar(int val)
{
    if (val > 0)
    {
        return 1;
    }
    return 0;
}
""")
    res = runner.invoke(app, ["check", str(src), "--json", "-R", "0x200Ch"])
    assert res.exit_code == 1
    data = json.loads(res.stdout)
    assert data["ok"] is False
    assert data["total_violaciones"] == 1
    viol = data["archivos"][0]["violaciones"][0]
    assert viol["codigo"] == "0x200Ch"
    assert "evaluar" in viol["mensaje"]
