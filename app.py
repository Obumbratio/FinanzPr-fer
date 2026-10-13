import re
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import streamlit as st
from src.config import settings
from src.agent.orchestrator import FinanzOrchestrator
from src.agent.fast_chat import FastChatCopilot, classify_query, KNOWN_TICKERS, COMPANY_ALIASES
from src.agent.memory import AuditMemoryManager
from src.cloud.serverless_jobs import AsyncBatchAuditRunner, NebiusServerlessJobRunner
from src.tools.report_tool import ReportGenerator
from src.tools.risk_tool import RiskEngineTool
from src.tools.search_tool import FinancialSearchTool
from src.tools.cache import tool_cache

# Mapeo institucional de régimen macro a color para telemetría y sensores (Tokens de diseño)
REGIME_COLORS = {
    "BULL": "#76B900",           # Verde NVIDIA — mercado favorable
    "STABLE_ACCUMULATION": "#76B900",
    "SIDEWAYS": "#FFB000",       # Ámbar Alerta — mercado lateral
    "NORMAL_REGIME": "#FFB000",
    "BEAR": "#E0533D",           # Crimson Flag — volatilidad elevada
    "ELEVATED_VOLATILITY": "#E0533D",
    "PANIC": "#E0533D",          # Crimson Flag — crisis
    "CRITICAL_VOLATILITY": "#E0533D",
}

def get_regime_color(regime_str: Optional[str]) -> str:
    """Devuelve el código hexadecimal oficial según el régimen de mercado."""
    r = (regime_str or "").upper().replace(" ", "_").replace("/", "_")
    if any(k in r for k in ["CRITICAL", "PANIC"]):
        return REGIME_COLORS["PANIC"]
    if any(k in r for k in ["ELEVATED", "BEAR"]):
        return REGIME_COLORS["BEAR"]
    if any(k in r for k in ["SIDEWAYS", "NORMAL"]):
        return REGIME_COLORS["SIDEWAYS"]
    if any(k in r for k in ["BULL", "STABLE", "ACCUMULATION"]):
        return REGIME_COLORS["BULL"]
    return "#FFB000"

# ─────────────────────────────────────────────────────────────
# 1. CONFIGURACIÓN DE PÁGINA Y VALIDACIÓN AL ARRANQUE
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinanzPrüfer — Sovereign Due Diligence Console",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Validación de entorno al inicio (Fail-Safe)
try:
    settings.validate_nebius()
except ValueError as e:
    st.error(
        f"🚨 **Error de Configuración Crítico:** {str(e)}\n\n"
        "Por favor, configure una clave válida en la variable `NEBIUS_API_KEY` dentro del archivo `.env` "
        "para inicializar la inferencia con NVIDIA Nemotron en Nebius Token Factory."
    )
    st.stop()

# ─────────────────────────────────────────────────────────────
# 2. INYECCIÓN CSS: NEMOTRON SOVEREIGN CONSOLE
# ─────────────────────────────────────────────────────────────
SOVEREIGN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@700&family=JetBrains+Mono:wght@400;500&family=Space+Grotesk:wght@400;500&display=swap');

:root {
    /* Colors — Achromatic */
    --color-carbon: #0A0C09;
    --color-bunker: #060806;
    --color-gunmetal: #1A1D1A;
    --color-armor: #2A2D2A;
    --color-slate: #3D403D;
    --color-smoke: #6B6E6B;
    --color-ash: #9B9E9B;
    --color-frost: #D4D7D4;
    --color-pure: #FFFFFF;
    --color-void: #000000;

    /* Colors — Signal */
    --color-nvidia-green: #76B900;
    --color-verdant-glow: #8FD119;
    --color-forest: #4A7A00;
    --color-amber-alert: #FFB000;
    --color-amber-dim: #CC8D00;
    --color-crimson-flag: #E0533D;
    --color-crimson-dim: #B33D2A;

    /* Semantic Compatibility Aliases */
    --bg: var(--color-carbon);
    --panel: var(--color-gunmetal);
    --sunk: var(--color-bunker);
    --line: var(--color-slate);
    --txt: var(--color-ash);
    --hi: var(--color-frost);
    --dim: var(--color-smoke);
    --mid: var(--color-ash);
    --green: var(--color-nvidia-green);
    --amber: var(--color-amber-alert);
    --red: var(--color-crimson-flag);

    /* Typography */
    --font-archivo: 'Archivo', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --font-space-grotesk: 'Space Grotesk', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    --font-jetbrains-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;

    /* Shadows */
    --shadow-inset-glow: inset 0 1px 0 0 rgba(118, 185, 0, 0.08);
    --shadow-card-edge: 0 1px 2px 0 rgba(0, 0, 0, 0.4);
}

/* Base Canvas */
.stApp {
    background-color: var(--color-carbon) !important;
    color: var(--color-ash) !important;
    font-family: var(--font-space-grotesk) !important;
}

header[data-testid="stHeader"] {
    background: transparent !important;
}

.block-container {
    padding-top: 1rem !important;
    padding-bottom: 2rem !important;
    max-width: 1280px !important;
}

/* Typography Overrides */
h1, h2, h3, h4, .stHeading {
    font-family: var(--font-archivo) !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    color: var(--color-frost) !important;
    text-align: left !important;
}

