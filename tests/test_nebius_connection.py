import time
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

    # 2. Inicializar cliente OpenAI compatible con Nebius
    client = OpenAI(
        base_url=settings.NEBIUS_BASE_URL,
        api_key=settings.NEBIUS_API_KEY
    )

    prompt = (
        "Actúa como FinanzPrüfer, auditor financiero de élite. "
        "En una sola oración concisa, explica qué riesgo evalúa "
        "un análisis de concentración en el formulario SEC 13F."
    )

    start_time = time.time()
    try:
        response = client.chat.completions.create(
            model=settings.MODEL_REASONING,
            messages=[
                {"role": "system", "content": "Eres un asistente de due diligence financiero riguroso."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=150
        )
        latency = time.time() - start_time

        # 3. Resultados y telemetría
        content = response.choices[0].message.content
        usage = response.usage

        print("[CONEXIÓN EXITOSA]")
        print(f"Respuesta:\n{content.strip()}\n")
        print("-" * 60)
        print(f"Latencia: {latency:.2f} segundos")
        if usage:
            print(f"Tokens Prompt (Entrada):     {usage.prompt_tokens}")
            print(f"Tokens Completion (Salida):  {usage.completion_tokens}")
            print(f"Tokens Totales:              {usage.total_tokens}")
        print("=" * 60)

    except Exception as e:
        print(f"\n[FALLO DE CONEXIÓN] Ocurrió un error al contactar Nebius Token Factory:")
        print(f"Detalle del error: {e}")

if __name__ == "__main__":
    test_nemotron_connection()
