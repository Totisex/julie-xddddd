# Arquitectura propuesta — Claude ↔ pyRevit ↔ Revit

> **PROPUESTA (Fase 1). No implementada.** Se confirma o ajusta con los resultados de la Fase 0.
> Los puntos marcados **[verificar]** dependen de la versión de Revit/pyRevit y se comprueban
> antes de escribir código que los use.

## 1. Restricción clave: Claude no puede “llamar” a tu Revit desde la nube

Una sesión de Claude en la nube **no alcanza** `127.0.0.1` de tu PC. Por eso el puente debe
iniciarse **desde tu equipo hacia Claude**, no al revés. Opciones:

| | Opción | Cómo funciona | Pros | Contras |
|---|---|---|---|---|
| **A (recomendada)** | **Servidor MCP local** registrado en Claude Desktop o Claude Code local | Claude emite *tool calls* con esquema JSON → proceso Python local (stdio) → HTTP en `127.0.0.1` → pyRevit | La traducción lenguaje natural → comando JSON la hace el propio *tool use* de Claude; sin API key aparte; nada sale de tu red salvo la conversación | Requiere Claude Desktop/Code instalado [verificar con Fase 0] |
| B | Servidor local que llama a la **API de Anthropic** (botón “CONECTAR CLAUDE” dentro de Revit) | Panel en Revit → servidor → API de Anthropic con *tool use* | Todo dentro de Revit | Requiere API key y facturación propias; hay que guardar la clave de forma segura |
| C | **Cola de archivos** JSON en una carpeta local | Claude escribe `peticion.json`; pyRevit la consume y escribe `respuesta.json` | Muy desacoplado, simple de auditar | Lento, sin interactividad |

Se decide en la Fase 2 según qué haya en tu equipo (la sonda del Paso A detecta Claude Desktop,
`claude` CLI, Python, Node y puertos libres).

## 2. Capas

```
Usuario ──lenguaje natural──▶ Claude
                                │  tool call (JSON con esquema)
                                ▼
                    server/  (Python, proceso local)
                      · validators.py  → esquema + lista blanca + nivel de riesgo
                      · commands.py    → catálogo CERRADO de comandos
                      · confirmaciones → 2 pasos para escritura
                                │  HTTP solo en 127.0.0.1 + token de sesión
                                ▼
          pyRevit (dentro de Revit)  — receptor de comandos
                      · registro estático  nombre → función
                      · ExternalEvent / IExternalEventHandler  (hilo principal de Revit)
                                │
                                ▼
                           Revit API  →  modelo .rvt
```

* **Hilo de Revit.** La API de Revit solo puede usarse desde el hilo principal en un contexto
  válido: el receptor encola el comando y lo ejecuta mediante `ExternalEvent`. pyRevit incluye el
  módulo **Routes** que resuelve esto **[verificar con la sonda `modulo_routes_disponible`]**; si no
  está, se implementa un receptor propio con `HttpListener` + `ExternalEvent`
  (la sonda también comprueba `HttpListener.IsSupported` y que se pueda abrir un puerto loopback
  dentro del proceso de Revit).
* **Solo loopback.** Escucha únicamente en `127.0.0.1`, con token aleatorio por sesión guardado en
  `config/*.local.json` (ignorado por git). Nada de `0.0.0.0`.
* **Sin código arbitrario.** No existe ningún camino que ejecute texto recibido: **sin `eval`, sin
  `exec`, sin importar módulos por nombre recibido**. Un comando desconocido o con parámetros fuera
  de esquema se rechaza y se registra.

## 3. Catálogo cerrado de comandos

Claude solo puede pedir estos (el nombre viene de tu especificación; se ampliará por fases):

| Nivel | Comando | Parámetros | Efecto |
|---|---|---|---|
| LECTURA | `GET_ENVIRONMENT` | — | Versiones, documento activo, unidades |
| LECTURA | `ANALYZE_MODEL` | — | Niveles, vistas, categorías, sistemas, familias, tipos, materiales |
| LECTURA | `ANALYZE_SANITARY_SYSTEMS` | — | Clasificación DESAGÜE / VENTILACIÓN / AGUA FRÍA / POR REVISAR con evidencia |
| LECTURA | `GET_DIAMETERS` | `system` | Diámetros presentes |
| LECTURA | `GET_QUANTITIES` | `system`, `group_by` | Metrado (m / und) calculado por la API |
| LECTURA | `FIND_UNASSIGNED` / `FIND_DUPLICATES` / `QUALITY_AUDIT` | — | Hallazgos (nunca corrige) |
| LECTURA→disco | `EXPORT_REPORT` | `format`: csv/xlsx/pdf | Escribe **solo** en `reports/`; no toca el modelo |
| ESCRITURA | `CREATE_BACKUP_COPY` | `name` | `SaveAs` a copia nueva (nunca sobrescribe); el original queda intacto |
| ESCRITURA | `CREATE_SCHEDULES` | `which` (SAN-00…06) | Crea vistas de planificación |
| DESTRUCTIVO | modificar parámetros, eliminar, mover | — | **No se implementan.** Reservado y deshabilitado por defecto |