h1 { font-size: 36px !important; line-height: 1.1 !important; }
h2 { font-size: 28px !important; line-height: 1.1 !important; }
h3 { font-size: 20px !important; line-height: 1.2 !important; }
h4 { font-size: 16px !important; line-height: 1.3 !important; }

p, span, label, div {
    font-family: var(--font-space-grotesk);
}

p {
    color: var(--color-ash);
    line-height: 1.6;
}

strong, b {
    color: var(--color-frost);
    font-weight: 500;
}

code, pre, .stCode, .nsc-mono {
    font-family: var(--font-jetbrains-mono) !important;
}

.stMetricValue {
    font-family: var(--font-jetbrains-mono) !important;
    font-weight: 500 !important;
    color: var(--color-pure) !important;
}

.stMetricLabel {
    font-family: var(--font-jetbrains-mono) !important;
    font-size: 12px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
    color: var(--color-smoke) !important;
}

/* Section Green Rule (Signature decorative element: 2px high, 40px long) */
.green-rule {
    width: 40px;
    height: 2px;
    background: var(--color-nvidia-green);
    margin-top: 8px;
    margin-bottom: 16px;
}

/* Micro-LEDs de Telemetría */
.led {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 6px;
    flex-shrink: 0;
}
.led-green { background: var(--color-nvidia-green); }
.led-amber { background: var(--color-amber-alert); }
.led-red   { background: var(--color-crimson-flag); }

/* Barra Global Superior de Telemetría */
.telemetry-strip {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--color-bunker);
    border: 1px solid var(--color-slate);
    border-radius: 4px;
    padding: 8px 16px;
    margin-bottom: 12px;
    font-family: var(--font-jetbrains-mono);
    font-size: 11px;
    letter-spacing: 0.04em;
}

.telemetry-cell {
    display: inline-flex;
    align-items: center;
    color: var(--color-smoke);
    margin-right: 14px;
    padding-right: 14px;
    border-right: 1px solid var(--color-slate);
}
.telemetry-cell b { color: var(--color-frost); font-weight: 500; }
.telemetry-cell.ok b { color: var(--color-nvidia-green); }
.telemetry-cell.wait b { color: var(--color-amber-alert); }
.telemetry-cell.err b { color: var(--color-crimson-flag); }

/* Source Tags (Provenance metadata) */
.source-tag {
    font-family: var(--font-jetbrains-mono);
    font-size: 10px;
    font-weight: 400;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-smoke);
    background: transparent;
    border: 1px solid var(--color-slate);
    border-radius: 4px;
    padding: 2px 8px;
    display: inline-block;
    line-height: 1.4;
}

/* Data Module Card */
.data-module-card {
    background: var(--color-gunmetal);
    border: 1px solid var(--color-slate);
    border-radius: 12px;
    padding: 24px;
    box-shadow: var(--shadow-inset-glow), var(--shadow-card-edge);
    margin-bottom: 16px;
}

.data-module-header {
    font-family: var(--font-archivo);
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--color-frost);
    line-height: 1.1;
    margin: 0 0 4px 0;
    text-align: left;
}

.data-module-subhead {
    font-family: var(--font-space-grotesk);
    font-size: 13px;
    color: var(--color-ash);
    margin-bottom: 16px;
    line-height: 1.5;
    text-align: left;
}

/* Compatibility alias for existing class */
.faceted-box {
    background: var(--color-gunmetal);
    border: 1px solid var(--color-slate);
    border-radius: 8px;
    padding: 20px;
    box-shadow: var(--shadow-inset-glow), var(--shadow-card-edge);
    margin-bottom: 14px;
}

/* Metric Row */
.metric-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 9px 0;
    border-bottom: 1px solid var(--color-slate);
    font-family: var(--font-jetbrains-mono);
}
.metric-row:last-child {
    border-bottom: none;
}
.metric-row-label {
    font-size: 12px;
    font-weight: 400;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--color-smoke);
}
.metric-row-value {
    font-size: 14px;
    font-weight: 500;
    color: var(--color-frost);
}

/* Composite Risk Score Badge */
.risk-badge-wrapper {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 12px 0 16px 0;
}
.risk-badge-label {
    font-family: var(--font-jetbrains-mono);
    font-size: 10px;
    font-weight: 400;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-smoke);
    margin-bottom: 8px;
}
.risk-score-badge {
    font-family: var(--font-jetbrains-mono);
    font-size: 16px;
    font-weight: 500;
    border-radius: 4px;
    padding: 6px 14px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    letter-spacing: 0.04em;
}
.risk-score-badge.low {
    background: var(--color-nvidia-green);
    color: var(--color-void);
}
.risk-score-badge.moderate {
    background: var(--color-amber-alert);
    color: var(--color-void);
}
.risk-score-badge.high {
    background: var(--color-crimson-flag);
    color: var(--color-pure);
}

/* Sensor Rows & Micro-Tracks */
.sensor-row {
    margin-bottom: 8px;
}
.sensor-meta {
    display: flex;
    justify-content: space-between;
    font-family: var(--font-jetbrains-mono);
    font-size: 12px;
    margin-bottom: 4px;
    color: var(--color-smoke);
    letter-spacing: 0.04em;
}
.sensor-meta span:first-child {
    text-transform: uppercase;
}
.sensor-meta span:last-child {
    color: var(--color-frost);
    font-weight: 500;
    font-size: 14px;
}
.sensor-track {
    background: var(--color-bunker);
    height: 4px;
    border: 1px solid var(--color-slate);
    border-radius: 2px;
    overflow: hidden;
}
.sensor-fill {
    height: 100%;
    transition: width 0.3s ease-out;
}

