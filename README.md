# FinanzPrüfer — Autonomous Financial Due Diligence Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Nebius Token Factory](https://img.shields.io/badge/Nebius-Token_Factory-blue)](https://nebius.com)
[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron_3_Family-green)](https://developer.nvidia.com)
[![Tavily](https://img.shields.io/badge/Tavily-Live_Search-orange)](https://tavily.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red)](https://streamlit.io)

> **Nebius × NVIDIA Global AI Hackathon** — *Best Apps and Agents Track*  
> An autonomous, multi-agent financial intelligence and due diligence platform powered by **NVIDIA Nemotron** foundation models running on **Nebius Token Factory**.

---

## 1. Executive Summary

**FinanzPrüfer** (*"Financial Auditor"*) transforms raw, fragmented financial data into audit-grade due diligence dossiers. By combining real-time SEC EDGAR filings, GAAP XBRL financial statements, Financial Modeling Prep (FMP) earnings surprises/segments, Finnhub analyst trends, FRED macro indicators, multi-factor quantitative risk models, and live journalistic intelligence, FinanzPrüfer automates institutional-grade equity inspection in seconds.

Unlike generic LLM wrappers that hallucinate financial figures, FinanzPrüfer enforces a **strict numerical provenance whitelist**, achieving **84.5% direct source attribution** and complete elimination of ungrounded market commentary.

---

## 2. Multi-Tier Model Architecture

FinanzPrüfer implements a smart **3-tier query classifier** that dynamically routes prompts to the optimal NVIDIA Nemotron model on Nebius Token Factory:

| Tier | Engine | Model ID | Latency | Primary Use Case |
|---|---|---|---|---|
| **Tier 1: Nano** | NVIDIA Nemotron 3 Nano (30B) | `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | ~0.8s | Conceptual financial definitions, portfolio theories (Kelly Criterion, Core-Satellite), formula explanations. |
| **Tier 2: Super** | NVIDIA Nemotron 3 Super (120B) | `nvidia/nemotron-3-super-120b-a12b` | ~2.5s | Cross-asset comparative overviews, sector landscape analysis, intermediate macro commentary. |
| **Tier 3: Ultra** | NVIDIA Nemotron 3 Ultra (550B) | `nvidia/Nemotron-3-Ultra-550b-a55b` | ~15-35s | Autonomous ReAct multi-hop forensic audits orchestrating institutional tools (SEC EDGAR, XBRL, FMP, Finnhub, FRED, Tavily) for comprehensive dossiers. |

---

## 3. System Architecture & Information Flow

```
                                  ┌──────────────────────────────┐
                                  │   Streamlit Terminal & UI    │
                                  │           (app.py)           │
                                  └──────────────┬───────────────┘
                                                 │
                   ┌─────────────────────────────┴─────────────────────────────┐
                   │                                                           │
                   ▼                                                           ▼
       [Tab 1: Chat / Terminal]                                    [Tab 2: Batch Watchlist]
                   │                                                           │
         ┌─────────┴─────────┐                                                 │
         │   classify_query  │                                                 │
         │   (fast_chat.py)  │                                                 │
         └─────────┬─────────┘                                                 │
                   │                                                           │
    ┌──────────────┼──────────────┐                                            │
    ▼              ▼              ▼                                            ▼
[Tier 1: NANO] [Tier 2: SUPER][Tier 3: ULTRA]                      [AsyncBatchAuditRunner]
Nemotron Nano  Nemotron Super FinanzOrchestrator                    (serverless_jobs.py)
  (Conceptos)   (Comparativas)  (orchestrator.py)                              │
                                       │                               ┌───────┴───────┐
                               ┌───────┴───────┐                       ▼               ▼
                               ▼               ▼                 RiskEngineTool    SECTool
                       [AuditMemory]      [ToolCache]            (5 factores)     (Form 4)
                        (memory.py)       (cache.py)
                               │
       ┌───────────────────────┼───────────────────────┬───────────────────────┐
       ▼                       ▼                       ▼                       ▼
  [SECTool]             [RiskEngineTool]      [FinancialSearchTool]       [XBRLTool]
 (sec_tool.py)          (risk_tool.py)          (search_tool.py)        (xbrl_tool.py)
       │                       │                       │                       │
 ┌─────┴─────┐           ┌─────┴─────┐           ┌─────┴─────┐                 │
 ▼           ▼           ▼           ▼           ▼           ▼                 ▼
SEC EDGAR  Latest      yfinance     Macro      Tavily News  Analyst       SEC EDGAR
Form 4 XML Filing     Historical    VIX 4      Market News  Consensus      XBRL GAAP
(Parser)   Summary    Prices (1y)  Regimes      (Live Web)  (3 Queries)   (Balance/OCF)
```

---

## 4. Institutional Tool Arsenal

The `FinanzOrchestrator` agent coordinates specialized institutional tools via JSON function calling with fail-closed error handling:

| Tool | Source | Description |
|---|---|---|
| `search_market_news` | Tavily Search API | Real-time breaking corporate news, earnings, and regulatory events |
| `get_analyst_consensus` | Financial Portals / Tavily | Wall Street price targets, consensus distribution, earnings estimates |
| `get_recommendation_trends` | Finnhub API | Historical analyst rating evolution (buy/hold/sell over time) |
| `get_insider_trades` | SEC EDGAR Form 4 XML | Direct insider filings, Rule 10b5-1 plan detection, executive alignment |
| `calculate_risk_metrics` | Risk Engine & yfinance | 5-factor risk score, 60d realized volatility, VIX regime, 12M envelopes |
| `get_fundamentals` | SEC EDGAR XBRL | Balance sheet metrics, OCF/NI ratio, DSO, DIO, net leverage |
| `get_income_statement` | FMP API | Quarterly financials, margins, YoY growth |
| `get_earnings_surprises` | FMP API | EPS/revenue actual vs estimates, beat streak |
| `get_revenue_by_segment` | FMP API | Revenue breakdown by business line and geographic regions |
| `get_company_profile` | FMP API | Sector, industry, employees, market cap |
| `get_macro_indicators` | FRED API | US Treasury yields, yield spread, Fed Funds, CPI/PCE, macro regime |

### Key Tool Capabilities
1. **`search_market_news` (`src/tools/search_tool.py`):** Queries Tavily Search API for breaking corporate events, regulatory probes, earnings announcements, and executive changes.
2. **`get_analyst_consensus` (`src/tools/search_tool.py`):** Gathers consensus price targets (Low / Median / High), Wall Street buy/hold/sell distributions, and firm ratings across institutional finance portals.
3. **`get_recommendation_trends` (`src/tools/search_tool.py`):** Pulls monthly breakdown of analyst ratings and 3-month momentum trends via Finnhub API.
4. **`get_insider_trades` (`src/tools/sec_tool.py`):** Fetches and parses official SEC EDGAR Form 4 XML filings. Differentiates pre-scheduled **Rule 10b5-1 trading plans** from discretionary open-market transactions with rate-limiting safeguards.
5. **`calculate_risk_metrics` (`src/tools/risk_tool.py`):** Calculates empirical 5-factor risk score $[0, 100]$, 60-day realized volatility, ATR-14, 52-week position, and SMA 50/200 trends. Incorporates the 4-state macro VIX regime, computes correlation ($\rho$) against $SPY, and generates 12-month log-normal scenario envelopes.
6. **`get_fundamentals` (`src/tools/xbrl_tool.py`):** Extracts official US-GAAP balance sheet and cash flow statement taxonomies from SEC EDGAR XBRL endpoints. Derives earnings quality (OCF/NI), DSO, DIO, Net Debt, and Gross Margins.
7. **`FMPTool` (`src/tools/fmp_tool.py`):** Integrates Financial Modeling Prep for quarterly income statements, earnings surprise histories, product/geographic segmentation, and corporate profiles.
8. **`get_macro_indicators` (`src/tools/fred_tool.py`):** Pulls real-time Federal Reserve Economic Data (FRED) for yield curves, inflation, unemployment, and macro regime classification.

### Supporting Infrastructure
* **`ToolCache` (`src/tools/cache.py`):** Thread-safe in-memory cache with TTL (900s / 3600s) to prevent redundant external API queries and respect rate limits.
* **`AuditMemoryManager` (`src/agent/memory.py`):** Context preservation and entity tracking to facilitate multi-turn comparative queries (e.g., comparing $NVDA vs a previously audited $TSLA).
* **`AsyncBatchAuditRunner` (`src/cloud/serverless_jobs.py`):** Multi-threaded background engine that audits entire portfolios/watchlists asynchronously with real-time status polling and risk matrix generation.

---

## 5. Dossier Structure & Whitelist Provenance

Every deep audit generated by `FinanzOrchestrator` follows a standardized 5-block forensic structure:

1. **Bloque 1: Perfil de Riesgo Cuantitativo** (Score, régimen VIX, volatilidad 60d, correlación SPY, escenarios log-normales).
2. **Bloque 2: Actividad de Insiders (SEC Form 4)** (Compras/ventas, planes Rule 10b5-1, alineación de directivos).
3. **Bloque 3: Fundamentales y Calidad Contable (SEC XBRL)** (OCF/NI, DSO, DIO, apalancamiento neto, márgenes).
4. **Bloque 4: Noticias y Consenso de Wall Street** (Eventos recientes de mercado, ratings, precio objetivo consenso vs actual).
5. **Bloque 5: Veredicto de Due Diligence y Checklist** (Calificación final, principales banderas rojas, checklist de mitigación).

---

## 6. Installation & Quickstart

### Prerequisites
* Python 3.10+ (tested on Python 3.10, 3.11, 3.12)
* Active API keys for **Nebius Token Factory** and **Tavily Search**

### 1. Clone and Create Virtual Environment
```bash
git clone https://github.com/Obumbratio/FinanzPr-fer.git
cd FinanzPr-fer

python -m venv venv
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Linux / macOS:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Credentials
Copy the `.env.example` template:
```bash
cp .env.example .env
```
Edit `.env` with your API credentials:
```ini
# Nebius Token Factory
NEBIUS_API_KEY="your_nebius_api_key_here"
NEBIUS_BASE_URL="https://api.studio.nebius.ai/v1"

# NVIDIA Nemotron Models
MODEL_NANO="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
MODEL_SUPER="nvidia/nemotron-3-super-120b-a12b"
MODEL_ULTRA="nvidia/Nemotron-3-Ultra-550b-a55b"

# Tavily Live Financial Search
TAVILY_API_KEY="your_tavily_api_key_here"

# SEC EDGAR User-Agent (Required format: CompanyName ContactEmail@domain.com)
SEC_USER_AGENT="FinanzPrufer your_email@domain.com"
```

### 4. Launch the Streamlit Platform
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 7. Verification & Smoke Test Suite

FinanzPrüfer includes a complete verification suite covering all modules:

```bash
# Verify unit and integration tests
python tests/test_memory.py                # Fast in-memory audit tracking
python tests/test_nebius_connection.py     # Nebius Token Factory latency & tokens
python tests/test_tavily_connection.py     # Tavily live financial search
python tests/test_serverless_jobs.py       # Async batch portfolio runner
python tests/test_agent_orchestrator.py    # Full ReAct loop with Nemotron 3 Ultra

# Verify domain-specific smoke scripts
python scripts/smoke_routing.py            # 14/14 query routing test cases
python scripts/smoke_cache.py              # ToolCache TTL and thread safety
python scripts/smoke_market.py             # Market snapshot & 4-state VIX regimes
python scripts/smoke_sec_xml.py            # Real SEC EDGAR Form 4 XML parser
python scripts/smoke_risk_engine.py        # 5-factor quantitative risk model
python scripts/smoke_analyst_consensus.py  # Wall Street analyst price target extraction
python scripts/smoke_xbrl.py               # SEC XBRL US-GAAP balance sheet parser
python scripts/smoke_finnhub.py            # Finnhub recommendation trends evolution
python scripts/smoke_fmp.py                # FMP quarterly financials, earnings surprises & segments
python scripts/smoke_provenance.py         # Numerical provenance whitelist test
```

---

## 8. Hackathon Compliance Checklist

| Requirement | Status | Implementation Details |
|---|:---:|---|
| **Nebius Token Factory Runtime** | Verified | Direct runtime API consumption via `https://api.studio.nebius.ai/v1`. |
| **NVIDIA Nemotron Models** | Verified | Leverages 3 open Nemotron models: **Nano (30B)**, **Super (120B)**, and **Ultra (550B)**. |
| **Open Source License** | Verified | MIT License (`LICENSE`). |
| **Track Alignment** | Verified | *Best Apps and Agents Track*. |
| **Real Tools Integration** | Verified | SEC EDGAR Form 4 XML, SEC XBRL GAAP, Tavily Search, Yahoo Finance, FRED, Finnhub, Financial Modeling Prep (FMP). |
| **Responsible AI / Grounding** | Verified | 84.5% verified numerical provenance, anti-hallucination prompt guards, explicit disclaimers. |

---

## 9. Legal & Ethical Disclaimer

**FinanzPrüfer** is an educational and research engineering platform created for the **Nebius × NVIDIA Global AI Hackathon**. It does not constitute financial, investment, legal, or tax advice. All analyses are generated autonomously from publicly available data sources (SEC EDGAR, market feeds, journalistic publications). Always consult a licensed financial professional before making investment decisions. See [`legal/DISCLAIMER.md`](legal/DISCLAIMER.md) for full terms.

---

## 10. License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for complete terms.
