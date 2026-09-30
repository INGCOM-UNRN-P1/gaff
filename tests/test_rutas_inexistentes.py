"""`gaff diff` y `gaff lsp-quickfix` con un archivo que no existe son un error de uso (N-ECO-18).

Respondían «No se encontraron líneas C/H modificadas» y `[]` con código 0.
"""

import pytest
from typer.testing import CliRunner

from gaff.cli import app

runner = CliRunner()


@pytest.mark.parametrize("comando", ["diff", "lsp-quickfix"])
def test_un_archivo_que_no_existe_es_un_error_de_uso(comando, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    res = runner.invoke(app, [comando, "no_existe.c"], env={"COLUMNS": "200"})
    assert res.exit_code == 2, res.output
    assert "no_existe.c" in res.output
