"""Smoke test: FMP financial data."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.tools.fmp_tool import FMPTool

# Asegurar codificación UTF-8 en Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

tool = FMPTool()

for ticker in ["NVDA", "GOOGL", "TSLA"]:
    print(f"\n{'='*60}")
    print(f"FMP DATA: ${ticker}")
    print(f"{'='*60}")
    
    # Profile
    profile = tool.get_company_profile(ticker)
    if profile["status"] == "SUCCESS":
        p = profile["profile"]
        emp_str = f"{p['employees']:,}" if isinstance(p.get('employees'), (int, float)) else "N/A"
        print(f"  Company: {p['company_name']} | Sector: {p['sector']}")
        print(f"  Employees: {emp_str} | MCap: ${p.get('market_cap', 0)/1e9:.0f}B")
    else:
        print(f"  Profile status: {profile['status']} - {profile.get('reason', '')}")
    
    # Income
    income = tool.get_income_statement(ticker)
    if income["status"] == "SUCCESS":
        q = income["latest_quarter"]
        print(f"  Revenue: ${q['revenue']/1e9:.1f}B | Op Margin: {q['operating_margin']*100:.1f}%")
        yoy = income.get("yoy_growth", {})
        if yoy.get("revenue_growth") is not None:
            print(f"  Revenue YoY: {yoy['revenue_growth']*100:+.1f}%")
    else:
        print(f"  Income status: {income['status']} - {income.get('reason', '')}")
    
    # Earnings
    earnings = tool.get_earnings_surprises(ticker)
    if earnings["status"] == "SUCCESS":
        latest = earnings["surprises"][0] if earnings["surprises"] else {}
        print(f"  EPS Est: {latest.get('eps_estimated', 'N/A')} | Actual: {latest.get('eps_actual', 'N/A')} | Surprise: {latest.get('surprise_pct', 'N/A')}%")
        print(f"  Beat streak: {earnings.get('beat_streak', 0)} quarters")
    else:
        print(f"  Earnings status: {earnings['status']} - {earnings.get('reason', '')}")
    
    # Segments
    segments = tool.get_revenue_by_segment(ticker)
    if segments["status"] in ("SUCCESS", "PARTIAL"):
        prod = segments.get("product_segments", {})
        if prod:
            top = max(prod.items(), key=lambda x: x[1])
            print(f"  Top segment: {top[0]} (${top[1]/1e9:.1f}B)")
        elif segments.get("geographic_segments"):
            top_geo = max(segments["geographic_segments"].items(), key=lambda x: x[1])
            print(f"  Top geo region: {top_geo[0]} (${top_geo[1]/1e9:.1f}B)")
    else:
        print(f"  Segments status: {segments['status']} - {segments.get('reason', '')}")
    
    print(f"  * [OK] ${ticker} done.")

print(f"\n{'='*60}")
print("FMP VERIFICATION COMPLETE.")
print(f"{'='*60}")
