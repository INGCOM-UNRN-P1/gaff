"""gaff arranca en cualquier directorio (N-GAFF-08).

Al importar gaff.core.rules se buscan las reglas del apunte en carpetas vecinas
del directorio actual con `Path.cwd().parents[1]`: en un directorio poco
profundo (/tmp, /, C:\\tp en Windows) ese ancestro no existe y gaff terminaba
en IndexError antes de hacer nada.
"""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("profundidad", [0, 1])
def test_gaff_arranca_en_un_directorio_poco_profundo(tmp_path, profundidad):
    raiz = Path(tmp_path.anchor)  # «/» en POSIX, «C:\\» en Windows
    directorio = raiz if profundidad == 0 else raiz / "tmp"
    if not directorio.is_dir() or len(directorio.resolve().parents) != profundidad:
        pytest.skip(f"no hay un directorio de profundidad {profundidad} para probar")
    res = subprocess.run([sys.executable, "-c", "from gaff.cli import app; app(['--version'])"],
                         cwd=directorio, capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    assert res.stdout.startswith("gaff ")