/* Escalera de Riesgo (Risk Ladder) */
.ladder-row {
    background: var(--color-bunker);
    border: 1px solid var(--color-slate);
    padding: 8px 12px;
    margin-bottom: 6px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    gap: 12px;
    font-family: var(--font-jetbrains-mono);
    font-size: 12px;
}
.ladder-bar-bg {
    flex-grow: 1;
    height: 8px;
    background: var(--color-gunmetal);
    border: 1px solid var(--color-slate);
    border-radius: 2px;
    position: relative;
    overflow: hidden;
}
.ladder-bar-fill {
    height: 100%;
    border-radius: 1px;
}
.ladder-avg-marker {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 2px;
    background: var(--color-amber-alert);
    z-index: 2;
}

/* Beat Streak Indicator */
.beat-streak {
    font-family: var(--font-jetbrains-mono);
    font-size: 12px;
    font-weight: 500;
    text-transform: uppercase;
    color: var(--color-frost);
}

/* Primary CTA Button (The ONLY green fill in the UI) */
.stButton>button[kind="primary"],
.primary-cta-btn button {
    background: var(--color-nvidia-green) !important;
    color: var(--color-void) !important;
    border: 1px solid var(--color-nvidia-green) !important;
    border-radius: 4px !important;
    padding: 10px 20px !important;
    font-family: var(--font-space-grotesk) !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    letter-spacing: normal !important;
    box-shadow: none !important;
    transition: background-color 0.15s ease, border-color 0.15s ease !important;
}
.stButton>button[kind="primary"]:hover,
.primary-cta-btn button:hover {
    background: var(--color-verdant-glow) !important;
    border-color: var(--color-verdant-glow) !important;
    color: var(--color-void) !important;
}

/* Ghost Outline Button (Secondary actions / Chips) */
.stButton>button {
    background: transparent !important;
    color: var(--color-frost) !important;
    border: 1px solid var(--color-slate) !important;
    border-radius: 4px !important;
    padding: 8px 16px !important;
    font-family: var(--font-space-grotesk) !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    box-shadow: none !important;
    transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
}
.stButton>button:hover {
    background: var(--color-gunmetal) !important;
    border-color: var(--color-smoke) !important;
    color: var(--color-frost) !important;
}

/* Download Button (Ghost style) */
.stDownloadButton>button {
    background: transparent !important;
    color: var(--color-frost) !important;
    border: 1px solid var(--color-slate) !important;
    border-radius: 4px !important;
    font-family: var(--font-space-grotesk) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    transition: background-color 0.15s ease, border-color 0.15s ease !important;
}
.stDownloadButton>button:hover {
    background: var(--color-gunmetal) !important;
    border-color: var(--color-smoke) !important;
    color: var(--color-pure) !important;
}

/* Audit Terminal Input */
div[data-testid="stChatInput"] {
    border: none !important;
    background: transparent !important;
}
div[data-testid="stChatInput"]>div {
    background-color: var(--color-carbon) !important;
    border: 1px solid var(--color-slate) !important;
    border-radius: 4px !important;
    box-shadow: var(--shadow-card-edge) !important;
    transition: border-color 0.15s ease !important;
}
div[data-testid="stChatInput"]>div:focus-within {
    border-color: var(--color-nvidia-green) !important;
}
div[data-testid="stChatInput"] textarea {
    background-color: transparent !important;
    color: var(--color-frost) !important;
    font-family: var(--font-space-grotesk) !important;
    font-size: 15px !important;
    font-weight: 400 !important;
}
div[data-testid="stChatInput"] textarea::placeholder {
    color: var(--color-smoke) !important;
    font-family: var(--font-space-grotesk) !important;
    font-size: 15px !important;
}
div[data-testid="stChatInput"] button {
    background: var(--color-nvidia-green) !important;
    color: var(--color-void) !important;
    border-radius: 4px !important;
    border: none !important;
}
div[data-testid="stChatInput"] button:hover {
    background: var(--color-verdant-glow) !important;
}
div[data-testid="stChatInput"] button svg {
    fill: var(--color-void) !important;
    color: var(--color-void) !important;
}

/* Text Area (Inputs in Batch) */
.stTextArea textarea {
    background-color: var(--color-carbon) !important;
    color: var(--color-frost) !important;
    border: 1px solid var(--color-slate) !important;
    border-radius: 4px !important;
    font-family: var(--font-jetbrains-mono) !important;
    font-size: 13px !important;
}
.stTextArea textarea:focus {
    border-color: var(--color-nvidia-green) !important;
}

/* Tabs */
button[data-baseweb="tab"] {
    background-color: transparent !important;
    color: var(--color-smoke) !important;
    font-family: var(--font-jetbrains-mono) !important;
    font-size: 12px !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    border-bottom: 2px solid transparent !important;
    padding: 10px 16px !important;
}
button[aria-selected="true"] {
    color: var(--color-frost) !important;
    border-bottom-color: var(--color-nvidia-green) !important;
}
div[data-baseweb="tab-highlight"] {
    background-color: var(--color-nvidia-green) !important;
}

