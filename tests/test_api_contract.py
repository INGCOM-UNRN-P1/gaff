"""Test para verificar el contrato de API pública y versionada de GAFF (GAFF-D0901)."""

from pathlib import Path
import gaff
import gaff.api
from gaff.core.linter import analizar_archivo as linter_analizar_archivo


def test_api_version_y_exports():
    assert hasattr(gaff, "API_VERSION")
    assert gaff.API_VERSION == "1.0.0"
    assert gaff.analizar_archivo is gaff.api.analizar_archivo


def test_analizar_archivo_contrato_compatibilidad(tmp_path: Path):
    c_file = tmp_path / "ejemplo.c"
    c_file.write_text("int main(void) { return 0; }\n", encoding="utf-8")

    # Ambas vías (core histórico y api nueva) deben funcionar
    res_api = gaff.api.analizar_archivo(c_file)
    res_core = linter_analizar_archivo(c_file)

    assert isinstance(res_api, list)
    assert isinstance(res_core, list)
    assert len(res_api) == len(res_core)


def test_analizar_codigo_memoria():
    codigo = "int main(void) { int a=1; return a; }\n"
    res = gaff.analizar_codigo(codigo)
    assert isinstance(res, list)
