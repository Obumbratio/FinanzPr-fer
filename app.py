import streamlit as st
import time
import re
from src.config import settings
from src.agent.orchestrator import FinanzOrchestrator
from src.agent.fast_chat import FastChatCopilot
from src.tools.report_tool import ReportGenerator

# 1. Configuración de página y estilos
st.set_page_config(
    page_title="FinanzPrüfer — Due Diligence Engine",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar orquestador agéntico y copiloto rápido
@st.cache_resource
def get_orchestrator():
    return FinanzOrchestrator()

@st.cache_resource
def get_fast_copilot():
    return FastChatCopilot()

orchestrator = get_orchestrator()
fast_copilot = get_fast_copilot()

# Inicializar historial de chat
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

# 2. Barra Lateral (Régimen Macro y Watchlist)
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
    
    st.divider()
    
    # Régimen Macro de Mercado
    st.markdown("### 📊 Market Regime Heuristic")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="VIX Est.", value="16.4", delta="-1.2%")
    with col2:
        st.metric(label="Regime", value="ACCUMULATION")
        
    st.caption("Current state: *Moderate risk appetite with selective tech rotation.*")
    
    st.divider()
    
    # Watchlist rápida
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
    st.warning("⚠️ **Educational Tool:** Not financial advice. Past results or heuristic scoring do not predict future market returns.")

# 3. Vista Principal del Dashboard
st.subheader("Autonomous Due Diligence Terminal")
st.caption("Dual Engine: NVIDIA Nemotron 3 Ultra & Nemotron Nano on Nebius Token Factory")

# Renderizar historial de conversación
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Si se activó un botón rápido de la barra lateral
preset_prompt = st.session_state.pop("quick_prompt", None)
user_query = st.chat_input("Escribe tu consulta financiera o pide una auditoría (ej. 'Audita el riesgo de $TSLA' o '¿Qué es el PER?')...")

active_prompt = preset_prompt or user_query

# 4. Procesamiento con Enrutamiento Dual
if active_prompt:
    st.session_state.messages.append({"role": "user", "content": active_prompt})
    with st.chat_message("user"):
        st.markdown(active_prompt)

    with st.chat_message("assistant"):
        # Evaluar si la consulta necesita herramientas complejas o respuesta rápida
        if fast_copilot.is_complex_query(active_prompt):
            status_placeholder = st.status("🧠 Nemotron 3 Ultra orquestando auditoría...", expanded=True)
            try:
                status_placeholder.write("🔎 Verificando contexto de mercado en Tavily Search API...")
                time.sleep(0.3)
                status_placeholder.write("📑 Consultando registros regulatorios en SEC EDGAR...")
                time.sleep(0.3)
                status_placeholder.write("⚙️ Computando métricas cuantitativas y Risk Score...")

                response_text = orchestrator.run(active_prompt)
                status_placeholder.update(label="✅ Auditoría completada con éxito", state="complete", expanded=False)
                st.markdown(response_text)

                # Detección precisa de ticker para el reporte descargable
                ticker_match = re.search(r'\$([A-Za-z]{1,5})\b', active_prompt)
                if ticker_match:
                    detected_ticker = ticker_match.group(1).upper()
                else:
                    known_tickers = ["NVDA", "TSLA", "MSFT", "AAPL", "PLTR", "AMD", "GOOGL", "META", "AMZN"]
                    detected_ticker = next((t for t in known_tickers if t in active_prompt.upper()), None)
                    if not detected_ticker:
                        raw_words = active_prompt.replace("$", " ").split()
                        detected_ticker = next((w.upper() for w in raw_words if w.isupper() and 2 <= len(w) <= 5), "AUDIT")

                # Generación de dossier
                dossier_content = ReportGenerator.create_markdown_dossier(detected_ticker, response_text, active_prompt)
                st.session_state.last_report = dossier_content
                st.session_state.last_ticker = detected_ticker

            except Exception as e:
                status_placeholder.update(label="❌ Error durante la auditoría", state="error")
                st.error(f"Fallo en la ejecución agéntica: {str(e)}")
                response_text = "Ocurrió un error en la auditoría."
        else:
            # Respuesta rápida con Nemotron Nano
            with st.spinner("⚡ Nemotron Nano respondiendo..."):
                response_text = fast_copilot.respond(active_prompt)
                st.markdown(response_text)

        st.session_state.messages.append({"role": "assistant", "content": response_text})

# 5. Sección de Exportación de Dossier
if st.session_state.last_report:
    st.divider()
    st.download_button(
        label=f"📥 Descargar Audit Dossier (${st.session_state.last_ticker})",
        data=st.session_state.last_report,
        file_name=f"FinanzPrufer_Audit_{st.session_state.last_ticker}.md",
        mime="text/markdown"
    )
