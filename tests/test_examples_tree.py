"""Test de integración que verifica la validez del árbol de ejemplos de GAFF."""

from pathlib import Path
from gaff.core.rules import CATALOGO_REGLAS
from gaff.core.linter import analizar_archivo

CATEGORIAS = {
    "0x00": "0x00xx_sintaxis",
    "0x10": "0x10xx_control",
    "0x20": "0x20xx_funciones",
    "0x30": "0x30xx_punteros",
    "0x40": "0x40xx_archivos",
    "0x50": "0x50xx_compilacion",
}

def test_arbol_ejemplos_completo():
    base_dir = Path(__file__).resolve().parent.parent / "examples"
    assert base_dir.is_dir()

    for code in CATALOGO_REGLAS.keys():
        is_hdr = code in ("0x5003h", "0x3004h", "0x0035h")
        ext = ".h" if is_hdr else ".c"
        subfolder = CATEGORIAS[code[:4]]
        file_path = base_dir / subfolder / f"regla_{code}{ext}"

        assert file_path.is_file(), f"Falta el archivo de ejemplo para {code}: {file_path}"
        viols = analizar_archivo(file_path, reglas_habilitadas={code})
        assert any(v.codigo == code for v in viols), f"El archivo {file_path} no disparó la regla {code}"
