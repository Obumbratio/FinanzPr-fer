import re
import logging
from typing import List, Dict, Optional
from openai import OpenAI
from src.config import settings

logger = logging.getLogger(__name__)

class FastChatCopilot:
    """
    Copiloto ligero para consultas conceptuales, teoría y planificación de carteras.
    Utiliza Nemotron Nano para entregar baja latencia y preservar créditos.
    """
    def __init__(self):
        self.client = OpenAI(
            base_url=settings.NEBIUS_BASE_URL,
            api_key=settings.NEBIUS_API_KEY
        )
        self.model = settings.MODEL_FAST

    def is_complex_query(self, prompt: str) -> bool:
        """
        Detecta si la consulta exige bucle ReAct multi-herramienta con Nemotron 3 Ultra.
        Identifica tickers con o sin $, términos de auditoría forense y temas macro.
        """
        p = prompt.lower()

        # 1. Tickers conocidos y patrones bursátiles ($TICKER o tickers populares en texto libre)
        common_tickers = [
            "nvda", "tsla", "aapl", "msft", "pltr", "amd", "googl", "goog", 
            "amzn", "meta", "spy", "qqq", "asml", "avgo", "intc", "arm"
        ]
        has_dollar_ticker = bool(re.search(r"\$[a-z]{1,5}\b", p))
        has_standalone_ticker = any(re.search(rf"\b{re.escape(t)}\b", p) for t in common_tickers)

        if has_dollar_ticker or has_standalone_ticker:
            return True

        # 2. Términos de auditoría, SEC, pronósticos y consenso
        audit_triggers = [
            "audita", "audit", "analisis", "análisis", "pronostico", "pronóstico",
            "precio objetivo", "price target", "target", "tipranks", "danelfin",
            "10-k", "10-q", "form 4", "insider", "ballena", "whale", "filing",
            "risk score", "volatilidad", "short interest"
        ]
        if any(trig in p for trig in audit_triggers):
            return True

        # 3. Macroeconomía y mercado en tiempo real
        macro_triggers = [
            "mercado", "market", "macro", "panorama", "sp500", "s&p",
            "fed", "tasas", "inflacion", "inflación", "recesion", "recesión"
        ]
        if any(trig in p for trig in macro_triggers):
            return True

        return False

    def respond(self, prompt: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Responde exclusivamente a dudas conceptuales o planificación patrimonial
        (ej. presupuestos de riesgo, Core-Satélite, diversificación).
        """
        system_instruction = (
            "Eres FinanzPrüfer Fast Copilot, un asesor institucional de educación y planificación financiera. "
            "Tu objetivo es guiar al usuario en la estructuración de presupuestos de riesgo, asignación de activos "
            "(Core-Satélite), diversificación y conceptos de mercado (EBITDA, P/E, Kelly Criterion, VaR). "
            "Responde de manera ejecutiva, con rigor matemático e institucional, usando tablas cuando sea pertinente. "
            "Aviso legal obligatorio: Propósito puramente educativo; no es asesoramiento financiero formal."
        )

        messages = [{"role": "system", "content": system_instruction}]
        if conversation_history:
            messages.extend(conversation_history[-4:])
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=600
            )
            return response.choices[0].message.content or "Sin respuesta disponible."
        except Exception as e:
            logger.error(f"Fallo en inferencia de Nemotron Nano: {e}")
            return f"Error en copiloto rápido: {str(e)}"
