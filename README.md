# FinanzPrüfer — Autonomous Financial Due Diligence Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Nebius Token Factory](https://img.shields.io/badge/Nebius-Token_Factory-blue)](https://nebius.com)
[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron_3_Ultra-green)](https://developer.nvidia.com)
[![Tavily](https://img.shields.io/badge/Tavily-Live_Search-orange)](https://tavily.com)

Autonomous financial intelligence and due diligence platform submitted to the **Nebius x NVIDIA Global AI Hackathon** under the **Best Apps and Agents Track**.

---

## Architecture Overview
FinanzPrüfer implements a dual-tier agentic architecture:
* **Reasoning Engine (ReAct):** `nvidia/Nemotron-3-Ultra` via Nebius Token Factory for multi-tool orchestration, SEC parsing, and risk evaluation.
* **Fast Conversational Copilot:** `nvidia/Nemotron-Nano` via Nebius Token Factory for rapid conceptual and educational financial queries.
* **Live Market Intelligence:** Real-time search runtime calls via **Tavily Search API**.
* **Regulatory Auditing:** Automated SEC EDGAR integration (Form 4 insider transactions and 10-K risk disclosures).
* **Asynchronous Batch Processing:** Background portfolio auditing inspired by **Nebius Serverless Jobs** architecture.

```
[User UI / Streamlit Terminal]
│
├──► Fast Conceptual Queries ──► Nemotron Nano (Low Latency / Credit Efficient)
│
└──► Deep Regulatory Audit ────► Nemotron 3 Ultra (ReAct Loop)
      │
      ┌──────────────────────────────┼──────────────────────────────┐
      ▼                              ▼                              ▼
 [Tavily API]                  [SEC EDGAR Tool]             [Risk Engine Tool]
(Live Market News)              (Form 4 & 10-K Filings)       (4-State Macro Regime)
      │                              │                              │
      └──────────────────────────────┼──────────────────────────────┘
                                     ▼
                        [Consolidated Audit Dossier]
```

---

## Significant Updates During Hackathon Submission Period
To comply with official competition rules regarding pre-existing foundations, FinanzPrüfer underwent the following core transformations:
1. **Core LLM Migration:** Replaced external third-party model endpoints with **NVIDIA Nemotron 3 Ultra** and **Nemotron Nano** running on **Nebius Token Factory**.
2. **Autonomous Tool Calling:** Transformed static analysis scripts into executable JSON-schema function definitions under a ReAct decision loop.
3. **Live Web Verification:** Added runtime integration with **Tavily Search API** to cross-examine SEC filings against breaking journalistic headlines.
4. **Serverless Background Processing:** Built the `NebiusServerlessJobRunner` pipeline to decouple heavy multi-ticker watchlist analysis from the user interface.
5. **Modernized Multi-Tab UI:** Created an institutional Streamlit dashboard supporting single-asset audits, entity memory comparisons, and batch portfolio exports.

---

## Installation & Local Reproduction

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Obumbratio/FinanzPr-fer.git
   cd FinanzPr-fer
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   Copy `.env.example` to `.env` and provide your credentials:
   ```env
   NEBIUS_API_KEY="your_nebius_api_key"
   NEBIUS_BASE_URL="https://api.studio.nebius.ai/v1"
   MODEL_REASONING="nvidia/Nemotron-3-Ultra-550b-a55b"
   MODEL_FAST="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
   TAVILY_API_KEY="your_tavily_api_key"
   SEC_USER_AGENT="FinanzPrufer bot@domain.com"
   ```

4. **Launch the platform:**
   ```bash
   streamlit run app.py
   ```

---

## License

Distributed under the MIT License. See `LICENSE` for details.
