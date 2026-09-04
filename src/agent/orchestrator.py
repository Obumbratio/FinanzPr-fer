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
    Orquestador agéntico institucional multi-hop (ReAct).
    Utiliza NVIDIA Nemotron 3 Ultra en Nebius Token Factory para coordinar
    auditorías cuantitativas, regulatorias y de consenso en un dossier unificado.
    """
    def __init__(self, memory: AuditMemoryManager = None):
        self.client = OpenAI(
            base_url=settings.NEBIUS_BASE_URL,
            api_key=settings.NEBIUS_API_KEY
        )
        self.search_tool = FinancialSearchTool()
        self.sec_tool = SECTool()
        self.risk_tool = RiskEngineTool()
        self.memory = memory or AuditMemoryManager()

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_market_news",
                    "description": "Recupera noticias recientes, catalizadores fundamentales y eventos regulatorios del activo.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Consulta de mercado o catalizador (ej. 'NVDA earnings guidance China rules')."}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_analyst_consensus",
                    "description": "Recupera los ratings, consenso de Wall Street y precios objetivo a 12 meses (TipRanks / FactSet).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string", "description": "Símbolo bursátil de la empresa (ej. NVDA, TSLA)."}
                        },
                        "required": ["ticker"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_insider_trades",
                    "description": "Audita presentaciones SEC Form 4 (compras y ventas de directivos) y metadatos del último 10-K.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string", "description": "Símbolo bursátil a auditar en SEC EDGAR."}
                        },
                        "required": ["ticker"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_risk_metrics",
                    "description": "Calcula el Composite Risk Score cuantitativo (0-100), régimen macro, volatilidad y sesgo de insiders.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string", "description": "Símbolo bursátil objetivo."}
                        },
                        "required": ["ticker"]
                    }
                }
            }
        ]

    def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        try:
            if name == "search_market_news":
                res = self.search_tool.search_market_news(query=arguments["query"], max_results=3)
                return json.dumps(res, ensure_ascii=False)
            elif name == "get_analyst_consensus":
                res = self.search_tool.get_analyst_consensus(ticker=arguments["ticker"])
                return json.dumps(res, ensure_ascii=False)
            elif name == "get_insider_trades":
                trades = self.sec_tool.get_insider_trades(ticker=arguments["ticker"], max_filings=5)
                filing_summary = self.sec_tool.get_latest_filing_summary(ticker=arguments["ticker"])
                return json.dumps({"form4_trades": trades, "latest_filing": filing_summary}, ensure_ascii=False)
            elif name == "calculate_risk_metrics":
                res = self.risk_tool.evaluate_risk(ticker=arguments["ticker"])
                if isinstance(res, dict) and "composite_risk_score" in res:
                    self.memory.store_audit_snapshot(
                        ticker=arguments["ticker"],
                        risk_score=res["composite_risk_score"],
                        regime=res.get("regime", "NORMAL_REGIME"),
                        summary=f"Risk Score {res['composite_risk_score']}/100, Tier: {res.get('risk_tier', 'N/A')}"
                    )
                return json.dumps(res, ensure_ascii=False)
            else:
                return json.dumps({"status": "UNAVAILABLE", "reason": f"Herramienta desconocida: {name}"})
        except Exception as e:
            return json.dumps({"status": "UNAVAILABLE", "reason": "EXECUTION_ERROR", "message": str(e)})

    def run(self, user_prompt: str) -> str:
        """
        Bucle ReAct multi-hop (hasta 4 turnos iterativos).
        Garantiza la síntesis de un dossier con integridad forense estricta y protocolo Fail-Closed.
        """
        comparative_context = self.memory.get_comparative_context()

        system_instruction = f"""Eres FinanzPrüfer, un auditor forense de riesgos y estratega de due diligence institucional.
Coordina tus herramientas (Tavily, analistas, SEC EDGAR y Risk Engine) para fundamentar empíricamente cada afirmación.

{comparative_context}

INTEGRIDAD FORENSE ESTRICTA Y PROTOCOLO FAIL-CLOSED:
- Si una herramienta devuelve status 'UNAVAILABLE', declara explícitamente en el bloque correspondiente que el dato no está disponible por limitación de la fuente oficial. Queda TERMINANTEMENTE PROHIBIDO estimar, inventar, proyectar o rellenar cifras numéricas ausentes.
- PROHIBIDO usar el signo '$' para cantidades monetarias (escribe 'USD 225', 'USD 105 B' o 'dólares'). Reserva el prefijo '$' exclusivamente para tickers bursátiles ($NVDA, $TSLA). Esto es mandatorio para evitar que el renderizador de Markdown rompa el texto interpretándolo como ecuaciones matemáticas.
- PROHIBIDO emitir monólogos internos o narrar tus intenciones (NUNCA digas: "Now I will search...", "Let me retrieve..."). Si requieres herramientas, emite la llamada de función directamente.
- Cuando tengas la información suficiente, genera SIEMPRE tu veredicto final en español estructurado exactamente en los siguientes 5 bloques:

