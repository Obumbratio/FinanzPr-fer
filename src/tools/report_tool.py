from datetime import datetime, timezone
from typing import Optional

class ReportGenerator:
    """
    Generador de informes de Due Diligence en formato Markdown.
    Estructura auditorías completas para revisión institucional o descarga.
    """
    @staticmethod
    def create_markdown_dossier(ticker: str, analysis_text: str, user_prompt: Optional[str] = None) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        dossier = f"""# FINANZPRÜFER — AUDIT DOSSIER: ${ticker.upper()}
**Date of Inspection:** {timestamp}  
**Engine:** NVIDIA Nemotron 3 Ultra via Nebius Token Factory  
**Verification Tools:** Tavily Live Market Search & SEC EDGAR Submissions  

---

## 1. Executive Summary & Query
* **Target Symbol:** ${ticker.upper()}
* **Initial Directive:** {user_prompt or 'Standard Full Risk & Regulatory Audit'}
* **Legal Disclaimer:** Educational Audit Tool — Not Financial Advice.

---

## 2. Synthesized Due Diligence Findings
{analysis_text}

---

## 3. Methodological Footnote
This audit was autonomously compiled using a multi-hop ReAct loop. Qualitative claims were grounded in SEC Form 4 and 10-K disclosures, live journalistic context via Tavily Search API, and quantitative volatility metrics.
"""
        return dossier
