from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.compiler import CompilerService
from src.config import AppConfig, load_config, save_config
from src.exporters import graph_html_text, rules_csv_text, system_json_text
from src.graph_builder import build_nx_graph, build_plotly_figure
from src.parser_pli import parse_pli_text
from src.parser_xml import parse_xml_file
from src.plingua_dialect import looks_like_official_plingua
from src.simulator import SimulationService, run_internal_simulation

EXAMPLES_DIR = Path("examples")

st.set_page_config(page_title="Visualizador Spiking", layout="wide")
st.title("Visualizador Spiking")


def init_state() -> None:
    defaults = {
        "editor_text": "",
        "source_name": "manual",
        "system": None,
        "compiled_xml": None,
        "compilation_result": None,
        "simulation_result": None,
        "graph": None,
        "config": AppConfig(),
        "last_processed_text": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def invalidate_if_changed() -> None:
    if st.session_state.editor_text != st.session_state.last_processed_text:
        st.session_state.system = None
        st.session_state.compiled_xml = None
        st.session_state.compilation_result = None
        st.session_state.simulation_result = None
        st.session_state.graph = None


def rule_rows(system):
    return [
        {
            "neuron_id": n.id,
            "initial_spikes": n.initial_spikes,
            "rule_type": r.rule_type,
            "regex": r.regex,
            "consumed": r.consumed_spikes,
            "produced": r.produced_spikes,
            "delay": r.delay,
            "rule_raw": r.raw,
        }
        for n in system.neurons
        for r in n.rules
    ]


init_state()
config: AppConfig = st.session_state.config

with st.sidebar:
    mode = st.radio("Modo", ["Usuario", "Diseñador"])
    st.subheader("Configuración del backend")
    config.plingua_cmd = st.text_input("PLINGUA_CMD", value=config.plingua_cmd)
    config.plingua_sim_cmd = st.text_input(
        "PLINGUA_SIM_CMD", value=config.plingua_sim_cmd
    )
    config.max_steps = int(
        st.number_input("max_steps", min_value=1, value=config.max_steps)
    )
    config.timeout_ms = int(
        st.number_input("timeout_ms simulación", min_value=100, value=config.timeout_ms)
    )
    config.compile_timeout_ms = int(
        st.number_input(
            "timeout_ms compilación", min_value=100, value=config.compile_timeout_ms
        )
    )
    config.simulator_mode = (
        st.text_input("simulator_mode", value=config.simulator_mode or "") or None
    )
    config.allow_alternative_steps = st.checkbox(
        "allow_alternative_steps", value=config.allow_alternative_steps
    )
    config.allow_backwards = st.checkbox(
        "allow_backwards", value=config.allow_backwards
    )
    if mode == "Diseñador":
        cfg_file = st.text_input(
            "Ruta config (yaml/json)", value="examples/config.local.yaml"
        )
        if st.button("Guardar configuración"):
            ok, err = save_config(config, cfg_file)
            st.success("Configuración guardada") if ok else st.error(err)
        if st.button("Cargar configuración"):
            loaded, err = load_config(cfg_file)
            st.session_state.config = loaded
            st.warning(err) if err else st.success("Configuración cargada")
            st.rerun()
    st.subheader("Diagnóstico")
    comp = CompilerService(config.plingua_cmd)
    sim = SimulationService(config.plingua_sim_cmd)
    st.write(
        {
            "compilación": config.plingua_cmd,
            "disponible": comp.is_available(),
            "ruta": comp.executable_path(),
        }
    )
    st.write(
        {
            "simulación": config.plingua_sim_cmd,
            "disponible": sim.is_available(),
            "ruta": sim.executable_path(),
        }
    )
    if not comp.is_available() or not sim.is_available():
        st.info(
            "P-Lingua no parece instalado/configurado. Puedes usar el parser y el simulador interno parcial; la compilación y la simulación oficial requieren el backend externo."
        )

st.subheader("Editor y carga")
examples = sorted(EXAMPLES_DIR.glob("*.pli"))
cols = st.columns([1, 1, 1])
with cols[0]:
    uploaded = st.file_uploader("Sube un archivo .pli", type=["pli", "txt"])
    if uploaded and st.button("Cargar archivo subido"):
        try:
            st.session_state.editor_text = uploaded.getvalue().decode("utf-8")
            st.session_state.source_name = uploaded.name
        except UnicodeDecodeError as exc:
            st.error(f"No se pudo leer como UTF-8: {exc}")
with cols[1]:
    choice = st.selectbox("Ejemplo incluido", [""] + [p.name for p in examples])
    if choice and st.button("Cargar ejemplo"):
        p = EXAMPLES_DIR / choice
        st.session_state.editor_text = p.read_text(encoding="utf-8")
        st.session_state.source_name = p.name
with cols[2]:
    if st.button("Limpiar editor"):
        st.session_state.editor_text = ""
        st.session_state.source_name = "manual"

st.text_area("Código P-Lingua (.pli)", key="editor_text", height=280)
invalidate_if_changed()
st.caption(
    f"Fuente actual: {st.session_state.source_name}. El parser parcial no es una validación formal completa de P-Lingua."
)

c1, c2 = st.columns(2)
if c1.button("Compilar"):
    if not st.session_state.editor_text.strip():
        st.warning("No hay código para compilar.")
    elif not looks_like_official_plingua(st.session_state.editor_text):
        st.info(
            "Este texto usa el subconjunto parcial de la app, no P-Lingua oficial. Se construirá el grafo sin invocar pLinguaCore."
        )
        st.session_state.compilation_result = None
        st.session_state.compiled_xml = None
        st.session_state.system = parse_pli_text(st.session_state.editor_text)
        st.session_state.graph = build_nx_graph(st.session_state.system)
        st.session_state.last_processed_text = st.session_state.editor_text
    else:
        result = CompilerService(config.plingua_cmd).compile_to_xml(
            st.session_state.editor_text, config.compile_timeout_ms
        )
        st.session_state.compilation_result = result
        if result.success and Path(result.output_xml_path).exists():
            st.session_state.compiled_xml = Path(result.output_xml_path).read_text(
                encoding="utf-8"
            )
            st.session_state.system = parse_xml_file(result.output_xml_path)
        else:
            st.session_state.system = parse_pli_text(st.session_state.editor_text)
        st.session_state.graph = build_nx_graph(st.session_state.system)
        st.session_state.last_processed_text = st.session_state.editor_text
if c2.button("Visualizar estructura parcial"):
    if st.session_state.editor_text.strip():
        st.session_state.system = parse_pli_text(st.session_state.editor_text)
        st.session_state.graph = build_nx_graph(st.session_state.system)
        st.session_state.last_processed_text = st.session_state.editor_text
    else:
        st.warning("No hay código para visualizar.")

system = st.session_state.system
graph = st.session_state.graph

tabs = st.tabs(
    ["Grafo", "Neuronas y reglas", "Simulación", "Diagnóstico", "Exportación"]
)
with tabs[0]:
    if graph:
        st.plotly_chart(build_plotly_figure(graph), width="stretch")
        st.caption(
            "Leyenda: azul=normal, verde=entrada, naranja=salida, morado=entrada y salida. Las marcas triangulares indican dirección."
        )
    else:
        st.info("Compila o visualiza parcialmente para construir el grafo.")
with tabs[1]:
    if system:
        with st.expander(
            "Advertencias y diagnóstico del parser", expanded=bool(system.warnings)
        ):
            st.write(system.warnings or ["Sin advertencias."])
            st.write(
                {
                    "bloques_reconocidos": len(system.recognized_blocks),
                    "bloques_ignorados": system.ignored_blocks,
                }
            )
        ids = [n.id for n in system.neurons]
        selected = st.selectbox("Seleccionar neurona", ids) if ids else None
        if selected:
            n = next(n for n in system.neurons if n.id == selected)
            st.write(
                {
                    "ID": n.id,
                    "Etiqueta": n.label,
                    "Spikes iniciales": n.initial_spikes,
                    "Input": n.is_input,
                    "Output": n.is_output,
                    "Entrantes": [
                        s.source for s in system.synapses if s.target == n.id
                    ],
                    "Salientes": [
                        s.target for s in system.synapses if s.source == n.id
                    ],
                }
            )
            st.dataframe(
                pd.DataFrame([r.model_dump() for r in n.rules]), width="stretch"
            )
        rows = rule_rows(system)
        st.subheader("Tabla global de reglas")
        st.dataframe(pd.DataFrame(rows), width="stretch")
    else:
        st.info("No hay sistema parseado.")
with tabs[2]:
    if st.button("Ejecutar simulación"):
        if not st.session_state.editor_text.strip():
            st.warning("No hay código para simular.")
        elif not looks_like_official_plingua(st.session_state.editor_text):
            st.info(
                "Este ejemplo usa el subconjunto parcial de la app; se ejecutará la simulación interna parcial sin llamar a pLinguaCore."
            )
            st.session_state.simulation_result = run_internal_simulation(
                st.session_state.editor_text, config.max_steps
            )
        else:
            sim_service = SimulationService(config.plingua_sim_cmd)
            if sim_service.is_available():
                result = sim_service.run(
                    st.session_state.editor_text,
                    config.max_steps,
                    config.timeout_ms,
                    config.simulator_mode,
                    config.allow_alternative_steps,
                    config.allow_backwards,
                )
                if result.success:
                    st.session_state.simulation_result = result
                else:
                    st.warning(
                        "El simulador externo no pudo interpretar este P-Lingua; se usará la simulación interna parcial."
                    )
                    st.session_state.simulation_result = run_internal_simulation(
                        st.session_state.editor_text, config.max_steps
                    )
                    st.session_state.simulation_result.stderr = (
                        result.stderr or result.stdout
                    )
                    st.session_state.simulation_result.parse_warnings.extend(
                        result.parse_warnings
                    )
            else:
                st.warning(
                    "El simulador externo no está disponible; se usará la simulación interna parcial."
                )
                st.session_state.simulation_result = run_internal_simulation(
                    st.session_state.editor_text, config.max_steps
                )
    sr = st.session_state.simulation_result
    if sr:
        st.write(
            {
                "success": sr.success,
                "return_code": sr.return_code,
                "timeout": sr.timed_out,
                "command": sr.command,
            }
        )
        st.text_area("stdout", sr.stdout, height=160)
        st.text_area("stderr", sr.stderr, height=100)
        for w in sr.parse_warnings:
            st.warning(w)
        if sr.step_rows:
            df = pd.DataFrame(sr.step_rows)
            st.dataframe(df)
            st.line_chart(df.set_index("step")["output_spike"])
        if sr.spike_train:
            st.code(sr.spike_train, language="text")
with tabs[3]:
    cr = st.session_state.compilation_result
    if cr:
        st.write(
            {
                "success": cr.success,
                "return_code": cr.return_code,
                "timeout": cr.timed_out,
                "command": cr.command,
                "input_path": cr.input_path,
                "output_xml_path": cr.output_xml_path,
            }
        )
        st.text_area("stdout compilación", cr.stdout, height=120)
        st.text_area("stderr compilación", cr.stderr, height=120)
    else:
        st.info("Aún no se ha ejecutado compilación.")
with tabs[4]:
    base = (
        Path(st.session_state.source_name).stem
        if st.session_state.source_name != "manual"
        else "snps"
    )
    if system and graph:
        st.download_button(
            "Descargar CSV de reglas",
            rules_csv_text(system).encode("utf-8"),
            file_name=f"{base}_reglas.csv",
            mime="text/csv",
        )
        st.download_button(
            "Descargar HTML del grafo",
            graph_html_text(graph).encode("utf-8"),
            file_name=f"{base}_grafo.html",
            mime="text/html",
        )
        st.download_button(
            "Descargar JSON parseado",
            system_json_text(system).encode("utf-8"),
            file_name=f"{base}_sistema.json",
            mime="application/json",
        )
    if st.session_state.compiled_xml:
        st.download_button(
            "Descargar XML compilado",
            st.session_state.compiled_xml.encode("utf-8"),
            file_name=f"{base}_compilado.xml",
            mime="application/xml",
        )
