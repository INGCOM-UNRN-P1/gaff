"""Tests de verificación para la Fase P0 de estabilización crítica de GAFF."""

from pathlib import Path
import time
from typer.testing import CliRunner

from gaff.cli import app
from gaff.core.linter import analizar_archivo, aplicar_autofix_archivo, ejecutar_linter
from gaff.core.models import ViolacionRegla


runner = CliRunner()


def test_autofix_preserva_literales_de_cadena(tmp_path: Path):
    """Verifica que el autofix no corrompa el contenido de strings con comas, puntos y coma o espacios."""
    src = tmp_path / "literales.c"
    codigo_original = (
        '#include <stdio.h>\n\n'
        'int main(void)\n'
        '{\n'
        '    int a = 1 , b = 2;\n'
        '    printf("a , b ; %d , %d\\n" , a , b);\n'
        '    char c = \' , \';\n'
        '    return 0;\n'
        '}\n'
    )
    src.write_text(codigo_original, encoding="utf-8")

    arreglos = aplicar_autofix_archivo(src)
    assert arreglos > 0

    contenido_despues = src.read_text(encoding="utf-8")
    # Los argumentos y variables deben corregirse
    assert "int a = 1, b = 2;" in contenido_despues
    assert "printf(\"a , b ; %d , %d\\n\", a, b);" in contenido_despues
    # El contenido literal debe conservarse intacto
    assert '"a , b ; %d , %d\\n"' in contenido_despues


def test_autofix_preserva_comentarios_en_linea(tmp_path: Path):
    """Verifica que los comentarios de fin de línea no sufran transformaciones de operadores o espaciado."""
    src = tmp_path / "comentarios.c"
    codigo = (
        'int main(void)\n'
        '{\n'
        '    int x = 10 ; // nota: a , b ; c\n'
        '    return 0;\n'
        '}\n'
    )
    src.write_text(codigo, encoding="utf-8")

    aplicar_autofix_archivo(src)
    contenido = src.read_text(encoding="utf-8")
    assert "int x = 10; // nota: a , b ; c" in contenido


def test_autofix_respeta_reglas_excluidas(tmp_path: Path):
    """Verifica que aplicar_autofix_archivo no modifique reglas explicitamente excluidas."""
    src = tmp_path / "exclusiones.c"
    codigo = (
        'int main(void)\n'
        '{\n'
        '    int x = 10 ;\n'
        '    return (x);\n'
        '}\n'
    )
    src.write_text(codigo, encoding="utf-8")

    # Excluir 0x200Fh / 0x2010h (return sin paréntesis)
    aplicar_autofix_archivo(src, reglas_excluidas={"0x200Fh", "0x2010h"})
    contenido = src.read_text(encoding="utf-8")

    # 0x200Fh no debió aplicarse (se mantiene return (x);)
    assert "return (x);" in contenido
    # 0x000Ah / 0x0019h sí debió aplicarse (int x = 10;)
    assert "int x = 10;" in contenido


def test_autofix_no_escribe_si_no_hay_cambios(tmp_path: Path):
    """Verifica que no se reescriba el archivo si no se aplicaron cambios, preservando mtime."""
    src = tmp_path / "limpio.c"
    codigo = (
        'int main(void)\n'
        '{\n'
        '    int a = 1, b = 2;\n'
        '    return a + b;\n'
        '}\n'
    )
    src.write_text(codigo, encoding="utf-8")
    mtime_inicial = src.stat().st_mtime_ns

    time.sleep(0.01)
    arreglos = aplicar_autofix_archivo(src)
    assert arreglos == 0
    assert src.stat().st_mtime_ns == mtime_inicial


def test_autofix_preserva_encoding_latin1(tmp_path: Path):
    """Verifica que un archivo codificado en latin-1 mantenga su codificación al aplicarse fixes."""
    src = tmp_path / "latin1.c"
    # Contiene caracteres específicos de latin-1
    codigo = "int main(void)\n{\n    // Comentario con acento: año e índice\n    int a = 1 ;\n    return 0;\n}\n"
    src.write_bytes(codigo.encode("latin-1"))

    aplicar_autofix_archivo(src)
    contenido_bytes = src.read_bytes()
    # Debe ser decodificable en latin-1
    texto = contenido_bytes.decode("latin-1")
    assert "int a = 1;" in texto
    assert "año e índice" in texto


def test_cli_fix_con_rules_y_exclude(tmp_path: Path):
    """Verifica que gaff fix acepte --rules y --exclude."""
    src = tmp_path / "cli_fix.c"
    src.write_text(
        "int main(void)\n{\n    int x = 10 ;\n    return (x);\n}\n",
        encoding="utf-8",
    )

    res = runner.invoke(app, ["fix", str(src), "--exclude", "0x200Fh,0x2010h"])
    assert res.exit_code == 0
    contenido = src.read_text(encoding="utf-8")
    assert "return (x);" in contenido
    assert "int x = 10;" in contenido


def test_cli_check_quiet_filtra_advertencias(tmp_path: Path, monkeypatch):
    """Verifica que gaff check --quiet descarte advertencias y sólo reporte errores críticos."""
    src = tmp_path / "warn_only.c"
    src.write_text(
        "int main(void)\n{\n    int a,b = 0;\n    return 0;\n}\n",
        encoding="utf-8",
    )

    # Invocación normal reporta violaciones y sale con 1
    res_normal = runner.invoke(app, ["check", str(src)])
    assert res_normal.exit_code == 1

    # Invocación con --quiet al no haber ERROR crítico debe salir con 0
    res_quiet = runner.invoke(app, ["check", str(src), "--quiet"])
    assert res_quiet.exit_code == 0
