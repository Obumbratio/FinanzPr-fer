import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    NEBIUS_API_KEY: str = os.getenv("NEBIUS_API_KEY", "")
    NEBIUS_BASE_URL: str = os.getenv("NEBIUS_BASE_URL", "https://api.studio.nebius.ai/v1")
    
    # Model tiers on Nebius Token Factory (3-Tier Routing)
    MODEL_NANO: str = os.getenv("MODEL_NANO", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B")      # Tier 1: conceptos, educación
    MODEL_SUPER: str = os.getenv("MODEL_SUPER", "nvidia/nemotron-3-super-120b-a12b")      # Tier 2: single-tool queries, comparativas
    MODEL_ULTRA: str = os.getenv("MODEL_ULTRA", "nvidia/Nemotron-3-Ultra-550b-a55b")      # Tier 3: dossier completo multi-hop

    # Alias compatibles con implementaciones anteriores
    MODEL_FAST: str = MODEL_NANO
    MODEL_REASONING: str = MODEL_ULTRA
    
    # Herramientas externas
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    SEC_USER_AGENT: str = os.getenv("SEC_USER_AGENT", "FinanzPrufer bot@domain.com")
    FRED_API_KEY: str = os.getenv("FRED_API_KEY", "")
    FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")
    FMP_API_KEY: str = os.getenv("FMP_API_KEY", "")
    ALPHA_VANTAGE_API_KEY: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")

    @classmethod
    def validate_nebius(cls) -> None:
        """Verifica que las credenciales de Nebius no sean nulas ni los valores por defecto."""
        if not cls.NEBIUS_API_KEY or cls.NEBIUS_API_KEY == "tu_clave_aqui":
            raise ValueError("NEBIUS_API_KEY no configurada o inválida.")

settings = Settings()
