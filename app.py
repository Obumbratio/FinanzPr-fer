import re
import time
from datetime import datetime
from typing import Dict, Any, Optional

import streamlit as st
from src.config import settings
from src.agent.orchestrator import FinanzOrchestrator
from src.agent.fast_chat import FastChatCopilot
from src.cloud.serverless_jobs import NebiusServerlessJobRunner
from src.tools.report_tool import ReportGenerator
from src.tools.risk_tool import RiskEngineTool

# ─────────────────────────────────────────────────────────────
# 1. CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinanzPrüfer — Sovereign Due Diligence Console",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─────────────────────────────────────────────────────────────
# 2. INYECCIÓN CSS: NEMOTRON SOVEREIGN CONSOLE
# ─────────────────────────────────────────────────────────────
SOVEREIGN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@700;800&family=JetBrains+Mono:wght@400;500;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --bg: #0A0C09;
    --panel: #0E110C;
    --sunk: #0B0E09;
    --line: #1E241B;
    --hair: #141A11;
    --txt: #AEB6A6;
    --hi: #F0F4EC;
    --dim: #4E5748;
    --mid: #6C7565;
    --green: #76B900;
    --amber: #FFB000;
    --red: #E0533D;
}

/* Reset base Streamlit */
.stApp {
    background-color: var(--bg) !important;
    color: var(--txt) !important;
    font-family: 'Space Grotesk', sans-serif !important;
}

header[data-testid="stHeader"] {
    background: transparent !important;
}

.block-container {
    padding-top: 1rem !important;
    padding-bottom: 2rem !important;
    max-width: 98% !important;
}

/* Tipografía Monoespaciada y Títulos */
.nsc-mono { font-family: 'JetBrains Mono', monospace !important; }
.nsc-title { font-family: 'Archivo', sans-serif !important; font-weight: 800; }

/* Micro-LEDs de Telemetría */
.led {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 6px;
    flex-shrink: 0;
}
.led-green { background: var(--green); box-shadow: 0 0 8px var(--green); }
.led-amber { background: var(--amber); box-shadow: 0 0 8px var(--amber); }
.led-red   { background: var(--red);   box-shadow: 0 0 8px var(--red); }

/* Barra Global Superior de Telemetría */
.telemetry-strip {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--sunk);
    border: 1px solid var(--line);
    border-radius: 2px;
    padding: 8px 16px;
    margin-bottom: 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.04em;
}

.telemetry-cell {
    display: inline-flex;
    align-items: center;
    color: var(--dim);
    margin-right: 14px;
    padding-right: 14px;
    border-right: 1px solid var(--line);
}
.telemetry-cell b { color: #95A08C; font-weight: 500; }
.telemetry-cell.ok b { color: var(--green); }
.telemetry-cell.wait b { color: var(--amber); }

/* Tarjetas Facetadas */
.faceted-box {
    background: var(--panel);
    border: 1px solid var(--line);
    clip-path: polygon(0 0, calc(100% - 11px) 0, 100% 11px, 100% 100%, 0 100%);
    padding: 16px;
    margin-bottom: 14px;
}

/* Gauge Radial de Riesgo */
.gauge-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 12px 0;
}
.radial-dial {
    width: 140px;
    height: 140px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}
.radial-dial-inner {
    width: 114px;
    height: 114px;
    border-radius: 50%;
    background: var(--panel);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}
.score-number {
    font-family: 'JetBrains Mono', monospace;
    font-size: 34px;
    font-weight: 700;
    line-height: 1;
    color: var(--hi);
}
.score-tier {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    letter-spacing: 0.1em;
    margin-top: 4px;
}

/* Barras de Sensores */
.sensor-row {
    margin-bottom: 10px;
}
.sensor-meta {
    display: flex;
    justify-content: space-between;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    margin-bottom: 4px;
    color: var(--dim);
}
.sensor-meta span { color: var(--txt); }
.sensor-track {
    background: var(--sunk);
    height: 6px;
    border: 1px solid var(--line);
    border-radius: 1px;
    overflow: hidden;
}
.sensor-fill {
    height: 100%;
    transition: width 0.4s ease;
}

