---
title: "Manual de Referencia: gaff"
subtitle: "Gaff — Linter Pedagógico de Estilo Arquitectónico y Convenciones Cátedra con Autofix"
author: "Cátedra de Algoritmos y Programación"
date: "2026-08-31"
---

(manual-gaff)=
# Gaff — Linter Pedagógico de Estilo Arquitectónico y Convenciones Cátedra con Autofix

````{abstract}
**Rol en el ecosistema:** Auditoría y corrección automática de estilo en C: formato Allman, nomenclatura snake_case, espacios en palabras clave, guardas de inclusión y prohibición de variables globales.
````

---

(manual-gaff-proposito)=
## 1. Propósito y Filosofía Pedagógica

La herramienta **`gaff`** forma parte del ecosistema oficial de software de la cátedra. Su diseño sigue principios pedagógicos rigurosos:

1. **Evidencia Técnica Directa**: Todo diagnóstico se fundamenta en la norma ISO C (C11/C23), en el modelo de memoria del sistema o en convenciones arquitectónicas formales.
2. **Acción Correctiva Concreta**: Cada advertencia incluye la prescripción técnica inmediata para resolver el defecto sin recurrir a conjeturas.
3. **Autonomía del Estudiante**: Facilita la autoevaluación local antes de la entrega final del trabajo práctico.
4. **Objetividad Docente**: Estandariza la corrección automática eliminando discrepancias subjetivas en la evaluación.

---

(manual-gaff-instalacion)=
## 2. Instalación y Diagnóstico del Entorno

````{important}
Asegurate de contar con el compilador GCC/Clang y las librerías del sistema instaladas antes de ejecutar `gaff`.
````

Para comprobar el estado de salud de tu entorno de trabajo y las dependencias auxiliares:

````{code-block} bash
# Comprobación de dependencias del sistema
gaff doctor
````

Si se detecta la falta de alguna utilidad (como `gdb`, `valgrind`, `clang-format` o `typst`), el comando indicará el paquete exacto a instalar según tu distribución GNU/Linux o entorno MSYS2.

---

(manual-gaff-comandos)=
## 3. Referencia Completa de Comandos CLI

A continuación se detallan los subcomandos principales disponibles en `gaff`:

| Sintaxis del Comando | Descripción y Efecto |
| :--- | :--- |
| `gaff check src/ include/ [-r / --recursive]` | Audita todas las reglas de estilo de cátedra. |
| `gaff fix src/ include/ [-r / --recursive]` | Aplica correcciones automáticas sobre reglas autofixables. |
| `gaff fix --interactive src/` | Previsualiza los cambios en un diff coloreado antes de aplicar. |
| `gaff rules` | Lista el catálogo oficial de reglas GAFF con sus alias 0xXXXXh. |
| `gaff export-rules -o manual_estilo.md` | Exporta la guía completa de convenciones en Markdown. |
| `gaff init-config` | Genera el archivo canónico `.clang-format` institucional. |

````{tip}
Podés agregar el flag `--json` a la mayoría de los comandos para exportar resultados en formato estructurado o `--md` para generar reportes Markdown para el informe de entrega.
````

---

(manual-gaff-tutorial)=
## 4. Tutorial Paso a Paso con Ejemplos Reales

### Caso de Estudio

Considerá el siguiente fragmento de código representativo:

````{code-block} c
:linenos:
// Código con violaciones de estilo detectadas por GAFF
void FuncionPrueba(int a){ // 0x000Eh (camelCase), 0x000Bh (llave K&R)
    if(a>0){               // 0x0004h (falta espacio en if), 0x000Bh
        int* ptr=&a;       // 0x0006h (asterisco pegado a tipo)
    }
}
````

### Ejecución de la Herramienta

Ejecutá el análisis desde tu terminal:

````{code-block} bash
gaff check src/ include/ [-r / --recursive]
````

### Salida Obtenida en Consola

````{code-block} text
⚠️ Se encontraron 4 violaciones de estilo en src/prueba.c:
┌────────────────────┬─────────┬───────────────────────────────────────┬────────┐
│ Ubicación          │ Regla   │ Mensaje                               │ Fix    │
├────────────────────┼─────────┼───────────────────────────────────────┼────────┤
│ prueba.c:1:6       │ 0x000Eh │ Función 'FuncionPrueba' no snake_case │ manual │
│ prueba.c:1:26      │ 0x000Bh │ Llave '{' K&R en vez de Allman        │ ✓ auto │
│ prueba.c:2:5       │ 0x0004h │ Falta espacio tras 'if'               │ ✓ auto │
│ prueba.c:3:9       │ 0x0006h │ Formato puntero 'int* ptr'            │ ✓ auto │
└────────────────────┴─────────┴───────────────────────────────────────┴────────┘
💡 Ejecutá 'gaff fix src/' para corregir automáticamente los problemas marcados con '✓ auto'.
````

````{note}
Prestá atención a la explicación pedagógica generada: la herramienta no solo señala la línea del problema, sino que explica la causa raíz y el impacto en memoria o arquitectura.
````

---

(manual-gaff-ejercicios)=
## 5. Ejercicios Prácticos y Desafíos

Practicá el uso avanzado de **`gaff`** resolviendo los siguientes ejercicios:

````{exercise} Desafío 1: Auditoría Recursiva de Proyecto
Auditar todo el árbol de carpetas con el nuevo flag `-r`.

**Instrucción de ejecución:**
```bash
gaff check src/ include/ -r
```
````

````{solution} Desafío 1
```bash
gaff check src/ include/ -r
# Verificá que la operación concluya exitosamente con código de salida 0.
```
````

````{exercise} Desafío 2: Auto-Corrección Interactiva
Corregir espaciados y llaves Allman previsualizando el diff.

**Instrucción de ejecución:**
```bash
gaff fix --interactive src/
```
````

````{solution} Desafío 2
```bash
gaff fix --interactive src/
# Revisá el archivo generado o el informe en terminal para confirmar la resolución del problema.
```
````

````{exercise} Desafío 3: Exportación de Catálogo de Reglas
Generar el manual Markdown de reglas de estilo para consulta del equipo.

**Instrucción de ejecución:**
```bash
gaff export-rules -o REGLAS_ESTILO.md
```
````

````{solution} Desafío 3
```bash
gaff export-rules -o REGLAS_ESTILO.md
# Comprobá que la salida confirme la ausencia de advertencias o errores pendientes.
```
````

---

(manual-gaff-makefile)=
## 6. Integración en el Flujo de Trabajo y Makefile

Para incorporar `gaff` de forma automática a tu flujo de desarrollo, agregá la siguiente regla en el `Makefile` de tu proyecto:

````{code-block} makefile
check-gaff:
	@echo "=== Ejecutando verificación con gaff ==="
	gaff check src/ include/

.PHONY: check-gaff
````

Ejecutá `make check-gaff` antes de cada commit para asegurar que tu código conserve el estado de aprobación.