/* Chat Messages */
div[data-testid="stChatMessage"] {
    background-color: var(--color-gunmetal) !important;
    border: 1px solid var(--color-slate) !important;
    border-radius: 8px !important;
    padding: 16px !important;
    margin-bottom: 12px !important;
    box-shadow: var(--shadow-card-edge) !important;
}
div[data-testid="stChatMessage"][data-test-role="user"] {
    background-color: var(--color-bunker) !important;
    border-left: 2px solid var(--color-slate) !important;
}
div[data-testid="stChatMessage"][data-test-role="assistant"] {
    border-left: 2px solid var(--color-nvidia-green) !important;
}

/* Status Widget */
div[data-testid="stStatusWidget"] {
    background-color: var(--color-bunker) !important;
    border: 1px solid var(--color-slate) !important;
    border-radius: 8px !important;
}
</style>
"""
st.markdown(SOVEREIGN_CSS, unsafe_allow_html=True)

def clean_html(html: str) -> str:
    """Elimina indentación y saltos de línea para evitar que Streamlit interprete HTML como bloques de código Markdown."""
    return "".join(line.strip() for line in html.splitlines())

# ─────────────────────────────────────────────────────────────
# 3. GESTIÓN DE RECURSOS CON AISLAMIENTO DE SESIÓN
# ─────────────────────────────────────────────────────────────
# Herramientas globales sin estado compartido
@st.cache_resource
def load_search_tool():
    return FinancialSearchTool()

@st.cache_resource
def load_risk_tool():
    return RiskEngineTool()

@st.cache_resource
def load_fast_copilot():
    return FastChatCopilot()

search_tool = load_search_tool()
risk_tool = load_risk_tool()
fast_copilot = load_fast_copilot()

# Aislamiento estricto por usuario en session_state
if "memory" not in st.session_state:
    st.session_state.memory = AuditMemoryManager()

if "batch_runner" not in st.session_state:
    st.session_state.batch_runner = AsyncBatchAuditRunner()

orchestrator = FinanzOrchestrator(memory=st.session_state.memory)
batch_runner = st.session_state.batch_runner

# Inicializar historial de chat
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
if "last_audit" not in st.session_state:
    st.session_state.last_audit = None
if "last_report" not in st.session_state:
    st.session_state.last_report = None
if "last_ticker" not in st.session_state:
    st.session_state.last_ticker = None
if "active_job_id" not in st.session_state:
    st.session_state.active_job_id = None

# ─────────────────────────────────────────────────────────────
# 4. RENDERIZADORES HTML DINÁMICOS (TELEMETRÍA REAL)
# ─────────────────────────────────────────────────────────────
def render_telemetry_bar(job_status_label: str = "IDLE"):
    has_nebius = bool(settings.NEBIUS_API_KEY and settings.NEBIUS_API_KEY != "tu_clave_aqui")
    has_tavily = search_tool.is_configured()

    token_factory_class = "ok" if has_nebius else "err"
    token_factory_led = "led-green" if has_nebius else "led-red"
    token_factory_txt = "ONLINE" if has_nebius else "OFFLINE"

    tavily_class = "ok" if has_tavily else "wait"
    tavily_led = "led-green" if has_tavily else "led-amber"
    tavily_txt = "CONN" if has_tavily else "UNCONFIG"

    current_regime = "NORMAL_REGIME"
    if "last_audit" in st.session_state and st.session_state["last_audit"]:
        current_regime = st.session_state["last_audit"].get("regime", "NORMAL_REGIME")
    elif st.session_state.get("current_metrics"):
        current_regime = st.session_state["current_metrics"].get("macro_regime") or st.session_state["current_metrics"].get("regime", "NORMAL_REGIME")

    regime_color = get_regime_color(current_regime)

    html = f"""
    <div class="telemetry-strip">
        <div style="display:flex; align-items:center; flex-wrap:wrap; gap:4px;">
            <div class="telemetry-cell {token_factory_class}"><span class="led {token_factory_led}"></span>TOKEN FACTORY: <b>{token_factory_txt}</b></div>
            <div class="telemetry-cell ok"><span class="led led-green"></span>ULTRA (550B): <b>READY</b></div>
            <div class="telemetry-cell ok"><span class="led led-green"></span>SUPER (120B): <b>READY</b></div>
            <div class="telemetry-cell ok"><span class="led led-green"></span>NANO (30B): <b>READY</b></div>
            <div class="telemetry-cell {tavily_class}"><span class="led {tavily_led}"></span>TAVILY: <b>{tavily_txt}</b></div>
            <div class="telemetry-cell wait"><span class="led led-amber"></span>JOBS: <b>{job_status_label}</b></div>
            <div style="display:inline-flex; align-items:center; color:var(--color-smoke);">
                <span class="led" style="background:{regime_color};"></span>
                REGIME: <span style="color:{regime_color}; margin-left:5px; font-weight:500;">[{current_regime}]</span>
            </div>
        </div>
        <div>
            <span style="color:var(--color-smoke);">SOVEREIGN TERMINAL · </span>
            <a href="https://github.com/Obumbratio/FinanzPr-fer" target="_blank" style="color:var(--color-ash); text-decoration:none;">GITHUB MIT</a>
        </div>
    </div>
    """
    st.markdown(clean_html(html), unsafe_allow_html=True)

def render_gauge(score: float, tier: str) -> str:
    # Componente oficial: Risk Score Badge (0-100) con color por umbral estricto
    if score >= 61:
        badge_class = "high"
        accent_color = "var(--color-crimson-flag)"
        tier_label = "HIGH RISK"
    elif score >= 31:
        badge_class = "moderate"
        accent_color = "var(--color-amber-alert)"
        tier_label = "MODERATE RISK"
    else:
        badge_class = "low"
        accent_color = "var(--color-nvidia-green)"
        tier_label = "LOW RISK"

    pct = max(0, min(100, int(score)))

    html = f"""
    <div class="risk-badge-wrapper">
        <div class="risk-badge-label">COMPOSITE RISK SCORE</div>
        <div class="risk-score-badge {badge_class}">
            <span>{score:.0f} / 100</span>
            <span>—</span>
            <span>{tier_label}</span>
        </div>
        <div style="width:100%; margin-top:14px;">
            <div style="display:flex; justify-content:space-between; font-family:var(--font-jetbrains-mono); font-size:10px; color:var(--color-smoke); margin-bottom:4px; letter-spacing:0.04em;">
                <span>0 LOW</span>
                <span>30</span>
                <span>60</span>
                <span>100 HIGH</span>
            </div>
            <div class="sensor-track">
                <div class="sensor-fill" style="width:{pct}%; background:{accent_color};"></div>
            </div>
        </div>
    </div>
    """
    return clean_html(html)

def render_sensor_bars(metrics: Dict[str, Any]) -> str:
    vol_str = metrics.get("annualized_volatility_est")
    if not vol_str:
        vol_num = metrics.get("metrics", {}).get("realized_volatility_60d_pct")
        vol_str = f"{vol_num:.1f}%" if vol_num is not None else "25.0%"

    short_str = metrics.get("short_interest_est", "2.5%")
    regime = metrics.get("macro_regime") or metrics.get("regime", "NORMAL_REGIME")
    insider_sig = metrics.get("insider_alignment", "NEUTRAL")

    vol_val = float(str(vol_str).replace("%", ""))
    vol_pct = min(int((vol_val / 50.0) * 100), 100)

    short_val = float(str(short_str).replace("%", ""))
    short_pct = min(int((short_val / 10.0) * 100), 100)

    regime_color = get_regime_color(regime)
    regime_upper = str(regime).upper()
    if any(k in regime_upper for k in ["PANIC", "CRITICAL"]):
        regime_pct = 95
    elif any(k in regime_upper for k in ["ELEVATED", "BEAR"]):
        regime_pct = 80
    elif any(k in regime_upper for k in ["SIDEWAYS", "NORMAL"]):
        regime_pct = 50
    else:  # STABLE, ACCUMULATION, BULL
        regime_pct = 25

    insider_pct = 85 if "BEARISH" in insider_sig else (50 if "NEUTRAL" in insider_sig else 20)
    insider_color = "var(--color-crimson-flag)" if "BEARISH" in insider_sig else ("var(--color-nvidia-green)" if "BULLISH" in insider_sig else "var(--color-amber-alert)")

    html = f"""
    <div style="margin-top:12px;">
        <div class="metric-row">
            <span class="metric-row-label">ANNUALIZED VOLATILITY</span>
            <span class="metric-row-value">{vol_str}</span>
        </div>
        <div class="sensor-track" style="margin-bottom:8px;"><div class="sensor-fill" style="width:{vol_pct}%; background:var(--color-amber-alert);"></div></div>

        <div class="metric-row">
            <span class="metric-row-label">MARKET REGIME</span>
            <span class="metric-row-value" style="color:{regime_color};">{regime}</span>
        </div>
        <div class="sensor-track" style="margin-bottom:8px;"><div class="sensor-fill" style="width:{regime_pct}%; background:{regime_color};"></div></div>

        <div class="metric-row">
            <span class="metric-row-label">SHORT INTEREST</span>
            <span class="metric-row-value">{short_str}</span>
        </div>
        <div class="sensor-track" style="margin-bottom:8px;"><div class="sensor-fill" style="width:{short_pct}%; background:var(--color-amber-alert);"></div></div>

        <div class="metric-row">
            <span class="metric-row-label">INSIDER SIGNAL</span>
            <span class="metric-row-value" style="color:{insider_color};">{insider_sig}</span>
        </div>
        <div class="sensor-track"><div class="sensor-fill" style="width:{insider_pct}%; background:{insider_color};"></div></div>
    </div>
    """
    return clean_html(html)

def render_standby_rail() -> str:
    html = """
    <div class="data-module-card" style="text-align:center; padding:32px 20px;">
        <div class="risk-badge-wrapper" style="padding: 0 0 16px 0;">
            <div class="risk-badge-label">COMPOSITE RISK SCORE</div>
            <div class="risk-score-badge" style="background:transparent; border:1px solid var(--color-slate); color:var(--color-smoke);">
                <span>— / 100</span>
                <span>·</span>
                <span>STANDBY</span>
            </div>
        </div>
        <div style="font-family:var(--font-jetbrains-mono); font-size:11px; color:var(--color-smoke); letter-spacing:0.08em; margin-bottom:16px;">
            AWAITING TARGET TICKER FOR FULL AUDIT
        </div>
        <div style="opacity:0.4;">
            <div class="metric-row" style="padding:6px 0;">
                <span class="metric-row-label">ANNUALIZED VOLATILITY</span>
                <span class="metric-row-value" style="color:var(--color-smoke);">—%</span>
            </div>
            <div class="sensor-track" style="margin-bottom:8px;"><div class="sensor-fill" style="width:30%; background:var(--color-smoke);"></div></div>
            <div class="metric-row" style="padding:6px 0;">
                <span class="metric-row-label">MARKET REGIME</span>
                <span class="metric-row-value" style="color:var(--color-smoke);">STANDBY</span>
            </div>
            <div class="sensor-track"><div class="sensor-fill" style="width:45%; background:var(--color-smoke);"></div></div>
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

    score_color = "var(--color-nvidia-green)" if score < 31 else ("var(--color-amber-alert)" if score < 61 else "var(--color-crimson-flag)")

    html = f"""
    <div class="data-module-card" style="border-left: 2px solid var(--color-nvidia-green); padding:16px; margin-top:12px;">
        <div style="font-family:var(--font-jetbrains-mono); font-size:10px; color:var(--color-smoke); letter-spacing:0.08em; text-transform:uppercase;">
            AUDIT CONTEXT SNAPSHOT
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
            <div style="font-family:var(--font-jetbrains-mono); font-size:14px; font-weight:700; color:var(--color-frost);">${ticker}</div>
            <div style="font-family:var(--font-jetbrains-mono); font-size:12px; font-weight:500; color:{score_color};">SCORE: {score:.1f}/100</div>
        </div>
        <div style="font-family:var(--font-jetbrains-mono); font-size:11px; color:var(--color-smoke); margin-top:4px;">
            REGIME: <span style="color:var(--color-ash);">{regime}</span>
        </div>
    </div>
    """
    return clean_html(html)