**Escritura = dos pasos.** El primer llamado devuelve un *plan* (qué se creará, en qué archivo,
cuántos elementos tocaría = 0) y un `confirm_token`; solo un segundo llamado con ese token ejecuta.
Antes de la primera escritura se exige la copia de seguridad (`PROYECTO_METRADOS_SANITARIOS.rvt`).

## 4. Identificación de sistemas (sin fiarse del nombre)

Evidencia, de más a menos fiable (todas se **registran** en el reporte para cada elemento):

1. **Clasificación del sistema MEP** de Revit (`PipeSystemType`: p. ej. `Sanitary`, `Vent`,
   `DomesticColdWater`) — independiente del idioma.
2. **Conectores** (para accesorios y aparatos): `PipeSystemType` y `MEPSystem` de cada conector.
3. **Tipo de sistema / nombre / abreviatura / Pipe Type** frente a sinónimos de
   `config/clasificacion.json` (Desagüe, DES, Sanitary, Drain, DWV · Vent, Ventilación, V ·
   Agua Fría, AF, Cold Water, Potable…). Es evidencia *secundaria*.
4. Contradicción entre señales, o sin señal ⇒ `CLASIFICACIÓN AMBIGUA` / `SIN SISTEMA` / `POR REVISAR`.

**Riesgo conocido [verificar con tus datos]:** muchos modelos usan la misma clasificación
`Sanitary` para desagüe *y* ventilación y los separan solo por nombre/abreviatura. La tabla
“clasificación | tipo de sistema | abreviatura” del diagnóstico lo dirá.

## 5. Schedules: dónde chocan dos requisitos

Los filtros de un Schedule de Revit son **solo AND** y operan sobre campos. Para que
“SAN-01 contenga exclusivamente desagüe” se puede:

* **(a) Filtrar por campo nativo** (`System Classification` o `System Type`) cuando cada grupo
  sanitario corresponde a un valor distinto. No modifica elementos. **Preferida.**
* **(b)** Varios `System Type` por grupo ⇒ un schedule no puede hacer OR; habría que dividir o
  usar un **parámetro compartido** (`SAN_Sistema`) rellenado en los elementos.
  Eso **escribe parámetros de elementos** y contradice “no cambiar parámetros salvo petición
  explícita”: solo se haría con tu autorización expresa y plan previo.

La decisión se toma en la Fase 4 con los datos reales. Hasta entonces **no se escribe ningún parámetro**.

Detalles de creación **[verificar en Fase 8, dentro de un `TransactionGroup` que hace rollback si algo falla]**:
`ViewSchedule.CreateSchedule` por categoría (`OST_PipeCurves`, `OST_PipeFitting`,
`OST_PipeAccessory`, `OST_PlumbingFixtures`), campos por `GetSchedulableFields()`, agrupación con
`ScheduleSortGroupField`, `IsItemized = False`, `ShowGrandTotal`, totales por campo, y formato de
longitud fijado en metros por campo (`SetFormatOptions`) para que el resultado no dependa de las
unidades del proyecto.

## 6. Unidades

Siempre con la API (`UnitUtils.ConvertFromInternalUnits` con `UnitTypeId`, o `DisplayUnitType`
en Revit ≤ 2021), **nunca** con factores manuales. El diagnóstico imprime una prueba de la ruta
de conversión y la unidad del proyecto.

## 7. Verificación cruzada (“reporte = Schedules”)

El metrado calculado en Python se compara con el texto de las celdas de cada Schedule creado
(`ViewSchedule.GetTableData()`). Cualquier diferencia se reporta como **INCONSISTENCIA DETECTADA**
(ElementId, parámetro, valor, problema, recomendación) y no se corrige automáticamente.

## 8. Transacciones, errores y logs

Lectura: sin `Transaction`. Escritura: `TransactionGroup` + `Transaction`; si hay excepción ⇒
rollback del grupo, error en `logs/`, mensaje al usuario, modelo sin cambios parciales.

## 9. Evitar duplicados

Clave primaria `ElementId` (y `UniqueId` como respaldo); cada elemento se procesa una vez.
Detección (sin borrar): geometría coincidente/superpuesta, conectores libres, sin sistema,
parámetros incompletos, clasificación ambigua. Alcance de vínculos RVT: se decide con el
diagnóstico (los colectores no ven dentro de vínculos).
