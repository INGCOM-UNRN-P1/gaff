/*
 * REGLA 0x1002h: Evitá el uso descontrolado de break y continue; preferí lazos con bandera de control
 *
 * Categoria: Estructuras de Control y Lazos (0x10XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * La cátedra desaconseja el uso generalizado de `break` y `continue` para controlar lazos complejos. En su lugar, preferí usar variables booleanas (banderas) de control en la condición del lazo. **Excepción:** Se admite el uso de `break` para salir anticipadamente de un lazo cuando simplifique la lógica y evite un anidamiento excesivo o banderas redundantes. El uso de `continue` sigue estando estrictamente prohibido debido a que salta partes del código y oscurece el flujo lógico del lazo. (Si tenés dudas, consultá)
 *
 * Ejemplo canónico correcto según cátedra:
 * bool seguir = true;
 * while (i < 10 && seguir) { ... }
 */

void test_violacion(void)
{
    for (int i = 0; i < 10; i++) { if (i == 4) continue; }
}
