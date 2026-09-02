import sys
import time
from src.config import settings
from src.agent.orchestrator import FinanzOrchestrator

# Asegurar codificación UTF-8 en la consola de Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def test_full_agent_workflow():
    settings.validate_nebius()
    
    print("=" * 65)
    print("FINANZPRÜFER: TEST DEL ORQUESTADOR AGÉNTICO (NEMOTRON 3 ULTRA)")
    print("=" * 65)
    
    orchestrator = FinanzOrchestrator()
    prompt = (
        "Realiza una auditoría rápida de riesgo para $NVDA. "
        "Verifica las noticias recientes del mercado, sus movimientos de insiders en la SEC "
        "y su score cuantitativo de volatilidad. Presenta un veredicto de due diligence estructurado."
    )
    
    print(f"Prompt del usuario:\n'{prompt}'\n")
    print("Iniciando bucle ReAct en Nebius Token Factory...\n")

    start_time = time.time()
    try:
        verdict = orchestrator.run(prompt)
        elapsed = time.time() - start_time

        print("[AUDITORÍA COMPLETADA CON ÉXITO]")
        print(f"Tiempo de ejecución total: {elapsed:.2f} segundos")
        print("-" * 65)
        print(verdict)
        print("=" * 65)
    except Exception as e:
        print(f"[ERROR EN EL ORQUESTADOR]: {e}")

if __name__ == "__main__":
    test_full_agent_workflow()
