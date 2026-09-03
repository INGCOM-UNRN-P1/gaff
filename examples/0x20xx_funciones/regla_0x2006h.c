/*
 * REGLA 0x2006h: Una aserción por cada función de prueba
 *
 * Categoria: Funciones y Modularización (0x20XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Podés lograr esto creando una función de prueba parametrizada que reciba los argumentos y el resultado esperado, o bien dedicando una función de prueba para cada caso específico de aserción.
 *
 * Ejemplo canónico correcto según cátedra:
 * void test_suma_positivos() { assert(sumar(2, 2) == 4); }
 */

void test_todo() { assert(sumar(2,2)==4); assert(restar(4,2)==2); assert(mult(2,3)==6); }
