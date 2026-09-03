import sys
import time
sys.path.insert(0, ".")

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.config import settings
from src.cloud.serverless_jobs import NebiusServerlessJobRunner

def test_serverless_batch_execution():
    settings.validate_nebius()
    
    print("=" * 65)
    print("FINANZPRÜFER: TEST DE SERVERLESS JOBS POR LOTES (NEBIUS CLOUD)")
    print("=" * 65)

    runner = NebiusServerlessJobRunner()
    target_watchlist = ["NVDA", "TSLA", "MSFT"]
    
    print(f"Watchlist a procesar: {target_watchlist}")
    print("Encolando Job asíncrono...\n")

    start_time = time.time()
    job_id = runner.submit_watchlist_batch_job(target_watchlist)
    print(f"[JOB DESPACHADO]: ID -> {job_id}")
    print("Iniciando sondeo de telemetría (Polling loop)...\n")

    # Bucle de polling hasta completar la tarea
    while True:
        status_info = runner.get_job_status(job_id)
        status = status_info["status"]
        progress = status_info["progress"]
        processed = status_info["processed"]

        print(f"⏱️ Estado: {status:<9} | Progreso: {progress:<6} | Activos: {processed}")

        if status in ["COMPLETED", "FAILED"]:
            break
        time.sleep(1.5)

    total_time = time.time() - start_time
    print("\n" + "=" * 65)
    print(f"[JOB FINALIZADO CON ÉXITO] — Tiempo total: {total_time:.2f}s")
    print("=" * 65)

    # Inspección de resultados tabulares
    report_markdown = runner.export_batch_markdown(job_id)
    print("\nReporte Consolidado Generado:\n")
    print(report_markdown)
    print("=" * 65)

if __name__ == "__main__":
    test_serverless_batch_execution()
