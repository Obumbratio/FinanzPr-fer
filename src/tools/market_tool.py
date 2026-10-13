import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


class MarketDataTool:
    """
    Herramienta agéntica institucional de métricas de mercado cuantitativas.
    Extrae datos empíricos en tiempo real y series de precios vía yfinance con
    arquitectura fail-closed.
    """

    def __init__(self):
        pass

    def get_market_snapshot(self, ticker: str) -> Dict[str, Any]:
        """
        Obtiene una instantánea empírica completa del mercado para un activo:
        - Precio actual, cierre previo y variación diaria (%chg).
        - Rango de 52 semanas (mínimo, máximo y posición relativa en %).
        - Volatilidad realizada anualizada (60 días de negociación).
        - Average True Range a 14 períodos (ATR 14).
        - Medias móviles simples (SMA 50, SMA 200) y distancia a la SMA 200.
        - Volumen medio diario de los últimos 30 días.
        """
        clean_ticker = ticker.replace("$", "").strip().upper()
        as_of = datetime.now(timezone.utc).isoformat()

        if not clean_ticker:
            return {
                "status": "UNAVAILABLE",
                "reason": "EMPTY_TICKER",
                "ticker": clean_ticker,
                "as_of": as_of
            }

        try:
            ticker_obj = yf.Ticker(clean_ticker)
            # Descargamos 1 año de datos históricos diarios
            df = ticker_obj.history(period="1y")

            if df is None or df.empty or len(df) < 5:
                return {
                    "status": "UNAVAILABLE",
                    "reason": f"INSUFFICIENT_DATA_FOR_TICKER: {clean_ticker}",
                    "ticker": clean_ticker,
                    "as_of": as_of
                }

            # 1. Precios y variación diaria
            current_price = float(df["Close"].iloc[-1])
            previous_close = float(df["Close"].iloc[-2]) if len(df) >= 2 else current_price
            daily_change = current_price - previous_close
            daily_change_pct = ((current_price - previous_close) / previous_close) * 100.0 if previous_close != 0 else 0.0

            # 2. Rango de 52 semanas (hasta 252 días de negociación)
            df_52w = df.iloc[-min(len(df), 252):]
            week_52_high = float(df_52w["High"].max())
            week_52_low = float(df_52w["Low"].min())
            
            if week_52_high > week_52_low:
                week_52_position_pct = ((current_price - week_52_low) / (week_52_high - week_52_low)) * 100.0
            else:
                week_52_position_pct = 50.0

            # 3. Volatilidad anualizada realizada (60 días, sqrt(252))
            close_series = df["Close"]
            log_returns = np.log(close_series / close_series.shift(1)).dropna()
            recent_log_ret = log_returns.tail(min(len(log_returns), 60))

            if len(recent_log_ret) >= 5:
                daily_std = float(recent_log_ret.std(ddof=1))
                realized_vol_60d = daily_std * np.sqrt(252)
                realized_vol_60d_pct = realized_vol_60d * 100.0
            else:
                realized_vol_60d = 0.0
                realized_vol_60d_pct = 0.0

            # 4. Average True Range a 14 períodos (ATR 14)
            prev_close_series = df["Close"].shift(1)
            tr1 = df["High"] - df["Low"]
            tr2 = (df["High"] - prev_close_series).abs()
            tr3 = (df["Low"] - prev_close_series).abs()
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1).dropna()
            
            atr_14 = float(true_range.tail(min(len(true_range), 14)).mean()) if not true_range.empty else 0.0

            # 5. Medias móviles simples (SMA 50, SMA 200) y distancia a SMA 200
            sma_50 = float(df["Close"].tail(50).mean()) if len(df) >= 50 else None
            sma_200 = float(df["Close"].tail(200).mean()) if len(df) >= 200 else None
            
            if sma_200 and sma_200 > 0:
                sma_200_distance_pct = ((current_price - sma_200) / sma_200) * 100.0
            else:
                sma_200_distance_pct = None

            # 6. Volumen medio diario de los últimos 30 días
            avg_daily_volume_30d = float(df["Volume"].tail(min(len(df), 30)).mean())

            return {
                "status": "SUCCESS",
                "source": "yfinance",
                "ticker": clean_ticker,
                "as_of": as_of,
                "current_price": round(current_price, 2),
                "previous_close": round(previous_close, 2),
                "daily_change": round(daily_change, 2),
                "daily_change_pct": round(daily_change_pct, 2),
                "week_52_high": round(week_52_high, 2),
                "week_52_low": round(week_52_low, 2),
                "week_52_position_pct": round(week_52_position_pct, 2),
                "realized_volatility_60d": round(realized_vol_60d, 4),
                "realized_volatility_60d_pct": round(realized_vol_60d_pct, 2),
                "atr_14": round(atr_14, 2),
                "sma_50": round(sma_50, 2) if sma_50 is not None else None,
                "sma_200": round(sma_200, 2) if sma_200 is not None else None,
                "sma_200_distance_pct": round(sma_200_distance_pct, 2) if sma_200_distance_pct is not None else None,
                "avg_daily_volume_30d": int(avg_daily_volume_30d)
            }

        except Exception as e:
            logger.error(f"Error extrayendo snapshot de mercado para {clean_ticker}: {e}")
            return {
                "status": "UNAVAILABLE",
                "reason": str(e),
                "ticker": clean_ticker,
                "as_of": as_of
            }

    def get_macro_vix(self) -> Dict[str, Any]:
        """
        Consulta el símbolo '^VIX' para obtener el valor actual del índice de volatilidad,
        su variación diaria y la clasificación del régimen macroeconómico.
        """
        as_of = datetime.now(timezone.utc).isoformat()
        try:
            vix_ticker = yf.Ticker("^VIX")
            df = vix_ticker.history(period="5d")

            if df is None or df.empty or len(df) < 1:
                return {
                    "status": "UNAVAILABLE",
                    "reason": "VIX_DATA_UNAVAILABLE",
                    "as_of": as_of,
                    "regime": "UNKNOWN"
                }

            current_vix = float(df["Close"].iloc[-1])
            prev_vix = float(df["Close"].iloc[-2]) if len(df) >= 2 else current_vix
            daily_change = current_vix - prev_vix
            daily_change_pct = ((current_vix - prev_vix) / prev_vix) * 100.0 if prev_vix != 0 else 0.0

            # Clasificación de 4 regímenes macroeconómicos
            if current_vix < 15.0:
                regime = "BULL / STABLE_ACCUMULATION"
            elif 15.0 <= current_vix < 22.0:
                regime = "SIDEWAYS / NORMAL_REGIME"
            elif 22.0 <= current_vix < 30.0:
                regime = "BEAR / ELEVATED_VOLATILITY"
            else:
                regime = "PANIC / CRITICAL_VOLATILITY"

            return {
                "status": "SUCCESS",
                "source": "yfinance",
                "as_of": as_of,
                "vix_value": round(current_vix, 2),
                "previous_close": round(prev_vix, 2),
                "daily_change": round(daily_change, 2),
                "daily_change_pct": round(daily_change_pct, 2),
                "regime": regime
            }

        except Exception as e:
            logger.error(f"Error consultando índice macro VIX: {e}")
            return {
                "status": "UNAVAILABLE",
                "reason": str(e),
                "as_of": as_of,
                "regime": "UNKNOWN"
            }