/* Escalera de Riesgo (Risk Ladder) */
.ladder-row {
    background: var(--sunk);
    border: 1px solid var(--line);
    padding: 8px 12px;
    margin-bottom: 6px;
    border-radius: 2px;
    display: flex;
    align-items: center;
    gap: 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
}
.ladder-bar-bg {
    flex-grow: 1;
    height: 10px;
    background: #0E120D;
    border: 1px solid var(--line);
    position: relative;
}
.ladder-bar-fill {
    height: 100%;
}
.ladder-avg-marker {
    position: absolute;
    top: -2px;
    bottom: -2px;
    width: 2px;
    background: var(--amber);
    box-shadow: 0 0 4px var(--amber);
    z-index: 2;
}

/* Inputs y Botones Nativos */
div[data-testid="stChatInput"] textarea {
    background-color: var(--sunk) !important;
    color: var(--hi) !important;
    border: 1px solid var(--line) !important;
    font-family: 'JetBrains Mono', monospace !important;
}
.stButton>button {
    background: var(--panel) !important;
    color: var(--hi) !important;
    border: 1px solid var(--line) !important;
    font-family: 'JetBrains Mono', monospace !important;
    border-radius: 2px !important;
    font-size: 11px !important;
    text-transform: uppercase;
    transition: all 0.2s;
}
.stButton>button:hover {
    border-color: var(--green) !important;
    color: var(--green) !important;
}
.stDownloadButton>button {
    background: #11180E !important;
    color: var(--green) !important;
    border: 1px solid var(--green) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
}

