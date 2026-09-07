"""Tests para la regla 0x0037h / 0x0001h: Identificadores genéricos con sufijo numérico."""

from pathlib import Path
from gaff.core.linter import analizar_archivo
from gaff.core.rules import CATALOGO_REGLAS, obtener_regla


def test_catalogo_contiene_0x0037h():
    """Verifica que la regla 0x0037h esté en el catálogo oficial de GAFF."""
    assert "0x0037h" in CATALOGO_REGLAS
    regla = obtener_regla("0x0037h")
    assert regla is not None
    assert "numero1" in regla["titulo"].lower() or "numérico" in regla["titulo"].lower()


def test_argumentos_con_sufijo_numerico_generico(tmp_path: Path):
    """Detecta parámetros como numero1, num_2, etc."""
    codigo = """
    /**
     * @brief Calcula la suma.
     * @param numero1 Primer valor.
     * @param num_2 Segundo valor.
     * @return int Suma.
     */
    int sumar(int numero1, int num_2)
    {
        return numero1 + num_2;
    }
    """
    fuente = tmp_path / "suma.c"
    fuente.write_text(codigo, encoding="utf-8")

    viols = analizar_archivo(fuente, reglas_habilitadas={"0x0037h"})
    codigos = [v.codigo for v in viols]
    mensajes = [v.mensaje for v in viols]

    assert codigos.count("0x0037h") == 2
    assert any("numero1" in m for m in mensajes)
    assert any("num_2" in m for m in mensajes)


def test_variables_locales_con_sufijo_numerico_generico(tmp_path: Path):
    """Detecta variables locales como numero_1, num1, dato1, val_2, var1."""
    codigo = """
    /**
     * @brief Procesa valores.
     */
    void procesar(void)
    {
        int numero_1 = 10;
        int num1 = 20;
        int dato1 = 30;
        int val_2 = 40;
        int var1 = 50;
        int nro1 = 60;
    }
    """
    fuente = tmp_path / "procesar.c"
    fuente.write_text(codigo, encoding="utf-8")

    viols = analizar_archivo(fuente, reglas_habilitadas={"0x0037h"})
    mensajes = [v.mensaje for v in viols if v.codigo == "0x0037h"]

    assert len(mensajes) == 6
    assert any("numero_1" in m for m in mensajes)
    assert any("num1" in m for m in mensajes)
    assert any("dato1" in m for m in mensajes)
    assert any("val_2" in m for m in mensajes)
    assert any("var1" in m for m in mensajes)
    assert any("nro1" in m for m in mensajes)


def test_variables_de_lazo_con_sufijo_numerico_generico(tmp_path: Path):
    """Detecta variables de lazo como num1 en encabezado for."""
    codigo = """
    /**
     * @brief Itera con variable poco descriptiva.
     */
    void iterar(void)
    {
        for (int num1 = 0; num1 < 10; num1++)
        {
            // lazo
        }
    }
    """
    fuente = tmp_path / "iterar.c"
    fuente.write_text(codigo, encoding="utf-8")

    viols = analizar_archivo(fuente, reglas_habilitadas={"0x0037h"})
    mensajes = [v.mensaje for v in viols if v.codigo == "0x0037h"]

    assert len(mensajes) == 1
    assert "num1" in mensajes[0]


def test_identificadores_validos_no_genericos(tmp_path: Path):
    """Verifica que variables válidas (coordenadas, dominios específicos) no sean marcadas erróneamente."""
    codigo = """
    /**
     * @brief Dibuja línea entre dos coordenadas.
     * @param x1 Coordenada X origen.
     * @param y1 Coordenada Y origen.
     * @param x2 Coordenada X destino.
     * @param y2 Coordenada Y destino.
     */
    void trazar_linea(int x1, int y1, int x2, int y2)
    {
        int num_alumnos = 30;
        int numero_cuenta = 12345;
        int dividendo = 10;
        int divisor = 2;
    }
    """
    fuente = tmp_path / "linea.c"
    fuente.write_text(codigo, encoding="utf-8")

    viols = analizar_archivo(fuente, reglas_habilitadas={"0x0037h"})
    assert len(viols) == 0


