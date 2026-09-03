# Árbol de Ejemplos de Reglas Pedagógicas de GAFF

Este directorio contiene un archivo de ejemplo canónico para cada una de las 115 reglas activas del catálogo de `gaff`.

## Estructura por Categorías

- `0x00xx_sintaxis/`: Reglas de sintaxis básica, estilo Allman, sangría de 4 espacios, snake_case, nomenclatura y espaciado intra-línea en operadores y expresiones (34 reglas).
- `0x10xx_control/`: Estructuras de control, delimitación con llaves, lazos estructurados y erradicación de saltos arbitrarios (16 reglas).
- `0x20xx_funciones/`: Modularización, firmas canónicas `(void)`, cláusulas de guarda, contratos Doxygen y alcance `static` (16 reglas).
- `0x30xx_punteros/`: Gestión de memoria dinámica, verificación estricta de `NULL`, prevención de punteros colgantes, límites de arreglos y tipado `size_t` (25 reglas).
- `0x40xx_archivos/`: Manejo de recursos de E/S, validación de `fopen`/`fclose`, verificación de `fread`/`fwrite`, llamadas desacopladas y reporte de errores (10 reglas).
- `0x50xx_compilacion/`: Buenas prácticas de compilación, guardas de cabecera, eliminación de directivas de silenciamiento, prevención de funciones obsoletas y orden canónico (14 reglas).

## Estructura de Cada Archivo

Cada archivo contiene:
1. Encabezado de metadatos con el código hexadecimal, título oficial, categoría pedagógica y disponibilidad de autofix.
2. Descripción conceptual y fundamentación arquitectónica según la cátedra de Algoritmos y Programación I.
3. Ejemplo de código canónico correcto según los lineamientos de la materia.
4. Fragmento de código ejecutable que ejemplifica la infracción y dispara de forma determinística la regla correspondiente al ejecutar `gaff check`.

## Uso

Para verificar un ejemplo específico con GAFF:

```bash
gaff check examples/0x00xx_sintaxis/regla_0x0001h.c
gaff explain 0x0001h
```
