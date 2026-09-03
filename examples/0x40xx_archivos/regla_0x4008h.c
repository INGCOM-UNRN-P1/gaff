/*
 * REGLA 0x4008h: Validación obligatoria del valor de retorno de fclose() en modo escritura
 *
 * Categoria: Gestión de Archivos y Errores (0x40XX)
 * Autofix disponible: No
 *
 * Descripcion:
 * Al cerrar flujos de archivo abiertos para escritura ("w", "a", "wb"), fclose() puede fallar al vaciar el búfer del sistema operativo. Debe verificarse que retorne distinto de EOF.
 *
 * Ejemplo canónico correcto según cátedra:
 * FILE *f = fopen("log.txt", "w");
 * ...
 * if (fclose(f) == EOF) { perror("Error"); }
 */

void test_violacion(void)
{
    FILE *f = fopen("log.txt", "w");
...
fclose(f); // retorno ignorado en archivo de salida
}
