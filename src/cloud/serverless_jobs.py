import json
import time
import uuid
import logging
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import OpenAI

from src.config import settings
from src.tools.risk_tool import RiskEngineTool
from src.tools.sec_tool import SECTool
from src.tools.search_tool import FinancialSearchTool

logger = logging.getLogger(__name__)

class NebiusServerlessJobRunner:
    """
    Gestor y orquestador de tareas en segundo plano (Background Serverless Jobs).
    Procesa Watchlists financieras por lotes sin bloquear el hilo principal ni la interfaz.
    """
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.risk_tool = RiskEngineTool()
        self.sec_tool = SECTool()
        self.search_tool = FinancialSearchTool()
        self.client = OpenAI(
            base_url=settings.NEBIUS_BASE_URL,
            api_key=settings.NEBIUS_API_KEY
        )

    def submit_watchlist_batch_job(self, watchlist: List[str]) -> str:
        """
        Encola un trabajo por lotes para auditar múltiples activos de forma concurrente.
        Retorna el identificador único del Job (job_id).
        """
        job_id = f"job-nebius-{uuid.uuid4().hex[:8]}"
        clean_watchlist = [t.strip().upper().replace("$", "") for t in watchlist if t.strip()]

        self.jobs[job_id] = {
            "job_id": job_id,
            "status": "QUEUED",
            "progress": 0.0,
            "watchlist": clean_watchlist,
            "total_items": len(clean_watchlist),
            "processed_items": 0,
            "submitted_at": datetime.utcnow().isoformat(),
            "completed_at": None,
            "results": {},
            "errors": []
        }

        # Lanzar ejecución desacoplada en segundo plano
        worker_thread = threading.Thread(
            target=self._execute_batch_worker,
            args=(job_id,),
            daemon=True
        )
        worker_thread.start()
        return job_id

    def _execute_batch_worker(self, job_id: str) -> None:
        """Worker que procesa cada ticker en segundo plano y computa el dossier."""
        job = self.jobs.get(job_id)
        if not job:
            return

        job["status"] = "RUNNING"
        total = job["total_items"]

        for idx, ticker in enumerate(job["watchlist"], 1):
            try:
                # 1. Extracción de métricas heurísticas y regulatorias
                risk_metrics = self.risk_tool.evaluate_risk(ticker)
                insider_trades = self.sec_tool.get_insider_trades(ticker, max_filings=3)
                news = self.search_tool.search_market_news(f"{ticker} stock news", max_results=2)

                # 2. Síntesis condensada vía Nemotron 3 Ultra
                prompt = (
                    f"Sintetiza un veredicto de due diligence para ${ticker} en 2 oraciones concisas.\n"
                    f"Risk Metrics: {json.dumps(risk_metrics)}\n"
                    f"Insider Activity: {len(insider_trades)} registros Form 4 recientes.\n"
                    f"Headline Context: {[n.get('title') for n in news]}"
                )

                response = self.client.chat.completions.create(
                    model=settings.MODEL_REASONING,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Eres un auditor financiero institucional de élite. Responde DIRECTAMENTE "
                                "con el veredicto final en 2 oraciones concisas. No incluyas preámbulos, "
                                "no repitas las instrucciones ni muestres notas internas."
                            )
                        },
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=150,
                    temperature=0.1
                )
                verdict = response.choices[0].message.content.strip()

                job["results"][ticker] = {
                    "risk_score": risk_metrics.get("composite_risk_score"),
                    "risk_tier": risk_metrics.get("risk_tier"),
                    "regime": risk_metrics.get("regime"),
                    "insider_signals": len(insider_trades),
                    "verdict": verdict
                }

            except Exception as e:
                job["errors"].append({"ticker": ticker, "error": str(e)})

            job["processed_items"] = idx
            job["progress"] = round((idx / total) * 100, 1)

        job["status"] = "COMPLETED"
        job["completed_at"] = datetime.utcnow().isoformat()

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Consulta el estado, telemetría y porcentaje de avance de un trabajo."""
        job = self.jobs.get(job_id)
        if not job:
            return {"error": f"Job ID {job_id} no encontrado", "status": "UNKNOWN"}
        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "progress": f"{job['progress']}%",
            "processed": f"{job['processed_items']}/{job['total_items']}",
            "completed_at": job["completed_at"]
        }

    def get_job_results(self, job_id: str) -> Dict[str, Any]:
        """Obtiene el payload estructurado con todos los resultados del lote."""
        job = self.jobs.get(job_id)
        if not job:
            return {"error": "Job no encontrado"}
        return job.get("results", {})

    def export_batch_markdown(self, job_id: str) -> str:
        """Compila los resultados consolidados de la Watchlist en formato Markdown."""
        job = self.jobs.get(job_id)
        if not job or job.get("status") != "COMPLETED":
            return "El job no existe o aún no ha completado su procesamiento."

        md = [
            f"# FINANZPRÜFER — CONSOLIDATED WATCHLIST AUDIT",
            f"**Job ID:** `{job_id}`  ",
            f"**Execution Timestamp:** {job['completed_at']} UTC  ",
            f"**Total Assets Audited:** {job['total_items']}\n",
            "| Asset | Risk Score | Risk Tier | Market Regime | Executive Verdict |",
            "| :--- | :---: | :--- | :--- | :--- |"
        ]

        for ticker, data in job["results"].items():
            clean_verdict = data['verdict'].replace("\n", " ")
            md.append(
                f"| **${ticker}** | {data['risk_score']}/100 | {data['risk_tier']} | "
                f"`{data['regime']}` | {clean_verdict} |"
            )

        return "\n".join(md)
