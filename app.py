import streamlit as st
import time
import re
from src.config import settings
from src.agent.orchestrator import FinanzOrchestrator
from src.agent.fast_chat import FastChatCopilot
from src.cloud.serverless_jobs import NebiusServerlessJobRunner
from src.tools.risk_tool import RiskEngineTool
from src.tools.report_tool import ReportGenerator

# 1. Configuración de página y estilos
st.set_page_config(
    page_title="FinanzPrüfer — Due Diligence Engine",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar recursos compartidos en caché
@st.cache_resource
def get_orchestrator():
    return FinanzOrchestrator()

@st.cache_resource
def get_fast_copilot():
    return FastChatCopilot()

@st.cache_resource
def get_job_runner():
    return NebiusServerlessJobRunner()

orchestrator = get_orchestrator()
fast_copilot = get_fast_copilot()
job_runner = get_job_runner()

# Inicializar estado de sesión
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "👋 **Willkommen bei FinanzPrüfer.** Soy tu auditor de inteligencia financiera y due diligence. "
                "Puedo auditar reportes de la SEC, compras/ventas de insiders, calcular scores cuantitativos de riesgo "
                "y verificar noticias de mercado en tiempo real con Tavily. ¿Qué activo deseas auditar hoy?"
            )
        }
    ]

if "last_report" not in st.session_state:
    st.session_state.last_report = None
if "last_ticker" not in st.session_state:
    st.session_state.last_ticker = "NVDA"
if "batch_report" not in st.session_state:
    st.session_state.batch_report = None
if "batch_job_id" not in st.session_state:
    st.session_state.batch_job_id = None

# 2. Barra Lateral (Régimen Macro y Watchlist Rápida)
with st.sidebar:
    st.title("⚖️ FinanzPrüfer")
    st.caption("Autonomous Financial Due Diligence Engine")
    
    st.divider()
    
    # Indicadores de Infraestructura
    st.markdown("### 🔌 System Infrastructure")
    st.success("🟢 **Nebius Token Factory:** Active")
    st.info("🧠 **Deep Reasoning:** Nemotron 3 Ultra")
    st.info("⚡ **Fast Copilot:** Nemotron Nano")
    st.success("🔎 **Tavily Search API:** Connected")
    st.success("☁️ **Serverless Jobs:** Ready")
    
    st.divider()
    
    # Régimen Macro de Mercado Dinámico (4 Estados Börsenhirn)
    st.markdown("### 📊 4-State Macro Regime")
    macro_info = RiskEngineTool.get_macro_market_regime(16.4)
    
    regime_colors = {
        "PANIC": "🔴",
        "BEAR": "🟠",
        "SIDEWAYS": "🟡",
        "BULL": "🟢"
    }
    regime_badge = regime_colors.get(macro_info["regime"], "⚪")

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="VIX Proxy", value=f"{macro_info['vix_estimate']}", delta="-1.2%")
    with col2:
        st.metric(label="Macro State", value=f"{regime_badge} {macro_info['regime']}")
        
    st.caption(f"**Market Context:** *{macro_info['description']}*")
    st.caption(f"**Posture:** `{macro_info['recommended_posture']}`")
    
    st.divider()
    
    # Watchlist rápida para la terminal interactiva
    st.markdown("### 📌 Quick Audit Tickers")
    selected_quick_ticker = st.selectbox(
        "Select symbol to preset prompt:",
        ["NVDA", "TSLA", "MSFT", "AAPL", "PLTR"]
    )
    if st.button(f"Audit ${selected_quick_ticker}"):
        st.session_state.quick_prompt = (
            f"Realiza una auditoría completa de riesgo para ${selected_quick_ticker}. "
            "Revisa filings recientes en la SEC, noticias de mercado con Tavily y calcula su Risk Score."
        )

    st.divider()
    st.warning("⚠️ **Educational Tool:** Not financial advice. See `legal/DISCLAIMER.md` for institutional compliance details.")

# 3. Encabezado Principal y Pestañas de la Aplicación
st.title("FinanzPrüfer — Institutional Due Diligence Platform")
st.caption("Dual Engine: NVIDIA Nemotron 3 Ultra & Nemotron Nano on Nebius Token Factory & Nebius AI Cloud")

tab1, tab2 = st.tabs([
    "💬 Interactive Terminal & Single Audit", 
    "⚡ Nebius Cloud Batch Watchlist"
])

