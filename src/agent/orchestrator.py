import json
import logging
from typing import List, Dict, Any
from openai import OpenAI
from src.config import settings
from src.tools.search_tool import FinancialSearchTool
from src.tools.sec_tool import SECTool
from src.tools.risk_tool import RiskEngineTool
from src.tools.xbrl_tool import XBRLTool
from src.tools.fred_tool import get_macro_indicators
from src.tools.fmp_tool import FMPTool
from src.tools.cache import tool_cache
from src.agent.memory import AuditMemoryManager

logger = logging.getLogger(__name__)

class FinanzOrchestrator:
    """
    Orquestador agéntico institucional multi-hop (ReAct).
    Utiliza NVIDIA Nemotron 3 Ultra en Nebius Token Factory para coordinar
    auditorías cuantitativas, regulatorias, fundamentales y macroeconómicas en un dossier unificado.
    Aplica protocolo estricto de procedencia de datos en lista blanca con reglas anti-alucinación.
    """
    def __init__(self, memory: AuditMemoryManager = None):
        self.client = OpenAI(
            base_url=settings.NEBIUS_BASE_URL,
            api_key=settings.NEBIUS_API_KEY
        )
        self.search_tool = FinancialSearchTool()
        self.sec_tool = SECTool()
        self.risk_tool = RiskEngineTool()
        self.xbrl_tool = XBRLTool()
        self.fmp_tool = FMPTool()
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
                    "description": "Retrieves Wall Street analyst consensus data for a given stock ticker, including price targets, buy/hold/sell ratings, and earnings estimates. Returns raw search results from reputable financial sources (TipRanks, MarketBeat, Yahoo Finance, Benzinga, etc.) that must be synthesized by the orchestrator. Use this tool whenever generating the Quantitative Forecast & Consensus section (Block 2) of the audit dossier.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker symbol, e.g. 'NVDA', 'TSLA', 'AAPL'"
                            }
                        },
                        "required": ["ticker"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_recommendation_trends",
                    "description": "Retrieves historical analyst recommendation trends from Finnhub (monthly breakdown of Strong Buy, Buy, Hold, Sell, Strong Sell, consensus, and 3-month trend direction). Use for Block 2 (Quantitative Forecast & Consensus) when available.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker symbol, e.g. 'NVDA', 'TSLA'"
                            }
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
                    "name": "get_institutional_flow",
                    "description": "Retrieves recent 13F institutional ownership filings, hedge fund buying/selling patterns, and whale portfolio movements from SEC 13F disclosures via Tavily. Use for Block 3 (Forensic Regulatory Audit & Institutional Flow).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker symbol, e.g. 'NVDA', 'TSLA'"
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
                    "description": "Calcula el Composite Risk Score cuantitativo (0-100), régimen macro VIX, volatilidad realizada 60d, escenarios log-normales a 12 meses (Bear/Base/Bull Case) y probabilidad empírica a 3 meses de superar al mercado.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string", "description": "Símbolo bursátil objetivo (ej. NVDA, TSLA, SPY)."}
                        },
                        "required": ["ticker"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_fundamentals",
                    "description": "Retrieves fundamental financial data from SEC EDGAR XBRL filings for a given stock ticker. Returns operating cash flow, net income, accounts receivable, revenue, inventory, debt, and derived metrics (OCF/NI ratio, DSO, DIO, net debt, gross margin). Use this tool for Block 3 (Forensic Regulatory Audit) of the dossier to assess earnings quality and balance sheet health.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker symbol, e.g. 'NVDA', 'TSLA'"
                            }
                        },
                        "required": ["ticker"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_macro_indicators",
                    "description": "Retrieves real-time US macroeconomic indicators from FRED (Federal Reserve Economic Data), including 10Y/2Y Treasury yields, yield spread (10Y-2Y recession indicator), Fed Funds rate, unemployment, CPI YoY inflation, Core PCE price index, and macroeconomic regime assessment (RECESSION_RISK / TIGHTENING / EASING / STABLE). Use for Block 4 (Catalysts, Sentiment & Macro) or general market overviews.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_income_statement",
                    "description": "Retrieves quarterly income statement data from Financial Modeling Prep (FMP) for the last 4 quarters, including revenue, gross profit, operating income, net income, diluted EPS, gross and operating margins, and YoY growth rates. Use for Block 2 (Quantitative Forecast & Consensus).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker symbol, e.g. 'NVDA', 'TSLA'"
                            }
                        },
                        "required": ["ticker"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_earnings_surprises",
                    "description": "Retrieves historical quarterly earnings surprises from Financial Modeling Prep (FMP), comparing actual vs estimated EPS and revenue, beat streak count, and average surprise percentage. Use for Block 2 (Quantitative Forecast & Consensus).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker symbol, e.g. 'NVDA', 'TSLA'"
                            }
                        },
                        "required": ["ticker"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_revenue_by_segment",
                    "description": "Retrieves revenue breakdown by business line / product segments and geographic regions from Financial Modeling Prep (FMP), including concentration notes. Use for Block 3 (Forensic Regulatory Audit & Working Capital).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker symbol, e.g. 'NVDA', 'TSLA'"
                            }
                        },
                        "required": ["ticker"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_company_profile",
                    "description": "Retrieves comprehensive company profile from Financial Modeling Prep (FMP), including official company name, sector, industry, full-time employee count, market capitalization, beta, and corporate description. Use for the executive summary header.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "Stock ticker symbol, e.g. 'NVDA', 'TSLA'"
                            }
                        },
                        "required": ["ticker"]
                    }
                }
            }
        ]

    def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        try:
            if name == "search_market_news":
                # Market news is live and dynamic - not cached by ticker
                res = self.search_tool.search_market_news(query=arguments["query"], max_results=3)
                return json.dumps(res, ensure_ascii=False)
            elif name == "get_analyst_consensus":
                ticker = arguments.get("ticker", "").strip().upper().replace("$", "")
                cache_key = f"consensus:{ticker}"
                cached = tool_cache.get(cache_key)
                if cached:
                    logger.info(f"[CACHE HIT] get_analyst_consensus for {ticker}")
                    return cached
                res = self.search_tool.get_analyst_consensus(ticker=ticker)
                res_str = json.dumps(res, ensure_ascii=False)
                if res.get("status") != "UNAVAILABLE":
                    tool_cache.set(cache_key, res_str)
                return res_str
            elif name == "get_recommendation_trends":
                ticker = arguments.get("ticker", "").strip().upper().replace("$", "")
                cache_key = f"finnhub:{ticker}"
                cached = tool_cache.get(cache_key)
                if cached:
                    logger.info(f"[CACHE HIT] get_recommendation_trends for {ticker}")
                    return cached
                res = self.search_tool.get_recommendation_trends(ticker=ticker)
                res_str = json.dumps(res, ensure_ascii=False)
                if res.get("status") != "UNAVAILABLE":
                    tool_cache.set(cache_key, res_str)
                return res_str
            elif name == "get_insider_trades":
                ticker = arguments.get("ticker", "").strip().upper().replace("$", "")
                cache_key = f"insider:{ticker}"
                cached = tool_cache.get(cache_key)
                if cached:
                    logger.info(f"[CACHE HIT] get_insider_trades for {ticker}")
                    return cached
                trades = self.sec_tool.get_insider_trades(ticker=ticker, max_filings=5)
                filing_summary = self.sec_tool.get_latest_filing_summary(ticker=ticker)
                res_str = json.dumps({"form4_trades": trades, "latest_filing": filing_summary}, ensure_ascii=False)
                tool_cache.set(cache_key, res_str)
                return res_str
            elif name == "get_institutional_flow":
                ticker = arguments.get("ticker", "").strip().upper().replace("$", "")
                cache_key = f"institutional:{ticker}"
                cached = tool_cache.get(cache_key)
                if cached:
                    logger.info(f"[CACHE HIT] get_institutional_flow for {ticker}")
                    return cached
                res = self.search_tool.get_institutional_flow(ticker=ticker)
                res_str = json.dumps(res, ensure_ascii=False)
                if res.get("status") != "UNAVAILABLE":
                    tool_cache.set(cache_key, res_str)
                return res_str
            elif name == "get_fundamentals":
                ticker = arguments.get("ticker", "").strip().upper().replace("$", "")
                cache_key = f"fundamentals:{ticker}"
                cached = tool_cache.get(cache_key)
                if cached:
                    logger.info(f"[CACHE HIT] get_fundamentals for {ticker}")
                    return cached
                res = self.xbrl_tool.get_fundamentals(ticker=ticker)
                res_str = json.dumps(res, ensure_ascii=False)
                if res.get("status") != "UNAVAILABLE":
                    tool_cache.set(cache_key, res_str)
                return res_str
            elif name == "calculate_risk_metrics":
                ticker = arguments.get("ticker", "").strip().upper().replace("$", "")
                cache_key = f"market:{ticker}"
                cached = tool_cache.get(cache_key)
                if cached:
                    logger.info(f"[CACHE HIT] calculate_risk_metrics for {ticker}")
                    return cached
                res = self.risk_tool.evaluate_risk(ticker=ticker)
                if isinstance(res, dict) and "composite_risk_score" in res:
                    self.memory.store_audit_snapshot(
                        ticker=ticker,
                        risk_score=res["composite_risk_score"],
                        regime=res.get("macro_regime", res.get("regime", "NORMAL_REGIME")),
                        summary=f"Risk Score {res['composite_risk_score']}/100, Tier: {res.get('risk_tier', 'N/A')}"
                    )
                res_str = json.dumps(res, ensure_ascii=False)
                tool_cache.set(cache_key, res_str)
                return res_str
            elif name == "get_macro_indicators":
                cache_key = "macro:global"
                cached = tool_cache.get(cache_key)
                if cached:
                    logger.info("[CACHE HIT] get_macro_indicators")
                    return cached
                res = get_macro_indicators()
                res_str = json.dumps(res, ensure_ascii=False)
                if res.get("status") != "UNAVAILABLE":
                    tool_cache.set(cache_key, res_str)
                return res_str
            elif name == "get_income_statement":
                ticker = arguments.get("ticker", "").strip().upper().replace("$", "")
                cache_key = f"fmp_income:{ticker}"
                cached = tool_cache.get(cache_key)
                if cached:
                    logger.info(f"[CACHE HIT] get_income_statement for {ticker}")
                    return cached
                res = self.fmp_tool.get_income_statement(ticker=ticker)
                res_str = json.dumps(res, ensure_ascii=False)
                if res.get("status") != "UNAVAILABLE":
                    tool_cache.set(cache_key, res_str)
                return res_str
            elif name == "get_earnings_surprises":
                ticker = arguments.get("ticker", "").strip().upper().replace("$", "")
                cache_key = f"fmp_earnings:{ticker}"
                cached = tool_cache.get(cache_key)
                if cached:
                    logger.info(f"[CACHE HIT] get_earnings_surprises for {ticker}")
                    return cached
                res = self.fmp_tool.get_earnings_surprises(ticker=ticker)
                res_str = json.dumps(res, ensure_ascii=False)
                if res.get("status") != "UNAVAILABLE":
                    tool_cache.set(cache_key, res_str)
                return res_str
            elif name == "get_revenue_by_segment":
                ticker = arguments.get("ticker", "").strip().upper().replace("$", "")
                cache_key = f"fmp_segments:{ticker}"
                cached = tool_cache.get(cache_key)
                if cached:
                    logger.info(f"[CACHE HIT] get_revenue_by_segment for {ticker}")
                    return cached
                res = self.fmp_tool.get_revenue_by_segment(ticker=ticker)
                res_str = json.dumps(res, ensure_ascii=False)
                if res.get("status") != "UNAVAILABLE":
                    tool_cache.set(cache_key, res_str)
                return res_str
            elif name == "get_company_profile":
                ticker = arguments.get("ticker", "").strip().upper().replace("$", "")
                cache_key = f"fmp_profile:{ticker}"
                cached = tool_cache.get(cache_key)
                if cached:
                    logger.info(f"[CACHE HIT] get_company_profile for {ticker}")
                    return cached
                res = self.fmp_tool.get_company_profile(ticker=ticker)
                res_str = json.dumps(res, ensure_ascii=False)
                if res.get("status") != "UNAVAILABLE":
                    tool_cache.set(cache_key, res_str)
                return res_str
            else:
                return json.dumps({"status": "UNAVAILABLE", "reason": f"Herramienta desconocida: {name}"})
        except Exception as e:
            return json.dumps({"status": "UNAVAILABLE", "reason": "EXECUTION_ERROR", "message": str(e)})

    def run(self, user_prompt: str) -> str:
        """
        Bucle ReAct multi-hop (hasta 4 turnos iterativos).
        Garantiza la síntesis de un dossier con estricta regla de procedencia de datos en lista blanca.
        """
        comparative_context = self.memory.get_comparative_context()

        system_instruction = f"""Eres FinanzPrüfer, un auditor forense de riesgos y estratega de due diligence institucional.
Coordina tus herramientas (Tavily, analistas, SEC EDGAR Form 4 / XBRL, FRED macro, FMP y Risk Engine) para fundamentar empíricamente cada afirmación.

{comparative_context}

MANDATORY TOOL INVOCATION RULE:
You MUST invoke AT LEAST 4 of the following tools BEFORE writing ANY section of the dossier:
- calculate_risk_metrics(ticker) — ALWAYS required
- get_insider_trades(ticker) — ALWAYS required
- get_analyst_consensus(ticker) — ALWAYS required
- search_market_news(ticker) — ALWAYS required
- get_fundamentals(ticker) — ALWAYS required
- get_company_profile(ticker) — required for company profile header
- get_income_statement(ticker) / get_earnings_surprises(ticker) — required for earnings & margins
- get_revenue_by_segment(ticker) — required for business segments
- get_macro_indicators() — required if available
If you have not called at least 4 tools, DO NOT generate the dossier. Instead, call the missing tools first.

ABSOLUTE PROHIBITION:
You MUST NOT cite any financial figure, price, date, percentage, or analyst name that was NOT returned by one of the tools above in THIS conversation.
If a tool returns UNAVAILABLE for a metric, report: "[metric]: Not available — no source."
Any figure you cite MUST include the tool name in parentheses: e.g., "Risk Score: 55.8 (calculate_risk_metrics)"
Using your training data for financial figures is STRICTLY FORBIDDEN. Your training data is stale.
The ONLY source of truth is the tool responses in this conversation.
NEVER say "as of [date in the past]" — all data is real-time from tools.

MARKET OVERVIEW QUERIES:
When the user asks for a general market analysis without specifying a ticker
(e.g., "analyze the market", "how's the market doing", "market overview", "dame un análisis del mercado", "panorama macro", "¿cómo va el mercado?"):
1. Invoke calculate_risk_metrics("SPY") for current S&P 500 data, realized volatility, and VIX regime.
2. Invoke get_macro_indicators() for Treasury yields, yield spread, unemployment, inflation, and Fed Funds.
3. Invoke search_market_news("US stock market outlook catalysts") for current catalysts and market drivers.
Generate a concise market overview covering:
- Current S&P 500 level, realized volatility, and VIX regime (Bull/Sideways/Elevated/Panic).
- Key macro readings (10Y/2Y yields, yield spread, unemployment, CPI YoY, Fed Funds, and macro regime assessment).
- Top 2-3 market-moving catalysts from recent news.
End with: "For a deep audit of a specific stock, type $TICKER (e.g., $NVDA, $AAPL)."
Do NOT ask the user to fill in parameters or specify asset class. Just give the overview.

REGLA DE PROCEDENCIA ESTRICTA (Máxima prioridad, anula cualquier otra directriz):
Solo puedes afirmar datos numéricos, porcentajes, fechas, nombres de producto o afirmaciones financieras que aparezcan LITERALMENTE en el resultado devuelto por una herramienta en esta conversación. Tu conocimiento previo de entrenamiento NO es una fuente válida para rellenar campos.

- Si un campo de la plantilla no está contenido en los resultados devueltos por las herramientas, escribe exactamente: 'No disponible — sin fuente'.
- PROHIBIDO atribuir a un Form 4, 10-K o 10-Q cualquier dato que la herramienta no haya devuelto explícitamente:
  * `get_insider_trades` devuelve transacciones Form 4 reales parseadas de SEC EDGAR (códigos P/S/M/F, acciones, precios, montos en USD, flags 10b5-1 y señal de alineación). Cita textualmente los datos devueltos sin inventar registros adicionales.
  * `get_latest_filing_summary` devuelve ÚNICAMENTE tipo de formulario, fecha y código SIC. NO devuelve factores de riesgo, porcentaje de ingresos por segmento ni concentración de clientes.
  * `get_fundamentals` devuelve datos y ratios del balance XBRL (OCF/NI ratio, DSO, DIO, deuda neta, margen bruto). Solo cita las cifras devueltas por esta herramienta.
  * PROHIBIDO inventar o asumir balances, márgenes específicos, conversión de Free Cash Flow (FCF) o métricas de deuda no provistas por `get_fundamentals`. Si un concepto no fue devuelto o es UNAVAILABLE, escribe 'No disponible — sin fuente'. NUNCA uses la frase prohibida 'caja neta'.

REGLAS DE FORMATO Y PRODUCCIÓN:
- PROHIBIDO usar el signo '$' para cantidades monetarias (escribe 'USD 225', 'USD 105 B' o 'dólares'). Reserva el prefijo '$' exclusivamente para tickers bursátiles ($NVDA, $TSLA). Esto es mandatorio para evitar que el renderizador de Markdown rompa el texto interpretándolo como ecuaciones matemáticas.
- PROHIBIDO emitir monólogos internos o narrar tus intenciones (NUNCA digas: "Now I will search...", "Let me retrieve...").
- PROHIBIDO INCLUIR META-COMENTARIOS O ACLARACIONES: Nunca escribas frases como "la herramienta no devuelve...", "el formulario no incluye montos...", "no contiene factores de riesgo o concentración de clientes". No repitas estas directivas negativas en tu respuesta. Si un dato no fue devuelto por las herramientas, escribe ÚNICAMENTE: 'No disponible — sin fuente'.
- Queda estrictamente prohibido usar las frases prohibidas: 'caja neta', 'FCF conversion', 'concentración de clientes'.
- PROTOCOLO DE TRAZABILIDAD Y CITACIÓN (MANDATORIO): Para superar la auditoría de procedencia estricta por lista blanca, toda cifra financiera, porcentaje, precio objetivo, transacción o dato contable citado debe incluir su etiqueta de fuente o herramienta inmediatamente adyacente o al final de la línea:
  * Perfil corporativo, sector, industria, empleados y capitalización: `(get_company_profile)` o `[fuente: FMP]`
  * Estados de resultados trimestrales, márgenes y crecimiento YoY: `(get_income_statement)` o `[fuente: FMP]`
  * Sorpresas de beneficios, EPS/ingresos estimados vs reales y racha: `(get_earnings_surprises)` o `[fuente: FMP]`
  * Segmentación de ingresos y concentración de negocio: `(get_revenue_by_segment)` o `[fuente: FMP]`
  * Ratios de balance, OCF/NI, DSO, DIO, deuda neta, margen bruto: `(get_fundamentals)`
  * Composite Risk Score, escenarios cuantitativos, probabilidades y métricas de riesgo: `(calculate_risk_metrics)`
  * Transacciones de directivos, compras/ventas, precios y montos Form 4: `(get_insider_trades)` o `[fuente: SEC EDGAR]`
  * Precios objetivos, ratings de analistas y estimaciones: `(get_analyst_consensus)` o mención explícita de `MarketBeat`, `TipRanks`, `Yahoo Finance` o URLs devueltas
  * Noticias, ingresos en riesgo y catalizadores: `(search_market_news)` o URL de la fuente
  * Indicadores macroeconómicos y régimen: `(get_macro_indicators)` o `[fuente: FRED]`
  * Tendencias históricas de analistas: `(get_recommendation_trends)`
  * Flujo institucional y posiciones de fondos: `(get_institutional_flow)`
- Cuando tengas la información suficiente, genera SIEMPRE tu veredicto final en español estructurado exactamente en los siguientes 5 bloques:

1. RESUMEN EJECUTIVO & DECISIÓN BINARIA
   - PERFIL CORPORATIVO: Si `get_company_profile` está disponible, incluye en la cabecera: sector, industria, número de empleados y capitalización de mercado en USD (o 'No disponible — sin fuente').
   - DECISIÓN DIRECTA: [SÍ / NO / SÍ SOLO CON COBERTURA]
   - ASIGNACIÓN SUGERIDA: [% exacto del NAV de la cartera, ej. 3.0% a 3.5%]
   - Composite Risk Score (0-100), Nivel de Riesgo y Régimen Macro (según devuelva calculate_risk_metrics).
   - POR QUÉ SÍ: (Los motores y catalizadores fácticos devueltos por las herramientas).
   - POR QUÉ NO A MERCADO ABIERTO HOY: (Las banderas rojas y riesgos de cola izquierda devueltos por las herramientas).
   - ZONAS DE PRECIO OPERATIVAS:
     * Zona Cara / Distribución (> USD X si está textualmente en las fuentes, de lo contrario 'No disponible — sin fuente')
     * Zona Razonable / Entrada Escalonada (USD X - Y si está en las fuentes, de lo contrario 'No disponible — sin fuente')
     * Zona Strong Buy sin Cobertura (< USD Z si está en las fuentes, de lo contrario 'No disponible — sin fuente')
   - Diagnóstico de Asimetría: Contraste empírico entre el consenso recuperado y las métricas cuantitativas devueltas por las herramientas.

2. PRONÓSTICO CUANTITATIVO Y CONSENSO
   - Invocación obligatoria: Debes invocar `get_analyst_consensus(ticker)`. Invoca también `get_earnings_surprises(ticker)` y `get_income_statement(ticker)`. Opcionalmente invoca `get_recommendation_trends(ticker)`.
   - Sorpresas de Beneficios y Crecimiento Fundamental (FMP):
     * Si `get_earnings_surprises` y `get_income_statement` están disponibles, incluye:
       - Último trimestre: EPS real vs estimado e ingresos reales vs estimados con porcentaje de sorpresa.
       - Tasas de crecimiento interanual (YoY) de ingresos e ingreso operativo.
       - Racha de superación/fallo (cuántos trimestres consecutivos ha superado estimados).
       - Margen bruto y margen operativo con tendencia.
     * Si no están disponibles, declara explícitamente: 'Sorpresas de beneficios / Métricas trimestrales: No disponible — sin fuente'.
   - A partir de los resultados de búsqueda devueltos por `get_analyst_consensus`, extrae y reporta:
     * Rating de consenso (Strong Buy / Buy / Hold / Sell) con recuento de analistas si está disponible.
     * Precio objetivo promedio, precio objetivo máximo y precio objetivo mínimo.
     * Estimaciones de EPS y proyección de ingresos del próximo trimestre si están disponibles.
     * Cita textualmente la fuente o URL para cada dato citado.
   - Si get_recommendation_trends está disponible (status SUCCESS), incluye la evolución de ratings de analistas de los últimos 3 a 6 meses y la dirección de tendencia (IMPROVING / STABLE / DETERIORATING). Si devuelve UNAVAILABLE, confía únicamente en el consenso de Tavily.
   - Si la herramienta devuelve UNAVAILABLE o no contiene datos, declara explícitamente: 'Analyst consensus data unavailable — no source.' (o 'No disponible — sin fuente').
   - NUNCA fabriques precios objetivo ni recuentos de analistas no presentes en los snippets.
   - Rango de 3 Escenarios Cuantitativos a 12M: Cita directamente los escenarios matemáticos devueltos por `calculate_risk_metrics` (Bear Case -1 std dev, Base Case, Bull Case +1 std dev) y compáralos con los objetivos de analistas de `get_analyst_consensus`.
   - Probabilidad estimada a 3 meses de superar al S&P 500: Cita el porcentaje devuelto por `calculate_risk_metrics` (prob_outperformance_3m o outperform_prob_3m_pct). Si no está disponible, escribe 'No disponible — sin fuente'.

3. AUDITORÍA FORENSE REGULATORIA Y CAPITAL DE TRABAJO (SEC EDGAR & FMP)
   - Invocación obligatoria: Debes invocar `get_insider_trades(ticker)` Y `get_fundamentals(ticker)`. Invoca también `get_revenue_by_segment(ticker)`. Si es relevante, invoca `get_institutional_flow(ticker)`.
   - Desglose de ingresos por segmento de negocio (FMP):
     * Si `get_revenue_by_segment` está disponible, incluye el desglose de ingresos por línea de negocio (o geográfico) e identifica el segmento más grande con su porcentaje de concentración respecto al total. Si no está disponible, escribe: 'Segmentación de ingresos: No disponible — sin fuente'.
   - Resumen de transacciones Form 4: Cita textualmente las transacciones fácticas devueltas por `get_insider_trades` (fechas, filer, código, shares, precio, total USD, flag 10b5-1). Distingue ventas discrecionales vs ventas bajo plan 10b5-1 y reporta la señal de alineación.
   - 3 Factores de Estrés Contable y Capital de Trabajo (derivados de `get_fundamentals`):
     1. Calidad de conversión de utilidades: Reporta el ratio OCF/NI y su diagnóstico institucional (HEALTHY / MODERATE / INVESTIGATE). Si no está disponible, escribe: 'Calidad de conversión de utilidades: No disponible — sin fuente'.
     2. Días de cobro (DSO) y variación de inventarios (DIO): Reporta los días de cobro (DSO) y días de inventario (DIO). Si no están disponibles, escribe: 'DSO / DIO: No disponible — sin fuente'.
     3. Estructura de apalancamiento y deuda neta: Reporta la posición de deuda neta en USD (señalando si es CASH_RICH o LEVERAGED) y margen bruto devueltos por `get_fundamentals`. NUNCA uses la frase 'caja neta'. Si no está disponible, escribe: 'Estructura de apalancamiento: No disponible — sin fuente'.
   - Flujo institucional (get_institutional_flow): Si está disponible, reporta las principales instituciones o fondos que compran o venden y la dirección neta del flujo institucional. Cita la fuente. Si no está disponible, confía únicamente en las presentaciones de insiders.
   - Si alguna métrica devuelve UNAVAILABLE, declara explícitamente: '[nombre de métrica]: No disponible — sin fuente'. NUNCA fabriques números de balance.
   - Datos del último filing: Cita el formulario, fecha y código SIC devueltos por `get_latest_filing_summary` o el período XBRL.

4. CATALIZADORES, SENTIMIENTO Y MACROECONOMÍA
   - Invocación obligatoria: Debes invocar `search_market_news(ticker)` Y `get_macro_indicators()`.
   - Tailwinds operacionales y catalizadores: Cita textualmente las noticias recuperadas por `search_market_news`. Si status es UNAVAILABLE o no hay noticias, escribe 'No disponible — sin fuente'.
   - Riesgos y cuellos de botella: Cita textualmente lo reportado en las noticias.
   - Indicadores Macroeconómicos (FRED): Reporta los rendimientos del Tesoro (10Y, 2Y), el yield spread (10Y-2Y), la tasa Fed Funds, desempleo, inflación CPI/PCE y la evaluación del régimen macro (RECESSION_RISK / TIGHTENING / EASING / STABLE) devueltos por `get_macro_indicators`. Si devuelve UNAVAILABLE, escribe 'Indicadores macro: No disponible — sin fuente'.
   - Contextualización macro: Explica cómo el entorno macroeconómico actual impacta a este ticker específico (ej. "el rendimiento del 10Y presiona las valoraciones de acciones growth como NVDA" o "la política monetaria acomodaticia favorece sectores sensibles a tasas").

5. GUÍA DE ASIGNACIÓN Y ESTRUCTURA DE COBERTURA
   - Límite de asignación aconsejado (% máximo del NAV de la cartera acorde al Risk Score).
   - Parámetros de cobertura con derivados para proteger la cola izquierda (ej. Long Put Spread o Collar táctico).
   - Nivel técnico o trigger fundamental de invalidación de tesis (Hard Stop).

SELF-CHECK BEFORE RESPONDING:
Before writing the final dossier, verify:
1. Did I call at least 4 tools? If no -> call them now.
2. Does every USD figure, percentage, and date come from a tool response? If no -> remove it or mark as "Not available."
3. Am I citing any information from my training data? If yes -> remove it.

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
