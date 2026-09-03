import sys
import time
sys.path.insert(0, ".")

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from openai import OpenAI
from src.config import settings

def test_nemotron_connection():
    # 1. Validar que la API key exista
    settings.validate_nebius()
    
    print("=" * 60)
    print("FINANZPRÜFER: TEST DE INFERENCIA EN NEBIUS TOKEN FACTORY")
    print("=" * 60)
    print(f"Base URL: {settings.NEBIUS_BASE_URL}")
    print(f"Modelo objetivo: {settings.MODEL_REASONING}")
    print("Enviando prompt de prueba...\n")

    client = OpenAI(
        base_url=settings.NEBIUS_BASE_URL,
        api_key=settings.NEBIUS_API_KEY
    )

    prompt = (
        "Explica brevemente en un solo párrafo qué es el riesgo de concentración "
        "en una auditoría de filings regulatorios (Form 13F)."
    )

    start_time = time.time()
    try:
        response = client.chat.completions.create(
            model=settings.MODEL_REASONING,
            messages=[
                {"role": "system", "content": "Eres un auditor financiero institucional de alto nivel."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=250
        )
        latency = time.time() - start_time

        print("[CONEXIÓN EXITOSA]")
        print("Respuesta:")
        print(response.choices[0].message.content)
        print("\n" + "-" * 60)
        print(f"Latencia: {latency:.2f} segundos")
        print(f"Tokens Prompt (Entrada):     {response.usage.prompt_tokens}")
        print(f"Tokens Completion (Salida):  {response.usage.completion_tokens}")
        print(f"Tokens Totales:              {response.usage.total_tokens}")
        print("=" * 60)
    except Exception as e:
        print(f"[ERROR]: Fallo al conectar con Nebius AI Cloud: {e}")

if __name__ == "__main__":
    test_nemotron_connection()
