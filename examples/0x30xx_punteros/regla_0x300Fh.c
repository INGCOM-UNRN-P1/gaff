/*
 * REGLA 0x300Fh: Liberá la memoria en el orden inverso a su asignación
 *
 * Categoria: Punteros y Gestión de Memoria (0x30XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Esto es crítico en estructuras de datos anidadas, como matrices dinámicas 2D o listas enlazadas, para evitar dejar memoria inaccesible en el heap.
 *
 * Ejemplo canónico correcto según cátedra:
 * free(nodo->nombre);
 * free(nodo);
 */

void liberar_matriz(int **matriz, int n)
{
    free(matriz);
    for (int i = 0; i < n; i++) {
        free(matriz[i]);
    }
}
