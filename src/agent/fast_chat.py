import re
import logging
from typing import List, Dict, Optional
from openai import OpenAI
from src.config import settings

logger = logging.getLogger(__name__)

# Tickers comunes conocidos (para detección de activos sin prefijo $)
KNOWN_TICKERS = {
    "NVDA", "TSLA", "AAPL", "MSFT", "AMZN", "GOOG", "GOOGL", "META",
    "AMD", "PLTR", "INTC", "NFLX", "DIS", "BA", "JPM", "GS", "V",
    "MA", "WMT", "COST", "UNH", "JNJ", "PFE", "XOM", "CVX",
    "SPY", "QQQ", "IWM", "BRK.B", "AVGO", "CRM", "ORCL", "ADBE",
    "SMCI", "ARM", "MRVL", "MU", "QCOM", "AMAT", "LRCX", "KLAC",
    "COIN", "SQ", "PYPL", "SHOP", "SNOW", "NET", "CRWD", "PANW",
    "SOFI", "HOOD", "RIVN", "LCID", "NIO", "F", "GM", "UBER", "LYFT"
}

# Alias de nombres comerciales a tickers bursátiles
COMPANY_ALIASES = {
    "TESLA": "TSLA",
    "NVIDIA": "NVDA",
    "APPLE": "AAPL",
    "MICROSOFT": "MSFT",
    "AMAZON": "AMZN",
    "GOOGLE": "GOOGL",
    "ALPHABET": "GOOGL",
    "PALANTIR": "PLTR",
}

def classify_query(user_message: str) -> str:
    """
    Clasificador de intención de 3 tiers (NVIDIA Nemotron Routing):
    Returns 'ultra', 'super', or 'nano' based on query complexity.
    Orden estricto de precedencia:
    1. $TICKER explícito → ultra
    2. Ticker + audit terms → ultra
    3. Ticker sin audit terms → super
    4. Market overview terms (sin ticker) → ultra (requiere herramientas para SPY y macro)
    5. Medium financial terms (sin ticker) → super
    6. Todo lo demás (educación, planificación personal) → nano
    """
    text = user_message.strip()
    text_upper = text.upper()
    text_lower = text.lower()

    # 1. Detección de ticker explícito con prefijo $ (excluyendo cifras monetarias como $5000)
    has_dollar_ticker = bool(re.search(r'\$[A-Za-z]{1,5}\b', text))

    # 2. Detección de tickers conocidos o empresas sin $
    words_upper = set(re.findall(r'\b[A-Z]{1,6}\b', text_upper))
    has_known_ticker = bool(words_upper & KNOWN_TICKERS)
    has_company_alias = bool(words_upper & set(COMPANY_ALIASES.keys()))
    has_ticker = has_dollar_ticker or has_known_ticker or has_company_alias

    # 1. $TICKER explícito → ultra
    if has_dollar_ticker:
        return "ultra"

    # 2. Ticker + audit terms → ultra
    DEEP_AUDIT_TERMS = [
        "audita", "due diligence", "dossier", "informe completo",
        "análisis completo", "analisis completo", "full analysis",
        "form 4", "10-k", "insider", "risk score", "score de riesgo",
        "cobertura", "hedge", "put spread", "collar", "watchlist batch"
    ]
    if has_ticker and any(term in text_lower for term in DEEP_AUDIT_TERMS):
        return "ultra"

    # 3. Ticker sin audit terms → super
    if has_ticker:
        return "super"

    # 4. Market overview terms (sin ticker) → ultra (necesita tools para SPY + macro)
    MARKET_OVERVIEW_TERMS = [
        "mercado", "market", "panorama", "overview", "macro", "s&p", "sp500", "nasdaq", "dow jones",
        "bolsa", "wall street", "mercado americano", "us market", "mercado estadounidense",
        "cómo va el mercado", "como va el mercado", "how's the market", "market analysis"
    ]
    if any(term in text_lower for term in MARKET_OVERVIEW_TERMS):
        return "ultra"

    # 5. Medium financial terms (sin ticker) → super
    MEDIUM_TERMS = [
        "analiza", "análisis", "analisis", "pronostico", "pronóstico",
        "forecast", "riesgo", "risk", "earnings", "consenso", "consensus",
        "price target", "volatilidad", "volatility", "comparar", "compare"
    ]
    if any(term in text_lower for term in MEDIUM_TERMS):
        return "super"

    # 6. Todo lo demás (educación, teoría, finanzas personales) → nano
    return "nano"

def is_complex_query(user_message: str) -> bool:
    """
    Compatibilidad hacia atrás con el orquestador y la interfaz:
    Devuelve True si la consulta requiere el bucle ReAct multi-herramienta de Nemotron 3 Ultra.
    """
    return classify_query(user_message) == "ultra"