/* Tabs personalizadas */
button[data-baseweb="tab"] {
    background-color: transparent !important;
    color: var(--dim) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
    letter-spacing: 0.05em !important;
    border-bottom: 2px solid transparent !important;
}
button[aria-selected="true"] {
    color: var(--green) !important;
    border-bottom-color: var(--green) !important;
}
</style>
"""
st.markdown(SOVEREIGN_CSS, unsafe_allow_html=True)

def clean_html(html: str) -> str:
    """Elimina indentación y saltos de línea para evitar que Streamlit interprete HTML como bloques de código Markdown."""
    return "".join(line.strip() for line in html.splitlines())

# ─────────────────────────────────────────────────────────────
# 3. GESTIÓN DE RECURSOS Y ESTADO
# ─────────────────────────────────────────────────────────────
@st.cache_resource
def load_orchestrator():
    return FinanzOrchestrator()

@st.cache_resource
def load_fast_copilot():
    return FastChatCopilot()

@st.cache_resource
def load_batch_runner():
    return NebiusServerlessJobRunner()

@st.cache_resource
def load_risk_tool():
    return RiskEngineTool()

orchestrator = load_orchestrator()
fast_copilot = load_fast_copilot()
batch_runner = load_batch_runner()
risk_tool = load_risk_tool()

# Inicializar sesión
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "**Nemotron Sovereign Console initialized.**\n"
                "I am **FinanzPrüfer**, an institutional financial due diligence and risk planning engine.\n\n"
                "• **Audit Target ($TICKER / Market):** Launches Nemotron 3 Ultra multi-hop ReAct loop (Tavily search, SEC EDGAR, Risk Engine).\n"
                "• **Financial Planning / Theory:** Consult Nemotron Nano directly regarding risk budgeting, portfolio allocation, and macro scenarios."
            )
        }
    ]

if "current_metrics" not in st.session_state:
    st.session_state.current_metrics = None
if "last_report" not in st.session_state:
    st.session_state.last_report = None
if "last_ticker" not in st.session_state:
    st.session_state.last_ticker = None
if "active_job_id" not in st.session_state:
    st.session_state.active_job_id = None

# ─────────────────────────────────────────────────────────────
# 4. RENDERIZADORES HTML DINÁMICOS (SANITIZADOS)
# ─────────────────────────────────────────────────────────────
def render_telemetry_bar(job_status_label: str = "IDLE"):
    html = f"""
    <div class="telemetry-strip">
        <div style="display:flex; align-items:center;">
            <div class="telemetry-cell ok"><span class="led led-green"></span>TOKEN FACTORY: <b>ONLINE</b></div>
            <div class="telemetry-cell ok"><span class="led led-green"></span>NEMOTRON ULTRA: <b>READY</b></div>
            <div class="telemetry-cell ok"><span class="led led-green"></span>NEMOTRON NANO: <b>READY</b></div>
            <div class="telemetry-cell ok"><span class="led led-green"></span>TAVILY: <b>CONN</b></div>
            <div class="telemetry-cell wait"><span class="led led-amber"></span>JOBS QUEUE: <b>{job_status_label}</b></div>
            <div style="display:inline-flex; align-items:center; color:var(--mid);">
                REGIME: <span style="color:var(--hi); margin-left:5px;">[VIX 16.4 · ACCUMULATION]</span>
            </div>
        </div>
        <div>
            <span style="color:var(--dim);">OPEN INFRASTRUCTURE · </span>
            <a href="https://github.com/Obumbratio/FinanzPr-fer" target="_blank" style="color:var(--txt); text-decoration:none;">GITHUB MIT</a>
        </div>
    </div>
    """
    st.markdown(clean_html(html), unsafe_allow_html=True)

def render_gauge(score: float, tier: str) -> str:
    if score >= 70:
        accent_color = "var(--red)"
        tier_label = "CRITICAL / HIGH RISK"
    elif score >= 45:
        accent_color = "var(--amber)"
        tier_label = "MODERATE RISK"
    else:
        accent_color = "var(--green)"
        tier_label = "LOW / CONTROLLED RISK"

    pct = int(score)
    dial_style = f"background: conic-gradient({accent_color} 0% {pct}%, var(--line) {pct}% 100%);"

    html = f"""
    <div class="gauge-container">
        <div class="radial-dial" style="{dial_style}">
            <div class="radial-dial-inner">
                <div class="score-number">{score:.0f}</div>
                <div class="score-tier" style="color:{accent_color};">{tier_label}</div>
            </div>
        </div>
    </div>
    """
    return clean_html(html)

def render_sensor_bars(metrics: Dict[str, Any]) -> str:
    vol_str = metrics.get("annualized_volatility_est", "25.0%")
    short_str = metrics.get("short_interest_est", "2.5%")
    regime = metrics.get("regime", "NORMAL_REGIME")
    insider_sig = metrics.get("insider_alignment", "NEUTRAL")

    vol_val = float(vol_str.replace("%", ""))
    vol_pct = min(int((vol_val / 50.0) * 100), 100)

    short_val = float(short_str.replace("%", ""))
    short_pct = min(int((short_val / 10.0) * 100), 100)

    # Lógica de color y fill para MARKET REGIME
    regime_upper = regime.upper()
    if any(k in regime_upper for k in ["ELEVATED", "PANIC", "BEAR"]):
        regime_color = "var(--red)"
        regime_pct = 85
    elif any(k in regime_upper for k in ["SIDEWAYS", "NORMAL"]):
        regime_color = "var(--amber)"
        regime_pct = 50
    else:  # STABLE, ACCUMULATION, BULL
        regime_color = "var(--green)"
        regime_pct = 70

    insider_pct = 85 if "BEARISH" in insider_sig else (50 if "NEUTRAL" in insider_sig else 20)
    insider_color = "var(--red)" if "BEARISH" in insider_sig else "var(--green)"

    html = f"""
    <div style="margin-top:14px;">
        <div class="sensor-row">
            <div class="sensor-meta"><span>ANNUALIZED VOLATILITY</span><span>{vol_str}</span></div>
            <div class="sensor-track"><div class="sensor-fill" style="width:{vol_pct}%; background:var(--amber);"></div></div>
        </div>
        <div class="sensor-row">
            <div class="sensor-meta"><span>MARKET REGIME</span><span>{regime}</span></div>
            <div class="sensor-track"><div class="sensor-fill" style="width:{regime_pct}%; background:{regime_color};"></div></div>
        </div>
        <div class="sensor-row">
            <div class="sensor-meta"><span>SHORT INTEREST</span><span>{short_str}</span></div>
            <div class="sensor-track"><div class="sensor-fill" style="width:{short_pct}%; background:var(--amber);"></div></div>
        </div>
        <div class="sensor-row">
            <div class="sensor-meta"><span>INSIDER SIGNAL</span><span>{insider_sig}</span></div>
            <div class="sensor-track"><div class="sensor-fill" style="width:{insider_pct}%; background:{insider_color};"></div></div>
        </div>
    </div>
    """
    return clean_html(html)

def render_standby_rail() -> str:
    html = """
    <div class="faceted-box" style="text-align:center; padding:35px 20px;">
        <div class="radial-dial" style="margin:0 auto; width:110px; height:110px; background: conic-gradient(var(--dim) 0% 100%);">
            <div class="radial-dial-inner" style="width:96px; height:96px;">
                <div class="score-number" style="color:var(--dim); font-size:24px;">—</div>
            </div>
        </div>
        <div class="nsc-mono" style="font-size:10px; color:var(--dim); margin-top:14px; letter-spacing:0.1em;">
            SENSOR STANDBY<br><b style="color:var(--txt);">WAITING FOR TARGET</b>
        </div>
        <div style="margin-top:20px; opacity:0.3;">
            <div class="sensor-track" style="margin-bottom:6px;"><div class="sensor-fill" style="width:40%; background:var(--dim);"></div></div>
            <div class="sensor-track" style="margin-bottom:6px;"><div class="sensor-fill" style="width:65%; background:var(--dim);"></div></div>
            <div class="sensor-track"><div class="sensor-fill" style="width:25%; background:var(--dim);"></div></div>
        </div>
    </div>
    """
    return clean_html(html)

def render_memory_card(memory_dict: Optional[Dict[str, Any]]) -> str:
    if not memory_dict:
        return ""
    ticker = memory_dict.get("ticker", "NONE")
    score = memory_dict.get("risk_score", 0.0)
    regime = memory_dict.get("regime", "N/A")

    html = f"""
    <div class="faceted-box" style="border-left: 2px solid var(--green);">
        <div class="nsc-mono" style="font-size:10px; color:var(--dim); letter-spacing:0.08em;">AUDIT CONTEXT SNAPSHOT</div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">
            <div class="nsc-mono" style="font-size:14px; font-weight:700; color:var(--hi);">${ticker}</div>
            <div class="nsc-mono" style="font-size:12px; color:var(--amber);">SCORE: {score:.1f}/100</div>
        </div>
        <div class="nsc-mono" style="font-size:10px; color:var(--mid); margin-top:2px;">Regime: {regime}</div>
    </div>
    """
    return clean_html(html)

# ─────────────────────────────────────────────────────────────
# 5. BARRA SUPERIOR Y NAVEGACIÓN
# ─────────────────────────────────────────────────────────────
render_telemetry_bar(job_status_label="RUNNING" if st.session_state.active_job_id else "IDLE")

tab_terminal, tab_batch = st.tabs([
    "💬 Interactive Terminal & Single Audit",
    "⚡ Nebius Cloud Batch Watchlist"
])

# ─────────────────────────────────────────────────────────────
# 6. PESTAÑA 1: TERMINAL & AUDITORÍA DUAL
# ─────────────────────────────────────────────────────────────
with tab_terminal:
    col_left, col_right = st.columns([65, 35])

    # --- COLUMNA DERECHA: RAIL FIJO DE INSTRUMENTOS ---
    with col_right:
        st.markdown("<div class='nsc-mono' style='font-size:11px; color:var(--dim); margin-bottom:6px;'>TELEMETRY CLUSTER</div>", unsafe_allow_html=True)
        
        if st.session_state.current_metrics:
            m = st.session_state.current_metrics
            gauge_html = render_gauge(m['composite_risk_score'], m['risk_tier'])
            bars_html = render_sensor_bars(m)
            st.markdown(clean_html(f"<div class='faceted-box'>{gauge_html}{bars_html}</div>"), unsafe_allow_html=True)
            
            # Tarjeta de Memoria
            mem_card = render_memory_card(orchestrator.memory.last_audited_entity)
            if mem_card:
                st.markdown(mem_card, unsafe_allow_html=True)

            if st.session_state.last_report:
                st.download_button(
                    label=f"📥 Export Dossier (${st.session_state.last_ticker})",
                    data=st.session_state.last_report,
                    file_name=f"FinanzPrufer_Audit_{st.session_state.last_ticker}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
        else:
            st.markdown(render_standby_rail(), unsafe_allow_html=True)

    # --- COLUMNA IZQUIERDA: STREAM INTERACTIVO ---
    with col_left:
        # Chips de Acción Inmediata
        chip_cols = st.columns([1, 1, 1, 1, 1.8])
        quick_query = None
        if chip_cols[0].button("$NVDA"):
            quick_query = "Audita el riesgo de $NVDA con filings SEC, noticias Tavily y Risk Score."
        if chip_cols[1].button("$TSLA"):
            quick_query = "Audita el riesgo de $TSLA con filings SEC, noticias Tavily y Risk Score."
        if chip_cols[2].button("$MSFT"):
            quick_query = "Audita el riesgo de $MSFT con filings SEC, noticias Tavily y Risk Score."
        if chip_cols[3].button("$PLTR"):
            quick_query = "Audita el riesgo de $PLTR con filings SEC, noticias Tavily y Risk Score."
        if chip_cols[4].button("⚡ Nano · Planificar"):
            quick_query = "Tengo 25 años y $5,000 USD de presupuesto. ¿Cómo estructuro mi presupuesto de riesgo y diversifico sin concentración tóxica?"

        # Contenedor de Historial
        chat_container = st.container(height=480)
        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # Botones de Acción Rápida y Seguimiento
        target_t = st.session_state.last_ticker or "NVDA"
        comp_t = "AMD" if target_t.upper() != "AMD" else "NVDA"
        
        qa_cols = st.columns([1.5, 1.5, 3])
        if qa_cols[0].button(f"📊 Comparar con ${comp_t}", use_container_width=True):
            quick_query = f"Compara ${target_t} con ${comp_t} evaluando sus métricas de riesgo, consenso y fundamentales."
        if qa_cols[1].button("🛡️ Simular Cobertura", use_container_width=True):
            quick_query = f"Simula una estructura de cobertura táctica institucional para proteger una posición en ${target_t} ante un escenario de alta volatilidad."

        user_input = st.chat_input("▍ Enter ticker (e.g. $NVDA) or ask a financial planning question...")
        active_prompt = quick_query or user_input

        if active_prompt:
            st.session_state.messages.append({"role": "user", "content": active_prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(active_prompt)

                with st.chat_message("assistant"):
                    # Detectar intención de auditoría cuantitativa vs. diálogo ágil
                    if fast_copilot.is_complex_query(active_prompt):
                        status_box = st.status("🧠 Nemotron 3 Ultra ReAct Loop Initiated...", expanded=True)
                        try:
                            status_box.write("🔎 [01] tavily_search -> Querying real-time market sentiment & headlines...")
                            time.sleep(0.3)
                            status_box.write("📑 [02] sec_edgar -> Parsing Form 4 insider transactions & 10-K...")
                            time.sleep(0.3)
                            status_box.write("⚙️ [03] risk_engine -> Computing deterministic 4-state volatility metrics...")

                            # Extraer ticker o mapear consultas de mercado general a $SPY
                            tickers_found = re.findall(r"\$([A-Za-z]{1,5})\b", active_prompt)
                            if tickers_found:
                                target_ticker = tickers_found[0].upper()
                            else:
                                macro_triggers = ["mercado", "eeuu", "sp500", "s&p", "macro", "market", "panorama", "fed", "tasas", "inflacion"]
                                if any(w in active_prompt.lower() for w in macro_triggers):
                                    target_ticker = "SPY"
                                else:
                                    known_symbols = ["NVDA", "TSLA", "MSFT", "AAPL", "PLTR", "AMD", "SPY", "QQQ", "DIA"]
                                    target_ticker = next((s for s in known_symbols if s in active_prompt.upper()), "NVDA")

                            # Ejecutar evaluación de riesgo para los instrumentos
                            eval_metrics = risk_tool.evaluate_risk(target_ticker)
                            st.session_state.current_metrics = eval_metrics
                            st.session_state.last_ticker = target_ticker

                            # Inferencia multi-hop con Nemotron 3 Ultra
                            agent_response = orchestrator.run(active_prompt)

                            # Actualizar memoria y generar dossier Markdown
                            orchestrator.memory.store_audit_snapshot(
                                ticker=target_ticker,
                                risk_score=eval_metrics["composite_risk_score"],
                                regime=eval_metrics["regime"],
                                summary=agent_response
                            )

                            dossier_text = ReportGenerator.create_markdown_dossier(
                                ticker=target_ticker,
                                analysis_text=agent_response,
                                user_prompt=active_prompt
                            )
                            st.session_state.last_report = dossier_text

                            status_box.update(label="✅ Full Due Diligence Audit Synthesized", state="complete", expanded=False)
                            st.markdown(agent_response)
                            st.session_state.messages.append({"role": "assistant", "content": agent_response})
                            st.rerun()

                        except Exception as e:
                            status_box.update(label="❌ Agent Execution Interrupted", state="error")
                            st.error(f"Error executing agent loop: {str(e)}")
                    else:
                        # Respuesta rápida / Planificación con Nemotron Nano
                        with st.spinner("⚡ Nemotron Nano synthesizing strategic guidance..."):
                            nano_response = fast_copilot.respond(active_prompt)
                            st.markdown(nano_response)
                            st.session_state.messages.append({"role": "assistant", "content": nano_response})

# ─────────────────────────────────────────────────────────────
# 7. PESTAÑA 2: NEBIUS CLOUD BATCH WATCHLIST
# ─────────────────────────────────────────────────────────────
with tab_batch:
    batch_col1, batch_col2 = st.columns([40, 60])

    with batch_col1:
        st.markdown(clean_html("<div class='faceted-box'><h4 class='nsc-title' style='margin:0 0 10px 0; font-size:15px; color:var(--hi);'>DISPATCH SERVERLESS BATCH JOB</h4></div>"), unsafe_allow_html=True)
        st.caption("Asynchronously audits entire watchlists via background workers inspired by Nebius Serverless Jobs.")

        watchlist_input = st.text_area(
            "Portfolio Tickers (comma separated):",
            value="NVDA, TSLA, MSFT, AAPL, PLTR",
            height=90
        )

        if st.button("🚀 DESPACHAR SERVERLESS BATCH JOB", use_container_width=True):
            clean_list = [x.strip() for x in watchlist_input.split(",") if x.strip()]
            job_id = batch_runner.submit_watchlist_batch_job(clean_list)
            st.session_state.active_job_id = job_id
            st.rerun()

        # Monitoreo de Job Activo
        if st.session_state.active_job_id:
            job_id = st.session_state.active_job_id
            st.markdown(clean_html(f"<div class='faceted-box'><div class='nsc-mono' style='font-size:11px;'>JOB ID: <b>{job_id}</b></div></div>"), unsafe_allow_html=True)
            
            prog_bar = st.progress(0.0)
            status_text = st.empty()

            # Polling reactivo
            while True:
                info = batch_runner.get_job_status(job_id)
                st_val = info["status"]
                pr_str = info["progress"].replace("%", "")
                pr_float = float(pr_str) / 100.0

                prog_bar.progress(pr_float)
                status_text.markdown(clean_html(f"<div class='nsc-mono' style='font-size:10.5px; color:var(--mid);'>STATUS: <span style='color:var(--green);'>{st_val}</span> | ASSETS: {info['processed']}</div>"), unsafe_allow_html=True)

                if st_val in ["COMPLETED", "FAILED"]:
                    break
                time.sleep(1.2)

            st.success("Batch Watchlist audit successfully completed.")

    with batch_col2:
        st.markdown(clean_html("<div class='faceted-box'><h4 class='nsc-title' style='margin:0 0 10px 0; font-size:15px; color:var(--hi);'>PORTFOLIO RISK LADDER</h4></div>"), unsafe_allow_html=True)

        active_job = st.session_state.active_job_id
        if active_job:
            job_results = batch_runner.get_job_results(active_job)
            if job_results:
                # Métricas Agregadas
                scores = [v["risk_score"] for v in job_results.values() if v.get("risk_score") is not None]
                avg_score = sum(scores) / len(scores) if scores else 0.0

                m_c1, m_c2, m_c3 = st.columns(3)
                m_c1.metric("PORTFOLIO WEIGHTED RISK", f"{avg_score:.1f}/100")
                m_c2.metric("ASSETS AUDITED", len(scores))
                m_c3.metric("ELEVATED RISK COUNT", sum(1 for s in scores if s >= 70))

                st.markdown("<div style='margin-top:16px;'>", unsafe_allow_html=True)
                # Renderizado de la escalera de riesgo con marcador de media (sanitizado)
                for ticker, res in sorted(job_results.items(), key=lambda x: x[1].get("risk_score", 0)):
                    sc = res.get("risk_score", 0)
                    fill_color = "var(--red)" if sc >= 70 else ("var(--amber)" if sc >= 45 else "var(--green)")
                    ladder_html = f"""
                    <div class="ladder-row">
                        <div style="width:60px; font-weight:700; color:var(--hi);">${ticker}</div>
                        <div class="ladder-bar-bg">
                            <div class="ladder-bar-fill" style="width:{sc}%; background:{fill_color};"></div>
                            <div class="ladder-avg-marker" style="left:{avg_score}%;" title="Portfolio Average ({avg_score:.1f})"></div>
                        </div>
                        <div style="width:55px; text-align:right; color:{fill_color}; font-weight:700;">{sc:.0f}/100</div>
                    </div>
                    """
                    st.markdown(clean_html(ladder_html), unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

                # Exportación del reporte de cartera
                batch_md = batch_runner.export_batch_markdown(active_job)
                st.download_button(
                    label="📥 Download Consolidated Watchlist Report (.md)",
                    data=batch_md,
                    file_name=f"FinanzPrufer_Watchlist_{active_job}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            else:
                st.caption("Awaiting completion of job execution...")
        else:
            st.caption("No batch job executed yet. Dispatch a watchlist from the left panel to populate the portfolio risk ladder.")
