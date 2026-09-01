from pathlib import Path
import tempfile
from gaff.ripley_plugin import GaffPlugin


def test_gaff_plugin_available():
    plugin = GaffPlugin()
    assert plugin.is_available() is True
    assert plugin.name == "style"
    assert plugin.version == "0.1.0"


def test_gaff_plugin_execute():
    plugin = GaffPlugin()
    with tempfile.TemporaryDirectory() as td:
        c_file = Path(td) / "main.c"
        c_file.write_text(
            """#include <stdio.h>
int main(void) {
    int x = 10;
    return 0;
}
"""
        )
        res = plugin.execute(Path(td), {})
        assert "ok" in res
        assert "total_violaciones" in res
        assert "observaciones" in res
        assert isinstance(res["observaciones"], list)
        if res["observaciones"]:
            obs = res["observaciones"][0]
            assert "codigo" in obs
            assert "rule_code" in obs
            assert "rule_name" in obs
            assert "severidad" in obs
            assert "archivo" in obs
            assert "linea" in obs
