"""Test de integración que verifica la validez del árbol de ejemplos de GAFF."""

from pathlib import Path
from gaff.core.rules import CATALOGO_REGLAS, MAPA_RENUMERACION
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

    archivos_ejemplo = sorted(base_dir.rglob("regla_0x*.*"))
    assert len(archivos_ejemplo) >= 140

    for file_path in archivos_ejemplo:
        code_file = file_path.stem.replace("regla_", "")
        if file_path.suffix == ".h" and code_file not in ("0x5003h", "0x3004h", "0x0035h", "0x301Dh"):
            continue
        subfolder = CATEGORIAS.get(code_file[:4])
        assert subfolder is not None, f"Prefijo no catalogado para {code_file}"
        assert file_path.parent.name == subfolder, f"{file_path} está en carpeta incorrecta"

        cod_nuevo = MAPA_RENUMERACION.get(code_file, code_file)
        viols = analizar_archivo(file_path, reglas_habilitadas={cod_nuevo})
        assert any(v.codigo == cod_nuevo or v.codigo == code_file for v in viols), (
            f"El archivo {file_path} no disparó la regla {cod_nuevo} (archivo: {code_file})"
        )
