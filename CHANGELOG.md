# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.
Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/);
versiones según [SemVer](https://semver.org/lang/es/).

## [0.2.0] - 2026-09-28

Primera versión con registro de cambios; lo anterior está en el historial de git.

### Agregado

- **cli**: cumplir el contrato de línea de comandos de LINEAMIENTOS §3.2 (N-ECO-04) (`57b3bda`)

### Corregido

- **tipos**: dejar mypy sin errores y ejecutarlo en el CI (N-GAFF-03) (`b0708e0`)
- **tipos**: importar los nombres de typing usados en anotaciones (N-ECO-08, N-GAFF-03) (`aa1b058`)
- **dead-store**: no marcar como sobreescritura las asignaciones en ramas de un switch (N-GAFF-05) (`7cea944`)
- **documentacion**: el esqueleto de gaff fix no cuenta como documentación (N-GAFF-02) (`e91f09f`)
- **espaciado**: no tomar los literales como espacios en las reglas de espaciado (N-GAFF-01) (`7779861`)

### Documentación

- agregar el texto de la licencia GPL-3.0-or-later que declara pyproject (N-ECO-06) (`0541024`)
- incorporar manual de uso integral y referencia tecnica (gaff) (`64aa958`)

### Mantenimiento

- **calidad**: verificar errores de Python y dependencias vulnerables (N-ECO-08, N-ECO-13) (`34b78a4`)
- **deps**: mover las dependencias de desarrollo a dependency-groups (N-ECO-07) (`9393dcd`)
