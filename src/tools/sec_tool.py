import time
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from src.config import settings

logger = logging.getLogger(__name__)

class SECTool:
    """
    Extractor de filings y movimientos regulatorios en la SEC EDGAR.
    Implementa protocolo Fail-Closed y patrón Circuit Breaker para protección contra 429 y caídas.
    Descarga y parsea formularios Form 4 XML auténticos bajo el límite estricto de 10 req/s (0.12s cooldown).
    Bajo ninguna circunstancia genera datos sintéticos ni filings falsos.
    """
    def __init__(self, user_agent: str = settings.SEC_USER_AGENT):
        self.headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
        self._ticker_map: Dict[str, str] = {}
        # Estado del Circuit Breaker
        self.circuit_open: bool = False
        self.last_failure_timestamp: float = 0.0
        self.cooldown_period: float = 30.0  # segundos

    def _check_circuit(self) -> bool:
        """Verifica si el circuito está abierto o si ya expiró el periodo de enfriamiento."""
        if self.circuit_open:
            if time.time() - self.last_failure_timestamp > self.cooldown_period:
                logger.info("[CIRCUIT BREAKER SEC]: Enfriamiento finalizado. Circuito HALF-OPEN.")
                self.circuit_open = False
                return True
            return False
        return True

    def _trip_circuit(self, reason: str) -> None:
        """Abre el circuito preventivo ante errores críticos o 429 Rate Limits."""
        self.circuit_open = True
        self.last_failure_timestamp = time.time()
        logger.warning(f"[CIRCUIT BREAKER SEC ACTIVADO]: {reason}. Modo Fail-Closed activo.")

    def _get_cik(self, ticker: str) -> str:
        """Obtiene el CIK paddeado a 10 dígitos requerido por la API de la SEC."""
        ticker = ticker.upper().replace("$", "").strip()
        if not self._ticker_map:
            try:
                time.sleep(0.12)
                url = "https://www.sec.gov/files/company_tickers.json"
                res = requests.get(url, headers=self.headers, timeout=6)
                if res.status_code == 200:
                    data = res.json()
                    self._ticker_map = {
                        str(item["ticker"]).upper(): str(item["cik_str"]).zfill(10)
                        for item in data.values()
                    }
                elif res.status_code in [429, 403]:
                    self._trip_circuit(f"SEC HTTP {res.status_code} en índice de tickers")
            except Exception as e:
                logger.warning(f"No se pudo descargar el índice de tickers SEC: {e}")
        
        return self._ticker_map.get(ticker, "")

    def _detect_10b51(
        self,
        tx_node: ET.Element,
        root_node: ET.Element,
        footnotes: Dict[str, str],
        doc_10b51: Optional[bool]
    ) -> Optional[bool]:
        """
        Determina de manera fehaciente si una transacción fue ejecutada bajo un plan Rule 10b5-1.
        Devuelve True, False o None (si es indeterminado). NUNCA asume.
        """
        # 1. Inspeccionar transactionCoding por atributo o subelemento
        coding = tx_node.find("transactionCoding")
        if coding is not None:
            for child in coding:
                tag_lower = child.tag.lower()
                text_val = (child.text or "").strip().lower()
                if "10b5" in tag_lower or "10b5" in text_val:
                    if text_val in ["1", "true"]:
                        return True
                    elif text_val in ["0", "false"]:
                        return False
            for k, v in coding.attrib.items():
                if "10b5" in k.lower():
                    v_clean = str(v).strip().lower()
                    if v_clean in ["1", "true"]:
                        return True
                    elif v_clean in ["0", "false"]:
                        return False

        # 2. Footnotes referenciadas directamente en esta transacción
        tx_fn_ids = [el.get("id") for el in tx_node.findall(".//footnoteId") if el.get("id")]
        for fn_id in tx_fn_ids:
            fn_text = footnotes.get(fn_id, "").lower()
            if any(term in fn_text for term in ["10b5-1", "10b5", "rule 10b5"]):
                if "not pursuant to" in fn_text or "not intended to satisfy" in fn_text:
                    return False
                return True

        # 3. Checkbox a nivel de documento (<aff10b5One> o <rule10b51Flag>)
        if doc_10b51 is not None:
            return doc_10b51

        # 4. Búsqueda contextual en todas las notas al pie del filing
        for fn_id, fn_text in footnotes.items():
            fn_lower = fn_text.lower()
            if any(term in fn_lower for term in ["10b5-1", "10b5", "rule 10b5"]):
                if "not pursuant to" in fn_lower or "not intended to satisfy" in fn_lower:
                    return False
                return True

        return None

    def get_insider_trades(self, ticker: str, max_filings: int = 5) -> Dict[str, Any]:
        """
        Recupera y parsea transacciones de insiders reales (Form 4 XML) desde SEC EDGAR.
        Protocolo Fail-Closed: ante fallas de API devuelve status UNAVAILABLE sin inventar registros.
        """
        ticker = ticker.upper().replace("$", "").strip()
        as_of = datetime.now(timezone.utc).isoformat()

        if not self._check_circuit():
            return {
                "status": "UNAVAILABLE",
                "reason": "SEC_EDGAR_RATE_LIMIT",
                "ticker": ticker,
                "message": "SEC EDGAR en periodo de enfriamiento por rate limit previo."
            }

        cik = self._get_cik(ticker)
        if not cik:
            return {
                "status": "UNAVAILABLE",
                "reason": "CIK_NOT_FOUND",
                "ticker": ticker,
                "message": f"No se encontró un CIK oficial para el símbolo {ticker} en el directorio de la SEC."
            }

        # 1. Obtener listado de submissions
        url_sub = f"https://data.sec.gov/submissions/CIK{cik}.json"
        try:
            time.sleep(0.12)
            res_sub = requests.get(url_sub, headers=self.headers, timeout=7)
            if res_sub.status_code == 429:
                self._trip_circuit("HTTP 429 Too Many Requests de SEC EDGAR")
                return {
                    "status": "UNAVAILABLE",
                    "reason": "SEC_EDGAR_RATE_LIMIT",
                    "ticker": ticker
                }
            elif res_sub.status_code == 403:
                self._trip_circuit("HTTP 403 Forbidden de SEC EDGAR")
                return {
                    "status": "UNAVAILABLE",
                    "reason": "HTTP_403_FORBIDDEN",
                    "ticker": ticker
                }
            elif res_sub.status_code != 200:
                return {
                    "status": "UNAVAILABLE",
                    "reason": f"SEC_HTTP_{res_sub.status_code}",
                    "ticker": ticker
                }

            data = res_sub.json()
            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accession_numbers = recent.get("accessionNumber", [])
            primary_docs = recent.get("primaryDocument", [])

            # Filtrar los últimos N filings tipo '4' o '4/A'
            target_filings = []
            for i, form in enumerate(forms):
                if form in ["4", "4/A"]:
                    target_filings.append({
                        "form": form,
                        "date": dates[i] if i < len(dates) else "",
                        "accession": accession_numbers[i] if i < len(accession_numbers) else "",
                        "primary_doc": primary_docs[i] if i < len(primary_docs) else ""
                    })
                if len(target_filings) >= max_filings:
                    break

            all_trades: List[Dict[str, Any]] = []
            parsed_filings_count = 0

            # 2. Descargar y parsear el XML de cada Form 4
            for filing_meta in target_filings:
                acc = filing_meta["accession"]
                primary_doc = filing_meta["primary_doc"]
                if not acc or not primary_doc:
                    continue

                acc_no_dashes = acc.replace("-", "")
                doc_name = primary_doc.split("/")[-1]
                xml_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_dashes}/{doc_name}"

                try:
                    time.sleep(0.12)
                    res_xml = requests.get(xml_url, headers=self.headers, timeout=6)
                    if res_xml.status_code == 429:
                        self._trip_circuit("HTTP 429 descargando XML Form 4")
                        return {
                            "status": "UNAVAILABLE",
                            "reason": "SEC_EDGAR_RATE_LIMIT",
                            "ticker": ticker
                        }
                    elif res_xml.status_code == 403:
                        self._trip_circuit("HTTP 403 descargando XML Form 4")
                        return {
                            "status": "UNAVAILABLE",
                            "reason": "HTTP_403_FORBIDDEN",
                            "ticker": ticker
                        }
                    elif res_xml.status_code != 200:
                        logger.warning(f"Error HTTP {res_xml.status_code} recuperando {xml_url}")
                        continue

                    root = ET.fromstring(res_xml.content)
                    parsed_filings_count += 1

                    # Identidad y cargo del reportante
                    owner_name = root.findtext(".//reportingOwner/reportingOwnerId/rptOwnerName", default="").strip()
                    if not owner_name:
                        owner_name = root.findtext(".//rptOwnerName", default="Insider").strip()

                    officer_title = root.findtext(".//reportingOwnerRelationship/officerTitle", default="").strip()
                    is_dir = root.findtext(".//reportingOwnerRelationship/isDirector", default="0").strip().lower()
                    is_off = root.findtext(".//reportingOwnerRelationship/isOfficer", default="0").strip().lower()
                    is_ten = root.findtext(".//reportingOwnerRelationship/isTenPercentOwner", default="0").strip().lower()

                    if officer_title:
                        title = officer_title
                    elif is_dir in ["1", "true"]:
                        title = "Director"
                    elif is_off in ["1", "true"]:
                        title = "Officer"
                    elif is_ten in ["1", "true"]:
                        title = "10% Owner"
                    else:
                        title = "Insider"

                    # Mapeo de notas al pie (Footnotes)
                    footnotes: Dict[str, str] = {}
                    for fn in root.findall(".//footnotes/footnote"):
                        fn_id = fn.get("id")
                        if fn_id:
                            footnotes[fn_id] = (fn.text or "").strip()

                    # Flag 10b5-1 a nivel de documento
                    aff_elem = root.findtext(".//aff10b5One") or root.findtext(".//rule10b51Flag")
                    doc_10b51: Optional[bool] = None
                    if aff_elem is not None:
                        aff_val = aff_elem.strip().lower()
                        if aff_val in ["1", "true"]:
                            doc_10b51 = True
                        elif aff_val in ["0", "false"]:
                            doc_10b51 = False

                    # Iterar transacciones no derivadas
                    for tx in root.findall(".//nonDerivativeTransaction"):
                        try:
                            tx_date = tx.findtext(".//transactionDate/value", default=filing_meta["date"]).strip()
                            code = tx.findtext(".//transactionCoding/transactionCode", default="").strip().upper()
                            shares_str = tx.findtext(".//transactionAmounts/transactionShares/value", default="0").strip()
                            price_str = tx.findtext(".//transactionAmounts/transactionPricePerShare/value", default="").strip()

                            try:
                                shares = float(shares_str) if shares_str else 0.0
                            except (ValueError, TypeError):
                                shares = 0.0

                            try:
                                price = float(price_str) if price_str else 0.0
                            except (ValueError, TypeError):
                                price = 0.0

                            total_usd = round(shares * price, 2) if (price > 0 and shares > 0) else 0.0
                            flag_10b51 = self._detect_10b51(tx, root, footnotes, doc_10b51)

                            all_trades.append({
                                "filer": owner_name,
                                "title": title,
                                "date": tx_date,
                                "code": code,
                                "shares": shares,
                                "price_per_share": price,
                                "total_usd": total_usd,
                                "is_10b51": flag_10b51,
                                "accession": acc
                            })
                        except Exception as tx_err:
                            logger.warning(f"Error procesando transacción individual en {acc}: {tx_err}")
                            continue

                except Exception as filing_err:
                    logger.warning(f"Error procesando XML de filing {acc}: {filing_err}")
                    continue

            # 3. Computar agregados consolidados
            total_bought_usd = sum(t["total_usd"] for t in all_trades if t["code"] == "P")
            total_sold_usd = sum(t["total_usd"] for t in all_trades if t["code"] == "S")
            discretionary_sold_usd = sum(t["total_usd"] for t in all_trades if t["code"] == "S" and t["is_10b51"] is not True)
            programmed_10b51_sold_usd = sum(t["total_usd"] for t in all_trades if t["code"] == "S" and t["is_10b51"] is True)
            net_discretionary_flow_usd = total_bought_usd - discretionary_sold_usd

            if discretionary_sold_usd > 5_000_000 and total_bought_usd == 0:
                insider_alignment = "BEARISH_DIVERGENCE"
            elif total_bought_usd > discretionary_sold_usd:
                insider_alignment = "BULLISH_ACCUMULATION"
            else:
                insider_alignment = "NEUTRAL"

            return {
                "status": "SUCCESS",
                "source": "SEC EDGAR Form 4 XML",
                "as_of": as_of,
                "ticker": ticker,
                "summary": {
                    "total_bought_usd": round(total_bought_usd, 2),
                    "total_sold_usd": round(total_sold_usd, 2),
                    "discretionary_sold_usd": round(discretionary_sold_usd, 2),
                    "programmed_10b51_sold_usd": round(programmed_10b51_sold_usd, 2),
                    "net_discretionary_flow_usd": round(net_discretionary_flow_usd, 2),
                    "insider_alignment": insider_alignment,
                    "filings_parsed": parsed_filings_count,
                    "transactions_found": len(all_trades)
                },
                "trades": all_trades,
                "count": len(all_trades)
            }

        except Exception as e:
            self._trip_circuit(f"Fallo general o timeout en SEC Form 4: {e}")
            return {
                "status": "UNAVAILABLE",
                "reason": str(e),
                "ticker": ticker
            }

    def get_latest_filing_summary(self, ticker: str) -> Dict[str, Any]:
        """
        Extrae metadatos del reporte anual (10-K) o trimestral (10-Q) más reciente.
        Protocolo Fail-Closed: devuelve status UNAVAILABLE si no es accesible.
        """
        ticker = ticker.upper().replace("$", "")
        cik = self._get_cik(ticker)
        if not cik:
            return {
                "status": "UNAVAILABLE",
                "reason": "CIK_NOT_FOUND",
                "ticker": ticker,
                "message": f"CIK no encontrado para {ticker}."
            }

        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        try:
            res = requests.get(url, headers=self.headers, timeout=6)
            if res.status_code == 429:
                self._trip_circuit("HTTP 429 en filing summary")
                return {
                    "status": "UNAVAILABLE",
                    "reason": "SEC_EDGAR_RATE_LIMIT",
                    "ticker": ticker,
                    "message": "Rate limit (HTTP 429) en SEC EDGAR."
                }
            elif res.status_code != 200:
                return {
                    "status": "UNAVAILABLE",
                    "reason": "CONNECTION_ERROR",
                    "ticker": ticker,
                    "message": f"SEC EDGAR devolvió código HTTP {res.status_code}."
                }

            data = res.json()
            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            
            for i, form in enumerate(forms):
                if form in ["10-K", "10-Q"]:
                    return {
                        "status": "SUCCESS",
                        "ticker": ticker,
                        "entity_name": data.get("name", ticker),
                        "latest_form": form,
                        "filing_date": dates[i] if i < len(dates) else "N/A",
                        "sic": data.get("sic", "N/A"),
                        "sic_description": data.get("sicDescription", "N/A")
                    }
            return {
                "status": "UNAVAILABLE",
                "reason": "CONNECTION_ERROR",
                "ticker": ticker,
                "message": "No se encontraron reportes 10-K o 10-Q recientes en el archivo oficial."
            }
        except Exception as e:
            return {
                "status": "UNAVAILABLE",
                "reason": "CONNECTION_ERROR",
                "ticker": ticker,
                "message": f"Error consultando filing summary: {str(e)}"
            }
