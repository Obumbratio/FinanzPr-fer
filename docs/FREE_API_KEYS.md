# Free API Keys for FinanzPrüfer

All data APIs used by FinanzPrüfer have generous free tiers or require no key at all. Here is how to get and configure each key:

---

## 1. Required (Core Infrastructure)

### Nebius Token Factory
- **Provider:** Nebius AI Cloud
- **Sign up:** [https://nebius.com](https://nebius.com)
- **How to get:** Go to Token Factory dashboard → API Keys → Create Key.
- **Environment Variable:** `NEBIUS_API_KEY`
- **Base URL:** `NEBIUS_BASE_URL="https://api.studio.nebius.ai/v1"`
- **Models used:**
  - `MODEL_NANO="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"` (Educational Copilot & Personal Planning)
  - `MODEL_SUPER="nvidia/nemotron-3-super-120b-a12b"` (Comparative Analysis)
  - `MODEL_ULTRA="nvidia/Nemotron-3-Ultra-550b-a55b"` (Multi-Hop ReAct Audit Engine)

### Tavily Search
- **Provider:** Tavily AI
- **Sign up:** [https://tavily.com](https://tavily.com)
- **Free tier:** 1,000 free search queries per month.
- **How to get:** Register with email → API Keys dashboard.
- **Environment Variable:** `TAVILY_API_KEY`
- **Provides:** Live financial news, Wall Street analyst consensus, and 13F whale flows.

### SEC EDGAR
- **Provider:** U.S. Securities and Exchange Commission
- **Key required:** **No API key needed** — SEC EDGAR is free and open to the public.
- **Requirement:** User-Agent string identifying your application and email per SEC Fair Access policy.
- **Format:** `"Sample Company Name ContactEmail@domain.com"`
- **Environment Variable:** `SEC_USER_AGENT`
- **Provides:** Real-time Form 4 insider XML filings and XBRL financial statements.

---

## 2. Optional (Enhances Analysis Quality)

### FRED (Federal Reserve Economic Data)
- **Provider:** Federal Reserve Bank of St. Louis
- **Sign up:** [https://fred.stlouisfed.org](https://fred.stlouisfed.org)
- **How to get:** Log in → Click "My Account" → "API Keys" → "Request API Key".
- **Approval:** Instantaneous (automated approval).
- **Free tier:** Unlimited queries.
- **Environment Variable:** `FRED_API_KEY`
- **Provides:** 10Y/2Y Treasury yields, 10Y-2Y yield curve recession indicator, Effective Fed Funds rate, Civilian Unemployment, CPI YoY inflation, Core PCE price index, S&P 500 levels, and Initial Jobless Claims.

### Finnhub
- **Provider:** Finnhub Stock API
- **Sign up:** [https://finnhub.io/register](https://finnhub.io/register)
- **How to get:** Instant API key displayed on dashboard upon registration (no credit card required).
- **Free tier:** 60 API calls / minute.
- **Environment Variable:** `FINNHUB_API_KEY`
- **Provides:** Historical monthly breakdown of analyst recommendation trends (Strong Buy, Buy, Hold, Sell, Strong Sell) and 3-month momentum direction.

### Financial Modeling Prep (FMP)
- **Provider:** Financial Modeling Prep
- **Sign up:** [https://financialmodelingprep.com/developer](https://financialmodelingprep.com/developer)
- **How to get:** Register → verify email → copy free API key.
- **Free tier:** 250 API calls / day.
- **Environment Variable:** `FMP_API_KEY`
- **Provides:** Income statement breakdowns, revenue by business segment, earnings surprises.

### Alpha Vantage
- **Provider:** Alpha Vantage
- **Sign up:** [https://www.alphavantage.co/support/#api-key](https://www.alphavantage.co/support/#api-key)
- **How to get:** Enter email and organization; instant key generated without account registration.
- **Free tier:** 25 calls / day.
- **Environment Variable:** `ALPHA_VANTAGE_API_KEY`
- **Provides:** Balance sheet metrics and news sentiment scores.

---

## 3. Fail-Closed Protocol & Graceful Degradation

FinanzPrüfer enforces strict **fail-closed reliability**:
- If any optional API key is not configured or an endpoint is down, the system **never crashes** and **never hallucinates surrogate numbers**.
- It cleanly flags the component as `"status": "UNAVAILABLE"` and continues the audit relying on primary official sources (SEC EDGAR Form 4/XBRL and Tavily).