def test_deteccion_bajo_regla_0x0001h(tmp_path: Path):
    """Cuando solo está activa 0x0001h, también debe advertir sobre variables genéricas numeradas."""
    codigo = """
    /**
     * @brief Test con 0x0001h.
     */
    void demo(void)
    {
        int numero1 = 1;
        int num_2 = 2;
    }
    """
    fuente = tmp_path / "demo.c"
    fuente.write_text(codigo, encoding="utf-8")

    viols = analizar_archivo(fuente, reglas_habilitadas={"0x0001h"})
    viols_num = [v for v in viols if "sufijo numérico genérico" in v.mensaje]

    assert len(viols_num) == 2
    assert all(v.codigo == "0x0001h" for v in viols_num)


def test_argumentos_con_prefijos_y_sufijos_n_a_y_a_n(tmp_path: Path):
    """Detecta parámetros con combinaciones n_a, a_n, num_a, a_num, numero_a, a_numero."""
    codigo = """
    /**
     * @brief Función de cálculo.
     * @param n_a Primer operando.
     * @param a_n Segundo operando.
     * @param num_a Tercer operando.
     * @param a_num Cuarto operando.
     * @param numero_a Quinto operando.
     * @param a_numero Sexto operando.
     * @return int Resultado.
     */
    int calcular(int n_a, int a_n, int num_a, int a_num, int numero_a, int a_numero)
    {
        return n_a + a_n + num_a + a_num + numero_a + a_numero;
    }
    """
    fuente = tmp_path / "args_afijos.c"
    fuente.write_text(codigo, encoding="utf-8")

    viols = analizar_archivo(fuente, reglas_habilitadas={"0x0037h"})
    mensajes = [v.mensaje for v in viols if v.codigo == "0x0037h"]

    assert len(mensajes) == 6
    assert any("n_a" in m for m in mensajes)
    assert any("a_n" in m for m in mensajes)
    assert any("num_a" in m for m in mensajes)
    assert any("a_num" in m for m in mensajes)
    assert any("numero_a" in m for m in mensajes)
    assert any("a_numero" in m for m in mensajes)


def test_variables_locales_con_prefijos_sufijos_y_numeros(tmp_path: Path):
    """Detecta variables con prefijo/sufijo numérico o de letra (n_a, a_n, n_1, 1_n, n_a_1, na, an)."""
    codigo = """
    /**
     * @brief Procesamiento de datos con variables no descriptivas.
     */
    void procesar_afijos(void)
    {
        int n_a = 1;
        int a_n = 2;
        int n_b = 3;
        int b_n = 4;
        int n_1 = 5;
        int _1_n = 6;
        int n_a_1 = 7;
        int a_n_1 = 8;
        int num_1_a = 9;
        int a_num_1 = 10;
        int na = 11;
        int an = 12;
    }
    """
    fuente = tmp_path / "vars_afijos.c"
    fuente.write_text(codigo, encoding="utf-8")

    viols = analizar_archivo(fuente, reglas_habilitadas={"0x0037h"})
    mensajes = [v.mensaje for v in viols if v.codigo == "0x0037h"]

    assert len(mensajes) == 12
    for var in ("n_a", "a_n", "n_b", "b_n", "n_1", "_1_n", "n_a_1", "a_n_1", "num_1_a", "a_num_1", "na", "an"):
        assert any(var in m for m in mensajes), f"Variable {var} no detectada"


def test_variables_lazo_con_prefijos_y_sufijos(tmp_path: Path):
    """Detecta variables de lazo con afijos como n_a y a_n."""
    codigo = """
    /**
     * @brief Lazos con variables no descriptivas.
     */
    void iterar_afijos(void)
    {
        for (int n_a = 0; n_a < 10; n_a++)
        {
            // lazo 1
        }
        for (int a_n = 0; a_n < 10; a_n++)
        {
            // lazo 2
        }
    }
    """
    fuente = tmp_path / "lazo_afijos.c"
    fuente.write_text(codigo, encoding="utf-8")

    viols = analizar_archivo(fuente, reglas_habilitadas={"0x0037h"})
    mensajes = [v.mensaje for v in viols if v.codigo == "0x0037h"]

    assert len(mensajes) == 2
    assert any("n_a" in m for m in mensajes)
    assert any("a_n" in m for m in mensajes)