# ==============================================================================
# PESTAÑA 1: TERMINAL INTERACTIVA & AUDITORÍA INDIVIDUAL
# ==============================================================================
with tab1:
    st.subheader("Autonomous Due Diligence Terminal")
    st.caption("Consultas conceptuales rápidas (Nemotron Nano) y auditorías profundas ReAct con herramientas (Nemotron 3 Ultra)")

    # Renderizar historial de conversación
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Captura de prompts
    preset_prompt = st.session_state.pop("quick_prompt", None)
    user_query = st.chat_input("Escribe tu consulta financiera o pide una auditoría (ej. 'Audita el riesgo de $TSLA' o '¿Qué es el EBITDA?')...")

    active_prompt = preset_prompt or user_query

    # Procesamiento con Enrutamiento Dual
    if active_prompt:
        st.session_state.messages.append({"role": "user", "content": active_prompt})
        with st.chat_message("user"):
            st.markdown(active_prompt)

        with st.chat_message("assistant"):
            # Evaluar si requiere bucle ReAct con herramientas o respuesta conceptual ágil
            if fast_copilot.is_complex_query(active_prompt):
                status_placeholder = st.status("🧠 Nemotron 3 Ultra orquestando auditoría profunda...", expanded=True)
                try:
                    status_placeholder.write("🔎 Verificando contexto y noticias en Tavily Search API (Circuit Breaker Protected)...")
                    time.sleep(0.3)
                    status_placeholder.write("📑 Consultando filings regulatorios en SEC EDGAR (Form 4 / 10-K)...")
                    time.sleep(0.3)
                    status_placeholder.write("⚙️ Computando régimen macro de 4 estados y Risk Score...")

                    response_text = orchestrator.run(active_prompt)
                    status_placeholder.update(label="✅ Auditoría completada con éxito", state="complete", expanded=False)
                    st.markdown(response_text)

                    # Detección de ticker para el dossier
                    ticker_match = re.search(r'\$([A-Za-z]{1,5})\b', active_prompt)
                    if ticker_match:
                        detected_ticker = ticker_match.group(1).upper()
                    else:
                        known_tickers = ["NVDA", "TSLA", "MSFT", "AAPL", "PLTR", "AMD", "GOOGL", "META", "AMZN"]
                        detected_ticker = next((t for t in known_tickers if t in active_prompt.upper()), None)
                        if not detected_ticker:
                            raw_words = active_prompt.replace("$", " ").split()
                            detected_ticker = next((w.upper() for w in raw_words if w.isupper() and 2 <= len(w) <= 5), "AUDIT")

                    # Generación y almacenamiento del dossier Markdown
                    dossier_content = ReportGenerator.create_markdown_dossier(detected_ticker, response_text, active_prompt)
                    st.session_state.last_report = dossier_content
                    st.session_state.last_ticker = detected_ticker

                except Exception as e:
                    status_placeholder.update(label="❌ Error durante la auditoría", state="error")
                    st.error(f"Fallo en la ejecución agéntica: {str(e)}")
                    response_text = "Ocurrió un error al procesar la auditoría."
            else:
                # Respuesta conceptual rápida con Nemotron Nano
                with st.spinner("⚡ Nemotron Nano respondiendo..."):
                    response_text = fast_copilot.respond(active_prompt)
                    st.markdown(response_text)

            st.session_state.messages.append({"role": "assistant", "content": response_text})

    # Sección de Descarga del Dossier Individual
    if st.session_state.last_report:
        st.divider()
        st.download_button(
            label=f"📥 Descargar Audit Dossier (${st.session_state.last_ticker})",
            data=st.session_state.last_report,
            file_name=f"FinanzPrufer_Audit_{st.session_state.last_ticker}.md",
            mime="text/markdown",
            key="btn_download_single_dossier"
        )

# ==============================================================================
# PESTAÑA 2: NEBIUS CLOUD SERVERLESS BATCH WATCHLIST
# ==============================================================================
with tab2:
    st.subheader("⚡ Nebius Cloud Serverless Batch Watchlist")
    st.markdown(
        "Ejecuta auditorías concurrentes en segundo plano para carteras enteras utilizando "
        "los workers asíncronos de **Nebius AI Cloud** y **NVIDIA Nemotron 3 Ultra**."
    )

    # Entrada de tickers
    watchlist_input = st.text_area(
        "Ingresa los símbolos bursátiles a auditar (separados por coma):",
        value="NVDA, TSLA, MSFT, AAPL, PLTR",
        height=80
    )

    if st.button("🚀 Despachar Serverless Batch Job", type="primary"):
        # Limpiar y parsear tickers
        tickers = [t.strip().upper().replace("$", "") for t in watchlist_input.split(",") if t.strip()]
        
        if not tickers:
            st.error("Por favor, ingresa al menos un símbolo válido.")
        else:
            job_id = job_runner.submit_watchlist_batch_job(tickers)
            st.session_state.batch_job_id = job_id
            st.session_state.batch_report = None
            
            st.info(f"📋 **Job despachado exitosamente:** `{job_id}` | Total de activos: {len(tickers)}")
            
            progress_bar = st.progress(0.0)
            status_container = st.status(f"⏱️ Procesando lote en Nebius Cloud...", expanded=True)
            
            # Bucle de sondeo (Polling) con telemetría en tiempo real
            while True:
                status_info = job_runner.get_job_status(job_id)
                current_status = status_info.get("status", "UNKNOWN")
                raw_progress = status_info.get("progress", "0.0%").replace("%", "")
                progress_val = min(float(raw_progress) / 100.0, 1.0)
                processed = status_info.get("processed", "0/0")
                
                progress_bar.progress(progress_val)
                status_container.write(f"⚙️ **Estado:** `{current_status}` | **Avance:** {status_info.get('progress')} | **Activos:** {processed}")
                
                if current_status == "COMPLETED":
                    status_container.update(label=f"✅ Job `{job_id}` completado con éxito!", state="complete", expanded=False)
                    batch_md = job_runner.export_batch_markdown(job_id)
                    st.session_state.batch_report = batch_md
                    break
                elif current_status == "FAILED":
                    status_container.update(label=f"❌ Job `{job_id}` finalizó con errores.", state="error")
                    break
                    
                time.sleep(1.5)

    # Renderizar resultados de la Watchlist si existen
    if st.session_state.batch_report:
        st.divider()
        st.markdown("### 📊 Consolidated Watchlist Audit Results")
        st.markdown(st.session_state.batch_report)
        
        st.download_button(
            label="📥 Descargar Reporte Consolidado de Watchlist (.md)",
            data=st.session_state.batch_report,
            file_name=f"FinanzPrufer_Watchlist_{st.session_state.batch_job_id or 'Consolidated'}.md",
            mime="text/markdown",
            key="btn_download_batch_report"
        )

# Pie de página institucional
st.divider()
st.caption(
    "⚖️ **FinanzPrüfer 1.0.0** | Built with NVIDIA Nemotron on Nebius Token Factory & AI Cloud | "
    "Read the full [Ethical & Regulatory Disclaimer](legal/DISCLAIMER.md) — Strictly for educational purposes."
)
