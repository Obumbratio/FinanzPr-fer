import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    NEBIUS_API_KEY: str = os.getenv("NEBIUS_API_KEY", "")
    NEBIUS_BASE_URL: str = os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.ai/v1")
    
    # Modelos NVIDIA verificados en Nebius Token Factory
    MODEL_REASONING: str = os.getenv("MODEL_REASONING", "nvidia/Nemotron-3-Ultra-550b-a55b")
    MODEL_FAST: str = os.getenv("MODEL_FAST", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B")
    
    # Herramientas externas
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    SEC_USER_AGENT: str = os.getenv("SEC_USER_AGENT", "FinanzPrufer bot@domain.com")

    @classmethod
    def validate_nebius(cls) -> None:
        """Verifica que las credenciales de Nebius no sean nulas ni los valores por defecto."""
        if not cls.NEBIUS_API_KEY or cls.NEBIUS_API_KEY == "tu_clave_aqui":
            raise ValueError("NEBIUS_API_KEY no configurada o inválida.")

settings = Settings()
