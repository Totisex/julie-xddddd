# CLAUDE BIM — Metrados sanitarios desde Revit

Integración **Claude ↔ pyRevit ↔ Revit API** para leer un modelo `.rvt`, clasificar sus
instalaciones sanitarias (desagüe, ventilación, agua fría), cuantificarlas y crear Schedules
dentro del propio proyecto.

> **Regla de oro:** todos los metrados salen de la Revit API (elementos y parámetros reales).
> Si un dato no existe en el modelo se marca `NO DEFINIDO EN EL MODELO` / `POR REVISAR`;
> nunca se estima ni se inventa.

## Estado por fases

| Fase | Contenido | Estado |
|---|---|---|
| **0** | Diagnóstico del entorno y del modelo (solo lectura) | ✅ Herramientas listas — **pendiente de ejecutar en tu equipo** |
| 1 | Arquitectura Claude ↔ pyRevit | 📝 Propuesta en [`docs/ARQUITECTURA_PROPUESTA.md`](docs/ARQUITECTURA_PROPUESTA.md) (no implementada) |
| 2–11 | Conexión, lectura, clasificación, metrados, QA, Schedules, integración, exportación, pruebas | ⏸ No iniciadas — se avanza solo tras verificar la fase anterior |

## Qué se probó y qué NO

* **Probado aquí (Linux, sin Revit):** sintaxis de ambos scripts (pyflakes / parser de PowerShell) y el
  flujo completo del script de pyRevit contra una **API de Revit simulada** (`tests/fake_revit_smoke.py`):
  agregación, serialización JSON, manejo de errores.
* **NO probado:** ninguno de los dos scripts se ha ejecutado contra un Revit, un pyRevit ni un Windows
  reales. Los nombres de la API de Revit están escritos de memoria y protegidos con `try/except`
  (cualquier fallo queda registrado en `errores_del_script` del JSON, no se oculta).
  **Ejecutarlos en tu equipo es precisamente el objetivo de la Fase 0.**

## FASE 0 — cómo ejecutarla

Ambos pasos son de **solo lectura**. No abren transacciones, no guardan el RVT, no cambian la
configuración de Revit/pyRevit/Windows.

### Paso A — Entorno de Windows (PowerShell)

```powershell
# Desde la carpeta ClaudeRevit\diagnostics
powershell -ExecutionPolicy Bypass -File .\Diagnostico_Entorno.ps1
# Opcionales: -ProbarInternet  (TCP 443 a api.anthropic.com / claude.ai)
#             -BuscarEnTodosLosDiscos  (más lento)
```

`-ExecutionPolicy Bypass` vale **solo para esa ejecución**; no cambia la política del sistema.

Qué hace: SO y permisos · Revit instalado (carpetas, versión de `Revit.exe`/`RevitAPI.dll`, procesos
abiertos) · add-ins · pyRevit (carpetas, CLI, `pyrevit env`, extensiones, claves relevantes de la
config) · Python/Node/.NET · puertos candidatos y proxy · Claude Desktop/Claude Code (solo nombres de
servidores MCP) · **localiza** `SANI COMPLETO JULIETTE100*.rvt` en la carpeta `TIP II` y lee, solo
lectura, con qué versión de Revit fue guardado. Las credenciales de proxy se ocultan.

Único efecto: crea `Documentos\ClaudeRevit\reports\` y escribe `diag_entorno_<fecha>.json`.

### Paso B — Modelo abierto en Revit (pyRevit)

1. Haz una **copia** del RVT y ábrela en Revit (no trabajes sobre el original).
2. Copia la carpeta `pyrevit\ClaudeBIM.extension` a `%APPDATA%\pyRevit\Extensions\`
   (ruta habitual de extensiones de usuario de pyRevit; **no la he podido comprobar en tu equipo**).
   Si tras el *Reload* no aparece la pestaña, el Paso A muestra dónde busca tu pyRevit
   (`extensiones_usuario_en_AppData` y `configuracion_relevante`) y lo ajustamos sin tocar nada a ciegas.
3. En Revit: pestaña **pyRevit → Reload**. Aparece la pestaña **ClaudeBIM → Diagnostico Fase 0**.
4. Pulsa el botón. Al terminar, la ventana de salida muestra un resumen y la ruta de
   `diag_modelo_<fecha>.json` (en `Documentos\ClaudeRevit\reports\`).

El script comprueba al final `Document.IsModified` antes/después y lo informa
(`verificacion_solo_lectura`).

### Qué me debes enviar

Los dos JSON (`diag_entorno_*.json` y `diag_modelo_*.json`). Contienen rutas locales, nombre y número
del proyecto y nombres de familias; **revísalos y borra lo que no quieras compartir** (incluye el título de la ventana de Revit y la
salida de `pyrevit env`). No se vuelcan contraseñas: las credenciales de proxy se enmascaran y de la
config de Claude Desktop solo se leen los nombres de servidores MCP.
**Nunca subas el `.rvt` al repositorio** (`.gitignore` ya lo bloquea).

## Qué decidiremos con esos resultados

* Versión de Revit/pyRevit/.NET ⇒ motor de Python y mecanismo de comunicación (ver arquitectura).
* Cómo están clasificados **realmente** tus sistemas (`PipeSystemType`, nombres, abreviaturas) ⇒ regla
  de identificación de desagüe / ventilación / agua fría y estrategia de filtros de los Schedules.
* Si las instalaciones están en el modelo abierto o en un **vínculo RVT** (los colectores no ven
  dentro de vínculos).
* Cobertura de parámetros (sistema, diámetro, longitud, material, nivel) ⇒ cuántos elementos
  caerían en `POR REVISAR` / `INFORMACIÓN INCOMPLETA`.
* Unidades del proyecto y ruta de conversión validada.

## Estructura prevista

```
ClaudeRevit/
├── README.md
├── docs/ARQUITECTURA_PROPUESTA.md
├── diagnostics/Diagnostico_Entorno.ps1          ← Fase 0 (hecho)
├── pyrevit/ClaudeBIM.extension/
│   └── ClaudeBIM.tab/Diagnostico.panel/Fase0.pushbutton/script.py   ← Fase 0 (hecho)
├── tests/fake_revit_smoke.py                    ← prueba con API simulada
├── server/        (Fase 2+)   config/  logs/  reports/
└── pyrevit/ClaudeBIM.extension/ClaudeBIM.tab/Metrados.panel/ ...    (Fases 4–8)
```

`extension.json` (metadatos para distribuir la extensión) se añadirá cuando se publique; para uso
local no es necesario.
