import logging
from typing import List, Dict
from openai import OpenAI
from src.config import settings

logger = logging.getLogger(__name__)

class FastChatCopilot:
    """
    Copiloto ligero para consultas conversacionales y educación financiera.
    Utiliza Nemotron Nano para entregar baja latencia y bajo consumo de tokens.
    """
    def __init__(self):
        self.client = OpenAI(
            base_url=settings.NEBIUS_BASE_URL,
            api_key=settings.NEBIUS_API_KEY
        )
        self.model = settings.MODEL_FAST

    def is_complex_query(self, prompt: str) -> bool:
        """
        Clasificador heurístico de intención:
        Determina si la consulta requiere auditoría profunda (Nemotron Ultra + Tools)
        o si es una duda conceptual/educativa directa (Nemotron Nano).
        """
        audit_triggers = [
            "$", "audita", "audit", "10-k", "10-q", "form 4", "insider",
            "riesgo de", "risk score", "volatilidad", "sec", "dossier"
        ]
        prompt_lower = prompt.lower()
        return any(trigger in prompt_lower for trigger in audit_triggers)

    def respond(self, prompt: str, conversation_history: List[Dict[str, str]] = None) -> str:
        system_instruction = (
            "Eres FinanzPrüfer Fast Copilot, un asistente financiero ágil y educativo. "
            "Responde de forma clara, concisa y profesional a dudas conceptuales sobre finanzas, "
            "términos de mercado, ratios o finanzas personales. Recuerda siempre que tu propósito es puramente educativo."
        )

        messages = [{"role": "system", "content": system_instruction}]
        
        if conversation_history:
            messages.extend(conversation_history[-4:])
            
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=300
            )
            return response.choices[0].message.content or "No se pudo generar respuesta rápida."
        except Exception as e:
            logger.error(f"Fallo en Nemotron Nano: {e}")
            return f"Error en inferencia rápida: {str(e)}"