1. RESUMEN EJECUTIVO & DECISIÓN BINARIA
   - DECISIÓN DIRECTA: [SÍ / NO / SÍ SOLO CON COBERTURA]
   - ASIGNACIÓN SUGERIDA: [% exacto del NAV de la cartera, ej. 3.0% a 3.5%]
   - Composite Risk Score (0-100), Nivel de Riesgo y Régimen Macro.
   - POR QUÉ SÍ: (Los 3 motores y catalizadores fundamentales más sólidos de la empresa).
   - POR QUÉ NO A MERCADO ABIERTO HOY: (Las 3 banderas rojas y riesgos de cola izquierda).
   - ZONAS DE PRECIO OPERATIVAS:
     * Zona Cara / Distribución (> USD X)
     * Zona Razonable / Entrada Escalonada (USD X - Y)
     * Zona Strong Buy sin Cobertura (< USD Z)
   - Diagnóstico de Asimetría: Contraste entre el optimismo público de Wall Street y las métricas reales de riesgo/insiders.

2. PRONÓSTICO CUANTITATIVO Y CONSENSO
   - Precio actual y Consenso de Wall Street (Price Target promedio a 12 meses y % Upside proyectado). Si get_analyst_consensus devuelve únicamente fragmentos textuales (snippets) sin un promedio numérico estructurado, cita textualmente los rangos reportados indicando la fuente oficial. PROHIBIDO calcular un promedio matemático inventado.
   - Rango de 3 Escenarios: Bear Case (-1 std dev), Base Consenso, Bull Case (+1 std dev).
   - Probabilidad estimada a 3 meses de superar al S&P 500 (vs. 50.9% media histórica del mercado).

3. AUDITORÍA FORENSE REGULATORIA Y CAPITAL DE TRABAJO (SEC EDGAR)
   - Resumen de transacciones recientes Form 4: si están disponibles, distinguir ventas programadas bajo regla 10b5-1 de salidas discrecionales. Si status es UNAVAILABLE, declarar limitación de la fuente.
   - 3 Factores de Estrés Contable y Capital de Trabajo:
     1. Calidad de conversión de utilidades (Free Cash Flow vs Net Income y ratio OCF/NI).
     2. Días de cobro de cuentas por cobrar (DSO) y variación de inventarios (DIO).
     3. Estructura de deuda neta y riesgos de financiamiento circular del ecosistema.
   - Concentración de negocio y factores de riesgo clave del último 10-K/10-Q reportado.

4. CATALIZADORES Y SENTIMIENTO EN VIVO (TAVILY)
   - Tailwinds operacionales (demanda de arquitectura, expansión de márgenes).
   - Riesgos geopolíticos, regulatorios y cuellos de botella de suministro.

5. GUÍA DE ASIGNACIÓN Y ESTRUCTURA DE COBERTURA
   - Límite de asignación aconsejado (% máximo del NAV de la cartera).
   - Parámetros de cobertura con derivados para proteger la cola izquierda (ej. Long Put Spread financiado o Collar táctico).
   - Nivel técnico o trigger fundamental de invalidación de tesis (Hard Stop).

NOTA LEGAL: Concluye siempre con la cláusula: 'Herramienta heurística educativa — Not financial advice.'"""

        messages = [
            {"role": "system", "content": system_instruction}
        ]
        messages.extend(self.memory.get_recent_messages()[-4:])
        messages.append({"role": "user", "content": user_prompt})

        tools = self.get_tool_definitions()

        # Bucle ReAct Multi-Hop (máximo 4 iteraciones de llamadas a herramientas)
        for _ in range(4):
            response = self.client.chat.completions.create(
                model=settings.MODEL_REASONING,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.1
            )
            response_message = response.choices[0].message

            # Si el modelo no pide más herramientas, tenemos el informe final
            if not response_message.tool_calls:
                final_text = response_message.content or getattr(response_message, "reasoning_content", None) or "No se pudo generar el dossier."
                self.memory.add_message("user", user_prompt)
                self.memory.add_message("assistant", final_text)
                return final_text

            # Procesar las herramientas requeridas en este turno
            messages.append(response_message)
            for tool_call in response_message.tool_calls:
                fn_name = tool_call.function.name
                try:
                    fn_args = json.loads(tool_call.function.arguments)
                except Exception:
                    fn_args = {}
                tool_result = self._execute_tool(fn_name, fn_args)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                })

        # Cierre forzado tras agotar iteraciones
        final_response = self.client.chat.completions.create(
            model=settings.MODEL_REASONING,
            messages=messages,
            temperature=0.1
        )
        final_text = final_response.choices[0].message.content or getattr(final_response.choices[0].message, "reasoning_content", None) or "Auditoría completada."
        self.memory.add_message("user", user_prompt)
        self.memory.add_message("assistant", final_text)
        return final_text