class FastChatCopilot:
    """
    Copiloto ágil multimodelo para consultas conceptuales, teoría y análisis comparativo.
    - Tier 1 (Nano - 30B): Conceptos, teoría, planificación patrimonial sin herramientas.
    - Tier 2 (Super - 120B): Consultas comparativas de activos y proyecciones intermedias.
    - Tier 3 (Ultra - 550B): Gestionado por FinanzOrchestrator para auditorías completas.
    """
    def __init__(self):
        self.client = OpenAI(
            base_url=settings.NEBIUS_BASE_URL,
            api_key=settings.NEBIUS_API_KEY
        )
        self.model_nano = settings.MODEL_NANO
        self.model_super = settings.MODEL_SUPER
        self.model = self.model_nano  # Alias por defecto

    def classify_query(self, prompt: str) -> str:
        return classify_query(prompt)

    def is_complex_query(self, prompt: str) -> bool:
        return is_complex_query(prompt)

    def respond(self, prompt: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Alias para respuesta directa Tier 1 (Nano)."""
        return self.respond_nano(prompt, conversation_history)

    def respond_nano(self, prompt: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Tier 1: Responde a dudas conceptuales o planificación financiera personal
        usando Nemotron 3 Nano con enfoque socrático/educativo.
        """
        system_instruction = (
            "You are FinanzPrüfer's educational copilot, powered by NVIDIA Nemotron Nano on Nebius Token Factory.\n\n"
            "YOUR CAPABILITIES:\n"
            "- Financial education: Explain concepts (P/E ratio, Kelly Criterion, diversification, etc.)\n"
            "- Portfolio planning: Help users think through investment decisions with structured questions\n"
            "- Risk budgeting: Explain position sizing, asset allocation, and hedging concepts\n"
            "- General financial literacy: Savings strategies, emergency funds, debt management\n\n"
            "PLANNING MODE — When a user asks 'where should I invest $X' or 'help me build a portfolio':\n"
            "- NEVER give a direct investment recommendation (you are not a financial advisor)\n"
            "- Instead, ask 2-3 clarifying questions FIRST before giving guidance:\n"
            "  1. Time horizon: 'When might you need this money?' (< 1 year, 1-3 years, 5+ years)\n"
            "  2. Risk tolerance: 'How would you feel if this dropped 20% temporarily?'\n"
            "  3. Emergency fund: 'Do you already have 3-6 months of expenses saved separately?'\n"
            "- Based on their answers, provide EDUCATIONAL guidance:\n"
            "  * Short horizon + no emergency fund -> explain why a high-yield savings account (HYSA) is appropriate first\n"
            "  * Medium horizon -> explain index ETFs (VOO, VTI, QQQ) and dollar-cost averaging\n"
            "  * Long horizon -> explain diversified portfolios, Roth IRA benefits, sector allocation\n"
            "- Always end with: 'This is educational guidance, not financial advice. Your decision.'\n\n"
            "STYLE:\n"
            "- Warm, direct, practical — like a knowledgeable friend, not a textbook\n"
            "- Use concrete examples with current approximate numbers when helpful\n"
            "- If the user mentions a specific amount, work with that exact number\n"
            "- Keep responses focused — don't dump everything you know, answer what they asked\n"
            "- Answer in the same language as the user (Spanish if user writes in Spanish, English if in English).\n\n"
            "IMPORTANT: You do NOT have access to real-time market data tools. Do not cite specific "
            "current prices, yields, or rates unless the user provides them. For current data, suggest "
            "they use the audit terminal (e.g., 'For current NVDA analysis, try: $NVDA in the terminal')."
        )

        messages = [{"role": "system", "content": system_instruction}]
        if conversation_history:
            messages.extend(conversation_history[-4:])
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model_nano,
                messages=messages,
                temperature=0.3,
                max_tokens=1000
            )
            return response.choices[0].message.content or "Sin respuesta disponible."
        except Exception as e:
            logger.error(f"Fallo en inferencia de Nemotron Nano ({self.model_nano}): {e}")
            return f"Error en copiloto rápido Nano: {str(e)}"

    def respond_super(self, prompt: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Tier 2: Inferencia con Nemotron 3 Super (120B) para comparativas, pronósticos intermedios
        y síntesis analítica sin bucle ReAct multi-herramienta.
        """
        system_instruction = (
            "Eres FinanzPrüfer Super Copilot (Tier 2 - NVIDIA Nemotron 3 Super 120B), un analista cuantitativo "
            "y estratega de inversiones senior. Tu rol es resolver consultas financieras analíticas intermedias, "
            "comparativas de activos, estimaciones de consenso e impacto de eventos macroeconómicos o de resultados. "
            "Ofrece respuestas concisas, altamente analíticas, con métricas clave y estructura institucional. "
            "Aviso legal obligatorio: Propósito puramente educativo y analítico; no constituye recomendación formal de inversión."
        )

        messages = [{"role": "system", "content": system_instruction}]
        if conversation_history:
            messages.extend(conversation_history[-4:])
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model_super,
                messages=messages,
                temperature=0.2,
                max_tokens=800
            )
            return response.choices[0].message.content or "Sin respuesta disponible."
        except Exception as e:
            logger.error(f"Fallo en inferencia de Nemotron Super ({self.model_super}): {e}. Reintentando con Nano...")
            return self.respond_nano(prompt, conversation_history)