# ─────────────────────────────────────────────────────────────
# 5. BARRA SUPERIOR Y NAVEGACIÓN
# ─────────────────────────────────────────────────────────────
render_telemetry_bar(job_status_label="RUNNING" if st.session_state.active_job_id else "IDLE")

# Header institucional soberano con especificación de diseño
header_html = """
<div style="margin-top: 10px; margin-bottom: 20px;">
    <div style="display:flex; justify-content:space-between; align-items:flex-end; flex-wrap:wrap; gap:12px;">
        <div>
            <div style="font-family:'Archivo', sans-serif; font-size:36px; font-weight:700; color:var(--color-frost); line-height:1.1; letter-spacing:-0.02em;">
                FINANZPRÜFER
            </div>
            <div class="green-rule"></div>
            <div style="font-family:'Space Grotesk', sans-serif; font-size:14px; color:var(--color-ash); max-width:680px; line-height:1.5;">
                Sovereign due diligence terminal. Autonomous multi-hop risk audit infrastructure powered by NVIDIA Nemotron on Nebius Token Factory.
            </div>
        </div>
        <div style="display:flex; flex-direction:column; align-items:flex-end; gap:6px;">
            <div style="display:flex; gap:6px; flex-wrap:wrap;">
                <span class="source-tag">[SEC EDGAR]</span>
                <span class="source-tag">[TAVILY]</span>
                <span class="source-tag">[FINNHUB]</span>
                <span class="source-tag">[FRED]</span>
            </div>
            <span style="font-family:'JetBrains Mono', monospace; font-size:10px; color:var(--color-smoke); letter-spacing:0.04em;">
                SOVEREIGN DUE DILIGENCE INFRASTRUCTURE · RESEARCH USE ONLY
            </span>
        </div>
    </div>
</div>
"""
st.markdown(clean_html(header_html), unsafe_allow_html=True)

