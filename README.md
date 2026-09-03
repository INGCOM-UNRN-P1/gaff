# 📏 GAFF — Linter Pedagógico de Estilo y Arquitectura Cátedra

GAFF es un linter pedagógico de código C y cabeceras H diseñado para hacer cumplir de forma automatizada las convenciones de nomenclatura, diseño estructurado y arquitectura obligatorias de la cátedra de Programación en C.

---

## 🎯 Alcance

### Qué cubre
- Linter pedagógico de estilo y convenciones arquitectónicas obligatorias de la cátedra, cubriendo 88 reglas de catálogo (`0x00XXh` a `0x50XXh`).
- Validación de sintaxis básica (`0x00XXh`): sangría de 4 espacios, llaves estilo Allman, prolijidad, una variable por línea, macros `#define` en mayúsculas (`0x0013h`), prohibición de identificadores con caracteres no ASCII (`0x0014h`), prohibición del operador coma para sentencias (`0x0015h`) y nombres en `snake_case`.
- Control de flujo y lazos (`0x10XXh`): llaves obligatorias, simplificación de condiciones complejas, erradicación de `goto`, desuso de ternarios, prevención de truthiness implícito, asignaciones en condicionales (`0x100Ah`), control de cuerpos vacíos (`0x100Bh`), exigencia de `break`/fallthrough en `switch` (`0x100Ch`) y prohibición de alterar contadores dentro del cuerpo de un `for` (`0x100Dh`).
- Modularización y funciones (`0x20XXh`): contratos documentados Doxygen con autofix (`0x2003h`), cláusulas de guarda, una única aserción por función de test, límite de 4 parámetros por función (`0x200Bh`), prohibición de retornar punteros a variables de stack (`0x200Ch`) y retornos estructurados.
- Punteros y memoria dinámica (`0x30XXh`): validación inmediata contra `NULL` tras `malloc`, prevención de punteros colgantes (`free(p); p = NULL;`), reallocación segura con puntero temporal (`0x3015h`), prohibición de aritmética sobre `void *` (`0x3012h`), prevención de `sizeof(ptr)` en lugar de `sizeof(*ptr)` (`0x3013h`), control de double free (`0x3014h`), simetría, límites de arreglos y tipado con `size_t`.
- Gestión de archivos y errores (`0x40XXh`): validación estricta de `fopen`, erradicación del antipatrón `while (!feof(f))` (`0x4006h`), prohibición de rutas absolutas locales (`0x4007h`), verificación de retornos de `fread`/`fwrite`, uso de `perror`/`strerror`/`errno`, simetría de recursos y control de offsets en `fseek`.
- Buenas prácticas de compilación (`0x50XXh`): guardas en cabeceras, deduplicación de inclusiones redundantes con autofix (`0x5007h`), prohibición de funciones obsoletas (`gets`, `atoi`) (`0x5008h`), advertencia de división entera a flotante (`0x5009h`), protección de parámetros en macros con paréntesis (`0x500Ah`), inclusión obligatoria de cabeceras estándar para funciones de biblioteca (`0x500Bh`), cadenas seguras y estructura canónica de archivos `.c`.
- Formateo automático de código C mediante archivo de configuración `.clang-format` institucional.

### Qué no cubre (Límites y Delegación)
- Auditoría profunda de vulnerabilidades de seguridad de memoria o llamadas a funciones prohibidas complejas (delegado a `kaneda`).
- Fuzzing de memoria extrema (delegado a `drake`).
- Verificación formal con Frama-C (delegado a `callahan`).

---

## 📋 Requisitos

### Requisitos de Sistema y Entorno
- Multiplataforma. Python >= 3.10.

### Dependencias Externas y Binarios
- `clang-format` (opcional, para modo `--fix`).

### Integración en el Ecosistema
- CLI `gaff`. Plugin registrado en `ripley.plugins` (`style`).

---

## Reglas Principales

- **`0x0001h`**: Identificadores descriptivos (sin variables cortas no canónicas).
- **`0x0007h`**: Nombres de variables y funciones en `snake_case`.
- **`0x3004h`**: Nombres de `typedef` con prefijo `t_` o sufijo `_t`.
- **`0x2004h`**: Prohibición de variables globales mutables fuera de funciones.
- **`0x2005h`**: Longitud máxima de función $\le 50$ líneas.
- **`0x5003h`**: Guardas de inclusión obligatorias en cabeceras `.h` *(Autofix)*.
- **`0x300Dh`**: Prohibición de números mágicos sin constante definida.
- **`0x0004h`**: Espaciado correcto de palabras clave `if (`, `for (` *(Autofix)*.
- **`0x1006h`**: Prohibición de la sentencia `goto`.
- **`0x0009h`**: Longitud de línea $\le 100$ caracteres.
- **`0x0005h`**: Limpieza de trailing whitespace y tabuladores duros *(Autofix)*.

## Uso Rápido

```bash
# 1. Auditar archivos o directorios
gaff check src/ main.c

# 2. Auditar y aplicar correcciones automáticas
gaff check src/ --fix

# 3. Aplicar correcciones automáticas directamente
gaff fix src/

# 4. Salida estructurada JSON para CI/CD
gaff check src/ --json

# 5. Listar o explicar reglas del catálogo
gaff rules
gaff explain 0x0001h
```
