/*
 * REGLA 0x2002h: Las funciones no deben contener printf o scanf, a menos que ese sea su propósito explícito
 *
 * Categoria: Funciones y Modularización (0x20XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Las funciones deben desacoplarse de las operaciones de entrada y salida (I/O) para maximizar su reutilización y facilitar las pruebas unitarias. Si el propósito de una función no es realizar I/O, dichas llamadas deben ser delegadas a otras funciones especializadas del llamador.
 *
 * Ejemplo canónico correcto según cátedra:
 * float calcular_iva(float monto) { return monto * 0.21f; }
 */

int procesar_datos(int x)
{
    printf("Error: %d\n", x);
    return x;
}
