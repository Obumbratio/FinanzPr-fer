from typing import List, Dict, Any, Optional

class AuditMemoryManager:
    """
    Gestor de memoria de sesión y estado para FinanzPrüfer.
    Mantiene el contexto conversacional reciente y almacena los metadatos
    del último activo auditado para comparaciones multi-hop.
    """
    def __init__(self, max_history: int = 6):
        self.max_history = max_history
        self.conversation_history: List[Dict[str, str]] = []
        self.last_audited_entity: Optional[Dict[str, Any]] = None

    def add_message(self, role: str, content: str) -> None:
        """Agrega un mensaje y poda el historial para evitar desbordar la ventana de contexto."""
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]

    def store_audit_snapshot(self, ticker: str, risk_score: float, regime: str, summary: str) -> None:
        """Guarda un snapshot del último activo auditado para habilitar comparaciones cruzadas."""
        self.last_audited_entity = {
            "ticker": ticker.upper(),
            "risk_score": risk_score,
            "regime": regime,
            "summary_snippet": summary[:350]
        }

    def get_comparative_context(self) -> str:
        """Genera un fragmento de contexto previo si el usuario hace preguntas de seguimiento."""
        if not self.last_audited_entity:
            return ""
        
        entity = self.last_audited_entity
        return (
            f"[CONTEXTO DE AUDITORÍA PREVIA]: El usuario auditó recientemente ${entity['ticker']} "
            f"con un Risk Score de {entity['risk_score']}/100 y régimen '{entity['regime']}'. "
            f"Usa estos datos si el usuario pide una comparación directa o contraste de riesgo."
        )

    def get_recent_messages(self) -> List[Dict[str, str]]:
        return self.conversation_history

    def clear(self) -> None:
        self.conversation_history = []
        self.last_audited_entity = None