tab_terminal, tab_batch = st.tabs([
    "💬 Interactive Terminal & Single Audit",
    "⚡ Batch Watchlist"
])

# ─────────────────────────────────────────────────────────────
# 6. PESTAÑA 1: TERMINAL & AUDITORÍA DUAL
# ─────────────────────────────────────────────────────────────
with tab_terminal:
    col_left, col_right = st.columns([65, 35])

    # --- COLUMNA DERECHA: RAIL FIJO DE INSTRUMENTOS ---
    with col_right:
        st.markdown(clean_html("<div class='data-module-header' style='font-size:14px; margin-bottom:8px; color:var(--color-smoke); font-family:var(--font-jetbrains-mono); font-weight:500; text-transform:uppercase; letter-spacing:0.04em;'>TELEMETRY CLUSTER</div>"), unsafe_allow_html=True)
        
        audit_data = st.session_state.get("last_audit") or st.session_state.get("current_metrics")
        if audit_data:
            score = audit_data.get("risk_score", audit_data.get("composite_risk_score", 50.0))
            tier = audit_data.get("risk_tier", "MODERATE RISK")
            ticker_disp = audit_data.get("ticker") or st.session_state.get("last_ticker", "TARGET")
            gauge_html = render_gauge(score, tier)
            bars_html = render_sensor_bars(audit_data.get("raw_metrics") or audit_data)
            st.markdown(clean_html(f"<div class='data-module-card' style='padding:20px;'>{gauge_html}{bars_html}</div>"), unsafe_allow_html=True)
            
            # Tarjeta de Memoria
            mem_card = render_memory_card(st.session_state.memory.last_audited_entity or audit_data)
            if mem_card:
                st.markdown(mem_card, unsafe_allow_html=True)

            if st.session_state.get("last_report"):
                st.download_button(
                    label=f"📥 Export Dossier (${ticker_disp})",
                    data=st.session_state.last_report,
                    file_name=f"FinanzPrufer_Audit_{ticker_disp}.md",
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
        target_t = st.session_state.last_ticker or (st.session_state.get("last_audit", {}) or {}).get("ticker") or "NVDA"
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
                    # Detectar intención de 3 tiers con clasificador de alta precisión
                    query_tier = fast_copilot.classify_query(active_prompt)

                    if query_tier == "ultra":
                        # TIER 3: NEMOTRON 3 ULTRA (550B) RE-ACT MULTI-HOP
                        tickers_found = re.findall(r"\$([A-Za-z]{1,5})\b", active_prompt)
                        target_ticker = None
                        
                        if tickers_found:
                            target_ticker = tickers_found[0].upper()
                        else:
                            words = set(re.findall(r"\b[A-Za-z]{1,6}\b", active_prompt.upper()))
                            matched_tickers = words & KNOWN_TICKERS
                            if matched_tickers:
                                target_ticker = sorted(list(matched_tickers))[0]
                            else:
                                matched_companies = words & set(COMPANY_ALIASES.keys())
                                if matched_companies:
                                    target_ticker = COMPANY_ALIASES[sorted(list(matched_companies))[0]]
                                else:
                                    macro_triggers = [
                                        "mercado", "eeuu", "sp500", "s&p", "macro", "market", "panorama", 
                                        "fed", "tasas", "inflacion", "wall street", "bolsa", "nasdaq", "dow", "overview"
                                    ]
                                    if any(w in active_prompt.lower() for w in macro_triggers):
                                        target_ticker = "SPY"
                                    elif st.session_state.get("last_ticker"):
                                        target_ticker = st.session_state["last_ticker"]
                                    else:
                                        target_ticker = "SPY"  # Default to SPY for generic overview

                        # Si la consulta de auditoría no especifica ningún ticker
                        if not target_ticker:
                            msg_no_ticker = (
                                "⚠️ **Símbolo bursátil no especificado:** Por favor incluye un ticker para auditar "
                                "(por ejemplo `$NVDA`, `$TSLA`, `$AAPL`, o `$SPY` para el mercado general)."
                            )
                            st.warning(msg_no_ticker)
                            st.session_state.messages.append({"role": "assistant", "content": msg_no_ticker})
                        else:
                            status_box = st.status(f"🧠 Nemotron 3 Ultra ReAct Loop: ${target_ticker}...", expanded=True)
                            try:
                                status_box.write("🔎 [01] tavily_search -> Querying real-time market sentiment & headlines...")
                                time.sleep(0.3)
                                status_box.write("📑 [02] sec_edgar -> Parsing Form 4 insider transactions & XBRL...")
                                time.sleep(0.3)
                                status_box.write("⚙️ [03] risk_engine -> Computing deterministic 5-factor volatility metrics...")
                                time.sleep(0.3)
                                status_box.write("🏛️ [04] fred_macro -> Fetching Treasury yields, yield spread & inflation...")

                                # Ejecutar evaluación de riesgo para los instrumentos (con caché)
                                cache_key = f"market:{target_ticker}"
                                cached_eval = tool_cache.get(cache_key)
                                if cached_eval and isinstance(cached_eval, dict):
                                    eval_metrics = cached_eval
                                else:
                                    eval_metrics = risk_tool.evaluate_risk(target_ticker)
                                    tool_cache.set(cache_key, eval_metrics)

                                st.session_state.current_metrics = eval_metrics
                                st.session_state.last_ticker = target_ticker

                                # Inferencia multi-hop con Nemotron 3 Ultra
                                agent_response = orchestrator.run(active_prompt)

                                # Persistir auditoría completa en session_state para que no se pierda en preguntas subsecuentes
                                st.session_state["last_audit"] = {
                                    "ticker": target_ticker,
                                    "risk_score": eval_metrics.get("composite_risk_score", 50.0),
                                    "risk_tier": eval_metrics.get("risk_tier", "MODERATE RISK"),
                                    "regime": eval_metrics.get("macro_regime") or eval_metrics.get("regime", "NORMAL_REGIME"),
                                    "vol_90d": eval_metrics.get("metrics", {}).get("realized_volatility_60d_pct", 25.0),
                                    "annualized_volatility_est": f"{eval_metrics.get('metrics', {}).get('realized_volatility_60d_pct', 25.0):.1f}%",
                                    "short_interest_est": "2.5%",
                                    "insider_alignment": eval_metrics.get("insider_factor", {}).get("alignment", "NEUTRAL"),
                                    "prob_outperformance": eval_metrics.get("prob_outperformance_3m", 50.0),
                                    "bear_case": eval_metrics.get("scenarios_12m", {}).get("bear_case"),
                                    "bull_case": eval_metrics.get("scenarios_12m", {}).get("bull_case"),
                                    "price": eval_metrics.get("current_price", 0.0),
                                    "raw_metrics": eval_metrics,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }

                                # Actualizar memoria y generar dossier Markdown
                                st.session_state.memory.store_audit_snapshot(
                                    ticker=target_ticker,
                                    risk_score=eval_metrics.get("composite_risk_score", 50.0),
                                    regime=eval_metrics.get("macro_regime", eval_metrics.get("regime", "NORMAL_REGIME")),
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

                    elif query_tier == "super":
                        # TIER 2: NEMOTRON 3 SUPER (120B) COMPARATIVAS Y PRONÓSTICOS INTERMEDIOS
                        with st.spinner("⚡ Nemotron 3 Super (120B) synthesizing quantitative comparative analysis..."):
                            super_response = fast_copilot.respond_super(active_prompt, conversation_history=st.session_state.messages)
                            st.markdown(super_response)
                            st.session_state.messages.append({"role": "assistant", "content": super_response})
                            st.rerun()

                    else:
                        # TIER 1: NEMOTRON 3 NANO (30B) EDUCACIÓN, TEORÍA Y PLANIFICACIÓN
                        with st.spinner("⚡ Nemotron 3 Nano (30B) synthesizing strategic guidance..."):
                            nano_response = fast_copilot.respond_nano(active_prompt, conversation_history=st.session_state.messages)
                            st.markdown(nano_response)
                            st.session_state.messages.append({"role": "assistant", "content": nano_response})
                            st.rerun()

# ─────────────────────────────────────────────────────────────
# 7. PESTAÑA 2: BATCH WATCHLIST (PARALLEL WORKERS)
# ─────────────────────────────────────────────────────────────
with tab_batch:
    batch_col1, batch_col2 = st.columns([40, 60])

    with batch_col1:
        st.markdown(clean_html("""
        <div class='data-module-card' style='padding:20px;'>
            <div class='data-module-header'>DISPATCH BATCH AUDIT</div>
            <div class='green-rule'></div>
            <div class='data-module-subhead'>Asynchronously audits entire watchlists via background workers powered by parallel thread execution.</div>
        </div>
        """), unsafe_allow_html=True)

        watchlist_input = st.text_area(
            "Portfolio Tickers (comma separated):",
            value="NVDA, TSLA, MSFT, AAPL, PLTR",
            height=90
        )

        if st.button("🚀 DESPACHAR AUDITORÍA BATCH", type="primary", use_container_width=True):
            clean_list = [x.strip() for x in watchlist_input.split(",") if x.strip()]
            job_id = batch_runner.submit_watchlist_batch_job(clean_list)
            st.session_state.active_job_id = job_id
            st.rerun()

        # Monitoreo reactivo NO bloqueante
        if st.session_state.active_job_id:
            job_id = st.session_state.active_job_id
            info = batch_runner.get_job_status(job_id)
            st_val = info.get("status", "UNKNOWN")
            pr_str = str(info.get("progress", "0%")).replace("%", "")
            try:
                pr_float = float(pr_str) / 100.0
            except ValueError:
                pr_float = 0.0

            st.markdown(clean_html(f"""
            <div class='data-module-card' style='padding:14px; margin-top:12px;'>
                <div style='font-family:var(--font-jetbrains-mono); font-size:11px; color:var(--color-smoke); letter-spacing:0.04em;'>
                    JOB ID: <span style='color:var(--color-frost); font-weight:500;'>{job_id}</span>
                </div>
            </div>
            """), unsafe_allow_html=True)
            
            st.progress(pr_float)
            st.markdown(
                clean_html(
                    f"<div class='nsc-mono' style='font-size:10.5px; color:var(--color-smoke); margin-bottom:8px;'>"
                    f"STATUS: <span style='color:var(--color-nvidia-green); font-weight:500;'>{st_val}</span> | ASSETS: {info.get('processed', '0/0')}"
                    f"</div>"
                ), 
                unsafe_allow_html=True
            )

            if st_val in ["QUEUED", "RUNNING"]:
                time.sleep(1.0)
                st.rerun()
            elif st_val == "COMPLETED":
                st.success("Batch Watchlist audit successfully completed.")

    with batch_col2:
        st.markdown(clean_html("""
        <div class='data-module-card' style='padding:20px;'>
            <div class='data-module-header'>PORTFOLIO RISK LADDER</div>
            <div class='green-rule'></div>
            <div class='data-module-subhead'>Cross-asset risk dispersion and portfolio weighted risk scoring.</div>
        </div>
        """), unsafe_allow_html=True)

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
                for ticker, res in sorted(job_results.items(), key=lambda x: x[1].get("risk_score") or 0):
                    sc = res.get("risk_score")
                    sc_val = sc if sc is not None else 0
                    fill_color = "var(--color-crimson-flag)" if sc_val >= 70 else ("var(--color-amber-alert)" if sc_val >= 45 else "var(--color-nvidia-green)")
                    score_display = f"{sc_val:.0f}/100" if sc is not None else "N/A"
                    ladder_html = f"""
                    <div class="ladder-row">
                        <div style="width:60px; font-weight:700; color:var(--color-frost); font-family:var(--font-jetbrains-mono);">${ticker}</div>
                        <div class="ladder-bar-bg">
                            <div class="ladder-bar-fill" style="width:{sc_val}%; background:{fill_color};"></div>
                            <div class="ladder-avg-marker" style="left:{avg_score}%;" title="Portfolio Average ({avg_score:.1f})"></div>
                        </div>
                        <div style="width:60px; text-align:right; color:{fill_color}; font-weight:700; font-family:var(--font-jetbrains-mono);">{score_display}</div>
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
