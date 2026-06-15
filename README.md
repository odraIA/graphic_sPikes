# SN P-Lingua Visualizer

Aplicación académica en **Python + Streamlit** para inspeccionar modelos de **Spiking Neural P Systems (SN P systems)** escritos en un subconjunto simple de P-Lingua (`.pli`). El proyecto puede intentar compilar y simular con ejecutables externos de P-Lingua, pero también funciona sin ellos mediante un parser parcial orientado a visualización.

> Importante: el parser propio no es una validación formal completa de P-Lingua ni sustituye a P-Lingua/pLinguaCore.

## Funcionalidades

- Editor Streamlit con pegado manual, subida UTF-8 de `.pli`, carga de ejemplos y limpieza.
- Estado persistente con `st.session_state` para conservar código, parseo, compilación, simulación y grafo entre reruns.
- Diagnóstico del backend externo: comando configurado, disponibilidad con `shutil.which`, ruta encontrada y mensajes claros si falta P-Lingua.
- Compilación externa a XML con timeout, captura de `stdout`, `stderr`, código de retorno y errores de ejecución.
- Parser parcial tolerante a comentarios `//`, espacios variables, reglas/neuronas multilínea, `->`, olvido con `λ` o `l`, exponentes `a^n` y casos simples `a`.
- Grafo dirigido con NetworkX + Plotly, flechas visibles, estilos para entrada/salida, spikes iniciales y tooltips con reglas.
- Selector de neurona con detalle de reglas, sinapsis entrantes/salientes y metadatos.
- Simulación interna parcial para el subconjunto simple reconocido por el parser cuando no hay backend externo.
- Simulación externa conservada, con timeout, reporte de salida y parseo heurístico de spike train/tabla por pasos cuando `PLINGUA_SIM_CMD` está disponible.
- Descargas reales con `st.download_button`: CSV de reglas, HTML del grafo, XML compilado y JSON parseado.

## Flujo de uso

1. Ejecuta la aplicación desde la raíz del repositorio.
2. Pega código, sube un `.pli` o carga un ejemplo de `examples/`.
3. Usa **Visualizar estructura parcial** para construir el grafo sin depender de P-Lingua.
4. Si tienes P-Lingua instalado, usa **Compilar** para generar XML y parsearlo.
5. Revisa las pestañas: grafo, neuronas/reglas, simulación, diagnóstico y exportación.
6. Descarga los artefactos desde la pestaña **Exportación**.

## Requisitos

- Python 3.11 o superior.
- `uv`.
- P-Lingua/pLinguaCore opcional para compilación y simulación reales.

## Instalación y ejecución

Todos los comandos se ejecutan desde la raíz del proyecto, es decir, el directorio que contiene `app.py`, `pyproject.toml` y `src/`.

```bash
uv sync --dev
uv run streamlit run app.py
```

Para ejecutar tests:

```bash
uv run pytest
```

`pyproject.toml` es la definición principal del entorno. `requirements.txt` se mantiene como referencia de compatibilidad.

## Configuración de P-Lingua

Variables de entorno soportadas:

```bash
export PLINGUA_CMD="$PWD/tools/plingua/plingua"
export PLINGUA_SIM_CMD="$PWD/tools/plingua/plingua_sim"
```

El proyecto incluye esos wrappers para `tools/plingua/MeCoGUI.jar`. Si las variables no están definidas y los wrappers existen, la app los usa por defecto. También se pueden editar en la barra lateral de Streamlit. En modo **Diseñador** se puede guardar/cargar YAML o JSON. La carga maneja archivos inexistentes o contenido inválido sin cerrar la aplicación.

El diagnóstico muestra:

- comando de compilación configurado;
- comando de simulación configurado;
- si cada ejecutable está disponible;
- ruta real encontrada por `shutil.which`;
- mensajes comprensibles cuando no hay backend instalado.

La ausencia de P-Lingua no impide usar la visualización parcial ni la simulación interna parcial. La simulación interna es determinista, limitada al subconjunto simple que reconoce el parser, y no sustituye al simulador oficial.

Nota: los ejemplos incluidos usan el subconjunto parcial de la app y no se envían a pLinguaCore. La app solo invoca `PLINGUA_CMD`/`PLINGUA_SIM_CMD` cuando el texto parece P-Lingua oficial, es decir, cuando contiene una cabecera `@model`. Esto evita errores del backend oficial con construcciones parciales como `a*/a`, que pLinguaCore puede confundir con cierres de comentario `*/`.

## Subconjunto aproximado soportado por el parser parcial

El parser parcial reconoce de forma conservadora:

```text
input: n1;
output: n3;
neuron n1: 2 { a+/a^2 -> a ; 1 | a -> l };
syn(n1,n2);
```

Soporta comentarios `//`, mayúsculas/minúsculas en palabras clave básicas, neuronas multilínea cuando las llaves delimitan el bloque, sinapsis `syn(origen,destino)`, reglas de disparo simples y reglas de olvido con `λ` o `l`. Los bloques no reconocidos y reglas desconocidas se muestran como advertencias.

## Limitaciones reales

- No se implementa un compilador P-Lingua completo.
- No se implementa un simulador interno completo de SN P systems; el fallback interno cubre solo reglas simples reconocidas por el parser parcial.
- El formato exacto de compilación/simulación depende del backend externo instalado.
- El parseo de reportes de simulación es heurístico y puede no reconocer todos los formatos.
- Los ejemplos están diseñados para el subconjunto parcial del parser; no se afirma compatibilidad con una versión concreta de P-Lingua.

## Estructura del proyecto

```text
app.py                    Interfaz Streamlit y coordinación
src/config.py             Configuración y YAML/JSON
src/models.py             Modelos de datos
src/compiler.py           Compilación externa
src/simulator.py          Simulación externa y parser heurístico de reportes
src/parser_pli.py         Parser parcial .pli
src/parser_xml.py         Parser XML simple
src/graph_builder.py      Grafo NetworkX y figura Plotly
src/exporters.py          CSV, HTML y JSON para descargas
tests/                    Tests unitarios
tests/test_*.py
examples/                 Modelos y configuración de ejemplo
```
