"""Violaciones en la taxonomía común (yutani.hallazgos)."""

from gaff.core.linter import ejecutar_linter
from gaff.core.rules import CATALOGO_REGLAS
from gaff.core.taxonomia import CATEGORIA_POR_FAMILIA, categoria


def test_todas_las_familias_tienen_categoria():
    familias = {v.get("directorio") for k, v in CATALOGO_REGLAS.items() if k.startswith("0x")}
    assert familias <= set(CATEGORIA_POR_FAMILIA)


def test_reporte_json_con_hallazgos(tmp_path):
    fuente = tmp_path / "a.c"
    fuente.write_text("int main(void){int i;for(i=0;i<3;i++){continue;}return 0;}\n", encoding="utf-8")
    datos = ejecutar_linter([fuente], config={}).to_dict()
    assert datos["hallazgos"] and len(datos["hallazgos"]) == datos["total_violaciones"]
    h = datos["hallazgos"][0]
    assert h["id"].startswith("gaff:0x") and h["enlace"].startswith("https://ingcom-unrn-p1.github.io/x")
    assert categoria("0x1002h") in ("control", "estilo")
