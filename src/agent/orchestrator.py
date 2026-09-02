import json
import logging
from typing import List, Dict, Any
from openai import OpenAI
from src.config import settings
from src.tools.search_tool import FinancialSearchTool
from src.tools.sec_tool import SECTool
from src.tools.risk_tool import RiskEngineTool
from src.agent.memory import AuditMemoryManager

logger = logging.getLogger(__name__)

class FinanzOrchestrator:
    """
    Orquestador agéntico con razonamiento dual (ReAct).
    Utiliza Nemotron 3 Ultra en Nebius Token Factory para decidir autónomamente
    qué herramientas auditan un activo financiero y mantiene memoria de contexto.
    """
    def __init__(self):
        self.client = OpenAI(
            base_url=settings.NEBIUS_BASE_URL,
            api_key=settings.NEBIUS_API_KEY
        )
        self.search_tool = FinancialSearchTool()
        self.sec_tool = SECTool()
        self.risk_tool = RiskEngineTool()
        self.memory = AuditMemoryManager()

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Especificación JSON Schema de las herramientas disponibles."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_market_news",
                    "description": "Busca noticias financieras recientes y sentimiento de mercado en vivo.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Consulta de búsqueda o evento financiero relevante."
                            }
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_insider_trades",
                    "description": "Audita las transacciones de ejecutivos e insiders (SEC Form 4) para un ticker.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Símbolo bursátil de la empresa (ej. NVDA, MSFT, AAPL)."
                            }
                        },
                        "required": ["ticker"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_risk_metrics",
                    "description": "Calcula el Risk Score cuantitativo (0-100), régimen de mercado y volatilidad.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Símbolo bursátil a evaluar."
                            }
                        },
                        "required": ["ticker"]
                    }
                }
            }
        ]

    def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Despachador determinista de herramientas."""
        try:
            if name == "search_market_news":
                results = self.search_tool.search_market_news(query=arguments["query"], max_results=3)
                return json.dumps(results)
            elif name == "get_insider_trades":
                results = self.sec_tool.get_insider_trades(ticker=arguments["ticker"])
                return json.dumps(results)
            elif name == "calculate_risk_metrics":
                results = self.risk_tool.evaluate_risk(ticker=arguments["ticker"])
                # Guardar snapshot en memoria si se computaron métricas
                if isinstance(results, dict) and "composite_risk_score" in results:
                    self.memory.store_audit_snapshot(
                        ticker=arguments["ticker"],
                        risk_score=results["composite_risk_score"],
                        regime=results.get("regime", "NORMAL_REGIME"),
                        summary=f"Risk Score {results['composite_risk_score']}/100, Tier: {results.get('risk_tier', 'N/A')}"
                    )
                return json.dumps(results)
            else:
                return json.dumps({"error": f"Herramienta desconocida: {name}"})
        except Exception as e:
            return json.dumps({"error": f"Fallo ejecutando {name}: {str(e)}"})

    def run(self, user_prompt: str) -> str:
        """Bucle agéntico ReAct: procesa consultas y sintetiza auditorías completas con memoria."""
        comparative_context = self.memory.get_comparative_context()

        system_instruction = (
            "Eres FinanzPrüfer, un auditor financiero y de due diligence de nivel institucional. "
            "Usa tus herramientas para recolectar evidencia fáctica (Tavily, SEC y Risk Engine). "
            f"{comparative_context}\n"
            "Si el usuario pregunta por un segundo activo o pide contrastar, compara sus métricas con el activo previo. "
            "No inventes datos. Cita las métricas obtenidas con rigor analítico."
        )

        messages = [{"role": "system", "content": system_instruction}]
        messages.extend(self.memory.get_recent_messages()[-4:])
        messages.append({"role": "user", "content": user_prompt})

        tools = self.get_tool_definitions()

        # 1. Primera pasada: Nemotron decide qué herramientas invocar
        response = self.client.chat.completions.create(
            model=settings.MODEL_REASONING,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.2
        )

        response_message = response.choices[0].message

        # 2. Si el modelo solicita llamadas a herramientas
        if response_message.tool_calls:
            messages.append(response_message)

            for tool_call in response_message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)
                tool_output = self._execute_tool(fn_name, fn_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_output
                })

            # 3. Segunda pasada: Nemotron sintetiza los datos en un dossier
            final_response = self.client.chat.completions.create(
                model=settings.MODEL_REASONING,
                messages=messages,
                temperature=0.2
            )
            res = final_response.choices[0].message
            verdict = res.content or getattr(res, "reasoning_content", None) or "No se pudo generar respuesta."
        else:
            verdict = response_message.content or getattr(response_message, "reasoning_content", None) or "No se pudo generar respuesta."

        # Registrar en la memoria conversacional
        self.memory.add_message("user", user_prompt)
        self.memory.add_message("assistant", verdict)

        return verdict
