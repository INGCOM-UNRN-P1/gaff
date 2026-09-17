"""Test para verificar la existencia y validez del JSON Schema de gaffrc."""

import json
from pathlib import Path
from gaff.core.config import generar_plantilla_gaffrc_json


def test_schema_file_exists_and_valid():
    repo_root = Path(__file__).resolve().parent.parent
    schema_path = repo_root / "schema" / "gaffrc.schema.json"
    assert schema_path.is_file(), f"El archivo {schema_path} debe existir."

    contenido = schema_path.read_text(encoding="utf-8")
    schema = json.loads(contenido)

    assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
    assert "properties" in schema
    props = schema["properties"]

    # Verificar que las claves de plantilla están contempladas en el schema
    plantilla = generar_plantilla_gaffrc_json()
    for key in plantilla.keys():
        assert key in props, f"La clave '{key}' de la configuración debe estar definida en el schema"
