# SN P-Lingua Visualizer (MVP)

Aplicación visual en **Python + Streamlit** para cargar/pegar un modelo de **Spiking Neural P Systems (SN P systems)** en formato P-Lingua (`.pli`), intentar compilarlo con una instalación externa de P-Lingua y visualizar la estructura del sistema (neuronas, sinapsis, reglas, input/output).

## Qué hace

- Editor de texto para `.pli` y subida de archivo.
- Compilación vía backend externo (`plingua`) usando `subprocess`.
- Captura y muestra `stdout/stderr/return code` sin ocultar errores.
- Parseo de XML compilado (si existe).
- Parseo parcial de respaldo del texto `.pli` para visualización estática.
- Grafo dirigido de neuronas/sinapsis.
- Tabla de reglas por neurona.
- Simulación opcional con `plingua_sim` y extracción tentativa de tabla por pasos + spike train.
- Exportación de CSV de reglas, HTML de grafo y XML compilado.

## Requisitos

- Python 3.11+
- `uv`
- Instalación externa opcional de P-Lingua/pLinguaCore

## Instalación y ejecución

```bash
uv sync --dev
uv run streamlit run app.py
```

Desde el directorio `spike_p_lingua_visualizer/`.

`requirements.txt` queda como referencia de compatibilidad, pero la definición del
entorno del proyecto vive en `pyproject.toml`.

## Configuración de comandos externos

Variables soportadas:

- `PLINGUA_CMD` (default: `plingua`)
- `PLINGUA_SIM_CMD` (default: `plingua_sim`)

Ejemplo:

```bash
export PLINGUA_CMD="plingua"
export PLINGUA_SIM_CMD="plingua_sim"
```

También puedes usar configuración en YAML/JSON desde el modo diseñador.

## Flujo de compilación

1. Guarda el `.pli` en un archivo temporal.
2. Ejecuta compilación a XML:
   - `plingua input.pli -output_format xml output.xml`
3. Captura `stdout/stderr/return code`.
4. Si `return code = 0` y existe XML, parsea XML.
5. Si falla, muestra error y permite visualización parcial.

## Limitaciones

- La compilación y simulación reales dependen de tener instalado P-Lingua/pLinguaCore.
- El soporte exacto de modelos SN P depende del backend/versiones disponibles.
- El parser propio `.pli` es parcial y está orientado a visualización preliminar, no a validación completa de sintaxis P-Lingua.
- El parseo de reportes de simulación es heurístico y puede requerir adaptar regex al formato real del simulador.

## Estructura

```
spike_p_lingua_visualizer/
  app.py
  src/
    config.py
    models.py
    compiler.py
    parser_pli.py
    parser_xml.py
    graph_builder.py
    simulator.py
    exporters.py
  tests/
    test_parser_pli.py
    test_graph_builder.py
    test_compiler_mock.py
  examples/
    example_snps.pli
    config.example.yaml
  README.md
  requirements.txt
  pyproject.toml
  .python-version
  .env.example
```
