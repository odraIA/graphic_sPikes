from __future__ import annotations

from pathlib import Path
import tempfile

import pandas as pd
import streamlit as st

from src.compiler import CompilerService
from src.config import AppConfig, load_config, save_config
from src.exporters import export_graph_html, export_rules_csv
from src.graph_builder import build_nx_graph, build_plotly_figure
from src.parser_pli import parse_pli_text
from src.parser_xml import parse_xml_file
from src.simulator import SimulationService

st.set_page_config(page_title="SN P Visualizer", layout="wide")
st.title("SN P Systems Visualizer (MVP)")

mode = st.sidebar.radio("Modo", ["Usuario", "Diseñador"])
config = AppConfig()

if mode == "Diseñador":
    st.sidebar.subheader("Configuración compilador/simulador")
    config.plingua_cmd = st.sidebar.text_input("PLINGUA_CMD", value=config.plingua_cmd)
    config.plingua_sim_cmd = st.sidebar.text_input("PLINGUA_SIM_CMD", value=config.plingua_sim_cmd)
    config.max_steps = st.sidebar.number_input("max_steps", min_value=1, value=config.max_steps)
    config.timeout_ms = st.sidebar.number_input("timeout_ms", min_value=100, value=config.timeout_ms)
    cfg_file = st.sidebar.text_input("Ruta config (yaml/json)", value="examples/config.local.yaml")
    if st.sidebar.button("Guardar configuración"):
        save_config(config, cfg_file)
        st.sidebar.success("Configuración guardada")
    if st.sidebar.button("Cargar configuración"):
        config = load_config(cfg_file)
        st.sidebar.success("Configuración cargada")

editor_text = st.text_area("Código P-Lingua (.pli)", height=260)
uploaded = st.file_uploader("Sube un archivo .pli", type=["pli", "txt"])
if uploaded is not None:
    editor_text = uploaded.read().decode("utf-8")

col1, col2 = st.columns(2)
with col1:
    do_compile = st.button("Compilar")
with col2:
    do_partial = st.button("Visualizar estructura parcial")

system = None
compiled_xml = None
if do_compile and editor_text.strip():
    result = CompilerService(config.plingua_cmd).compile_to_xml(editor_text)
    st.subheader("Resultado de compilación")
    st.write({"success": result.success, "return_code": result.return_code})
    st.text_area("stdout", result.stdout, height=120)
    st.text_area("stderr", result.stderr, height=120)
    if result.success and Path(result.output_xml_path).exists():
        compiled_xml = Path(result.output_xml_path).read_text(encoding="utf-8")
        system = parse_xml_file(result.output_xml_path)
    else:
        st.warning("Compilación no disponible o fallida. Puedes usar la visualización parcial.")

if do_partial and editor_text.strip() and system is None:
    system = parse_pli_text(editor_text)

if system:
    st.subheader("Grafo de neuronas/sinapsis")
    g = build_nx_graph(system)
    st.plotly_chart(build_plotly_figure(g), use_container_width=True)

    rows = []
    for n in system.neurons:
        for r in n.rules:
            rows.append(
                {
                    "neuron_id": n.id,
                    "initial_spikes": n.initial_spikes,
                    "rule_type": r.rule_type,
                    "rule_raw": r.raw,
                    "consumed": r.consumed_spikes,
                    "produced": r.produced_spikes,
                    "delay": r.delay,
                }
            )
    if rows:
        st.subheader("Tabla global de reglas")
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    sim = SimulationService(config.plingua_sim_cmd)
    if st.button("Ejecutar simulación"):
        sim_result = sim.run(
            pli_source=editor_text,
            max_steps=config.max_steps,
            timeout_ms=config.timeout_ms,
            simulator_mode=config.simulator_mode,
            allow_alternative_steps=config.allow_alternative_steps,
            allow_backwards=config.allow_backwards,
        )
        st.write({"success": sim_result.success, "return_code": sim_result.return_code})
        st.text_area("Sim stdout", sim_result.stdout, height=180)
        st.text_area("Sim stderr", sim_result.stderr, height=100)
        if sim_result.step_rows:
            df = pd.DataFrame(sim_result.step_rows)
            st.dataframe(df)
            st.line_chart(df.set_index("step")["output_spike"])
            st.code(sim_result.spike_train or "")

    st.subheader("Exportación")
    if st.button("Exportar CSV reglas"):
        path = export_rules_csv(system, Path(tempfile.gettempdir()) / "snps_rules.csv")
        st.success(f"CSV exportado: {path}")
    if st.button("Exportar grafo HTML"):
        path = export_graph_html(g, Path(tempfile.gettempdir()) / "snps_graph.html")
        st.success(f"HTML exportado: {path}")
    if compiled_xml:
        st.download_button("Descargar XML compilado", data=compiled_xml, file_name="compiled.xml")
