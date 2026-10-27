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


def test_catalogo_dueno_canonico_y_concordancia_0x500a(tmp_path: Path):
    from gaff.core.rules import exportar_catalogo_dict

    cat = exportar_catalogo_dict()
    por_codigo = {r["codigo"]: r for r in cat["reglas"]}
    assert por_codigo["0x5004h"]["dueno"] == "kaneda"
    assert por_codigo["0x5006h"]["dueno"] == "kaneda"
    assert por_codigo["0x5008h"]["dueno"] == "kaneda"
    assert por_codigo["0x500Ah"]["dueno"] == "zhora"
    assert por_codigo["0x1008h"]["dueno"] == "gaff"

    c_ok = tmp_path / "macros_ok.h"
    c_ok.write_text(
        "#ifndef MACROS_OK_H\n#define MACROS_OK_H\n"
        '#define LOG(x) printf("x=%s: %d\\n", #x, x)\n'
        "#endif\n",
        encoding="utf-8",
    )
    v_ok = [v for v in gaff.api.analizar_archivo(c_ok) if v.codigo == "0x500Ah"]
    assert v_ok == []

    c_bad = tmp_path / "macros_bad.h"
    c_bad.write_text(
        "#ifndef MACROS_BAD_H\n#define MACROS_BAD_H\n"
        "#define DOBLE(x) (x + x)\n"
        "#endif\n",
        encoding="utf-8",
    )
    v_bad = [v for v in gaff.api.analizar_archivo(c_bad) if v.codigo == "0x500Ah"]
    assert len(v_bad) == 1
