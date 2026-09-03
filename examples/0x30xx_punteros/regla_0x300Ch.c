/*
 * REGLA 0x300Ch: Verificá siempre los límites de los arreglos antes de acceder a sus elementos
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * El acceso fuera de límites de un arreglo (`out-of-bounds`) es un error grave. Los índices deben ser explícitamente validados antes de acceder a un elemento.
 *
 * Ejemplo canónico correcto según cátedra:
 * if (indice >= 0 && indice < TAMANO) { arr[indice] = x; }
 */

void f(void)
{
    int arr[5];
    arr[10] = 42;
}
