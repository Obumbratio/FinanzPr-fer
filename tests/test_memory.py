import sys
sys.path.insert(0, ".")

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.agent.memory import AuditMemoryManager

def test_audit_memory():
    print("=" * 60)
    print("FINANZPRÜFER: TEST DE MEMORIA CONVERSACIONAL Y SNAPSHOT")
    print("=" * 60)

    memory = AuditMemoryManager()
    
    # 1. Guardar snapshot tras auditar NVDA
    memory.store_audit_snapshot(
        ticker="NVDA",
        risk_score=90.0,
        regime="ELEVATED_VOLATILITY",
        summary="Asimetría aguda de riesgo por concentración de ingresos y ventas de insiders."
    )
    
    # 2. Verificar inyección contextual
    context = memory.get_comparative_context()
    print("Contexto comparativo inyectado:")
    print(context)
    print("-" * 60)
    
    assert "NVDA" in context
    assert "90.0" in context
    print("[TEST COMPLETADO CON ÉXITO]: La memoria retiene la entidad para comparativas.")
    print("=" * 60)

if __name__ == "__main__":
    test_audit_memory()
