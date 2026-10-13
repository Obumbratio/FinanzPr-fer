"""Smoke test: Finnhub recommendation trends."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.tools.search_tool import FinancialSearchTool

# Asegurar codificación UTF-8 en Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

tool = FinancialSearchTool()

for ticker in ["NVDA", "TSLA", "AAPL"]:
    print(f"\n{'='*60}")
    print(f"FINNHUB RECOMMENDATION TRENDS: ${ticker}")
    print(f"{'='*60}")
    result = tool.get_recommendation_trends(ticker)
    print(f"  Status: {result['status']}")
    if result["status"] == "SUCCESS":
        latest = result.get("latest", {})
        print(f"  Total analysts: {result.get('total_analysts', 'N/A')}")
        print(f"  Strong Buy: {latest.get('strong_buy', 0)}, Buy: {latest.get('buy', 0)}, "
              f"Hold: {latest.get('hold', 0)}, Sell: {latest.get('sell', 0)}, "
              f"Strong Sell: {latest.get('strong_sell', 0)}")
        print(f"  Consensus: {result.get('consensus', 'N/A')}")
        print(f"  Trend: {result.get('trend_direction', 'N/A')}")
        print(f"  * [OK] ${ticker}: Trends verified.")
    else:
        print(f"  Reason: {result.get('reason', 'Unknown')}")
        print(f"  * [WARN] ${ticker}: Trends unavailable.")

print(f"\n{'='*60}")
print("FINNHUB VERIFICATION COMPLETE.")
print(f"{'='*60}")
