"""
PDF parsing module using Landing AI ADE unified schema for insurance quotations.
"""

import os
import json
from typing import Dict, Optional, List, Any, Iterable
import requests

def _first_amount(text: str) -> Optional[str]:
    """Return first currency-looking amount in text. Kept for compatibility."""
    import re
    m = re.search(r'\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)', text)
    return m.group(1) if m else None

def _to_number(amount: Optional[str]) -> Optional[float]:
    """Convert amount string like '1,234.56' or '$1,234.56' to float. Returns None if invalid."""
    if not amount:
        return None
    try:
        s = str(amount).strip().replace('$', '').replace(',', '').replace(' ', '')
        return float(s)
    except Exception:
        return None

def _format_currency(value: float) -> str:
    """Format float as currency string with thousands and two decimals (no symbol)."""
    try:
        return f"{value:,.2f}"
    except Exception:
        return str(value)

def _compute_financials(prima_neta_raw: Optional[str], prima_total_raw: Optional[str],
                        recargos_raw: Optional[str], derechos_raw: Optional[str],
                        recargos_cap: float = 2000.0, min_total_threshold: float = 1000.0) -> Dict[str, str]:
    """Standardized computation for Prima Neta, Recargos, Derechos, IVA and Prima Total.
    - Prefer provided Prima Neta if > threshold; fallback to Prima Total if > threshold.
    - Recargos above cap are treated as 0.
    - IVA = (neta + recargos + derechos) * 0.16
    - Prima Total = neta + recargos + derechos + IVA
    Returns formatted strings with '$'.
    """
    prima_neta_num = _to_number(prima_neta_raw)
    prima_total_num = _to_number(prima_total_raw)
    # Choose valid prima_neta
    chosen_neta = None
    if prima_neta_num is not None and prima_neta_num > min_total_threshold:
        chosen_neta = prima_neta_num
    elif prima_total_num is not None and prima_total_num > min_total_threshold:
        chosen_neta = prima_total_num
    else:
        chosen_neta = 0.0
    # Recargos
    rec_num = _to_number(recargos_raw) or 0.0
    if rec_num > recargos_cap:
        rec_num = 0.0
    # Derechos
    der_num = _to_number(derechos_raw) or 0.0
    # IVA and total
    iva_num = (chosen_neta + rec_num + der_num) * 0.16
    total_num = chosen_neta + rec_num + der_num + iva_num
    result = {
        'Prima Neta': f"${_format_currency(chosen_neta)}" if chosen_neta > 0 else 'N/A',
        'Recargos': f"${_format_currency(rec_num)}" if rec_num > 0 else '$ 0',
        'Derechos de Póliza': f"${_format_currency(der_num)}" if der_num > 0 else 'N/A',
        'IVA': f"${_format_currency(iva_num)}",
        'Prima Total': f"${_format_currency(total_num)}" if total_num > 0 else 'N/A',
    }
    return result


def parse_pdf(pdf_content: bytes) -> Optional[Dict[str, str]]:
    """
    Main function to parse PDF content using Landing AI ADE unified schema.
    
    Args:
        pdf_content: Raw PDF file content as bytes
        
    Returns:
        Dictionary with extracted insurance data or None if parsing fails
    """
    try:
        ade_data = _ade_extract_unified(pdf_content)
        if not ade_data:
            return None
        return _map_ade_to_result(ade_data)
    except Exception as e:
        print(f"Error parsing PDF: {str(e)}")
        return None


def parse_pdfs(pdf_contents: Iterable[bytes]) -> List[Optional[Dict[str, str]]]:
    """Batch parse helper using ADE; sequential calls for 1-2 page PDFs."""
    results: List[Optional[Dict[str, str]]] = []
    for content in pdf_contents:
        results.append(parse_pdf(content))
    return results


def _ade_extract_unified(pdf_content: bytes) -> Optional[Dict[str, Any]]:
    """Call Landing AI ADE extraction with a unified schema and return JSON dict.

    Expected environment variables:
    - LANDING_AI_API_KEY: VA API key (Basic auth)
    - LANDING_AI_ADE_URL: Full endpoint URL (defaults to Landing AI ADE endpoint)
      Default: https://api.va.landing.ai/v1/tools/agentic-document-analysis
    The extraction schema is always loaded from a local 'schema.json'.
    """
    api_key = os.environ.get("LANDING_AI_API_KEY")
    endpoint = os.environ.get("LANDING_AI_ADE_URL") or "https://api.va.landing.ai/v1/tools/agentic-document-analysis"

    if not api_key:
        raise RuntimeError("Missing LANDING_AI_API_KEY in environment")
    # Always load schema from local schema.json (project root)
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.json')
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema: Dict[str, Any] = json.load(f)
    except Exception as exc:
        raise RuntimeError(f"Failed to read schema.json: {exc}")

    headers = {"Authorization": f"Basic {api_key}"}

    # ADE expects either 'document' (file upload) or 'document_url'. Use file upload.
    files = {"document": ("document.pdf", pdf_content, "application/pdf")}
    data = {"fields_schema": json.dumps(schema)}

    resp = requests.post(endpoint, headers=headers, files=files, data=data, timeout=60)
    if resp.status_code >= 400:
        raise RuntimeError(f"ADE request failed: {resp.status_code} {resp.text[:240]}")
    try:
        return resp.json()
    except Exception:
        # Attempt to parse text to JSON if response is stringified
        try:
            return json.loads(resp.text)
        except Exception as exc:
            raise RuntimeError(f"Invalid ADE JSON response: {exc}")


def _map_ade_to_result(ade: Dict[str, Any]) -> Dict[str, str]:
    """Map ADE unified response to app's expected keys and compute financials."""
    # ADE API shape: { data: { extracted_schema: {...} } }
    container = ade.get("data") or ade
    if isinstance(container, dict) and "extracted_schema" in container:
        fields = container.get("extracted_schema") or {}
    else:
        # Fallbacks for other shapes
        fields = ade.get("fields") or container or ade

    def get_field(*names: str) -> Optional[str]:
        for n in names:
            if n in fields and fields[n] not in (None, ""):
                v = fields[n]
                if isinstance(v, dict) and "value" in v:
                    return str(v.get("value") or "").strip()
                return str(v).strip()
        return None

    # Company (optional in schema) and vehicle
    company = get_field("company", "insurer", "aseguradora") or "N/A"
    vehicle_name = ""
    # Nested location: vehicle_info.vehiculo
    if isinstance(fields, dict):
        try:
            vehicle_name = (
                (fields.get("vehicle_info") or {}).get("vehiculo")
                or get_field("vehicle_name", "vehiculo", "descripcion_vehiculo")
                or ""
            )
        except Exception:
            vehicle_name = get_field("vehicle_name", "vehiculo", "descripcion_vehiculo") or ""

    # Raw financials
    # Nested summary.* per provided schema
    prima_total_raw = None
    prima_neta_raw = None
    recargos_raw = None
    derechos_raw = None
    if isinstance(fields, dict) and isinstance(fields.get("summary"), dict):
        summary = fields.get("summary") or {}
        prima_total_raw = summary.get("prima_total")
        prima_neta_raw = summary.get("prima_neta")
        recargos_raw = summary.get("recargos")
        derechos_raw = summary.get("derechos")
    # Fallbacks
    prima_total_raw = prima_total_raw or get_field("prima_total", "primaTotal", "IMPORTE TOTAL", "PRIMA TOTAL")
    prima_neta_raw = prima_neta_raw or get_field("prima_neta", "primaNeta", "PRIMA NETA")
    recargos_raw = recargos_raw or get_field("recargos")
    derechos_raw = derechos_raw or get_field("derechos_poliza", "derechos_de_poliza", "derechos")

    fin = _compute_financials(prima_neta_raw, prima_total_raw, recargos_raw, derechos_raw)

    # Coverages: map from coverages[] list when available; fallback to flat keys
    danos_materiales = "N/A"
    robo_total = "N/A"
    responsabilidad_civil = "N/A"
    gmo = "N/A"
    asistencia_legal = get_field("asistencia_legal", "gastos_legales", "asistencia_juridica") or "N/A"
    asistencia_viajes = get_field("asistencia_viajes", "asistencia_vial", "asistencia_en_viajes") or "N/A"
    acc_conductor = get_field("accidente_conductor", "accidente_al_conductor", "muerte_conductor")
    acc_conductor = f"${acc_conductor}" if acc_conductor else "N/A"
    rc_cat = get_field("rc_catastrofica", "rc_complementaria_personas", "rc_cat_monto")
    rc_cat = f"${rc_cat}" if rc_cat else "N/A"
    desb_agua = get_field("desbielamiento_agua_motor", "desbielamiento_por_agua") or "N/A"

    coverages = []
    if isinstance(fields, dict):
        coverages = fields.get("coverages") or []
    # Helper to find coverage by name
    def cov_by_name(names: List[str]) -> Optional[Dict[str, Any]]:
        if not isinstance(coverages, list):
            return None
        for c in coverages:
            try:
                n = str(c.get("nombre") or "").strip().upper()
                for target in names:
                    if target in n:
                        return c
            except Exception:
                continue
        return None

    dm_cov = cov_by_name(["DAÑOS MATERIALES", "DANOS MATERIALES"]) or {}
    if dm_cov:
        monto = dm_cov.get("suma_asegurada")
        ded = dm_cov.get("porcentaje_deducible")
        if monto and ded not in (None, ""):
            danos_materiales = f"${monto} Deducible {ded}%"
        elif monto:
            danos_materiales = f"${monto}"

    rt_cov = cov_by_name(["ROBO TOTAL"]) or {}
    if rt_cov:
        monto = rt_cov.get("suma_asegurada")
        ded = rt_cov.get("porcentaje_deducible")
        if monto and ded not in (None, ""):
            robo_total = f"${monto} Deducible {ded}%"
        elif monto:
            robo_total = f"${monto}"

    rc_cov = cov_by_name(["RESPONSABILIDAD CIVIL"]) or {}
    if rc_cov:
        monto = rc_cov.get("suma_asegurada")
        if monto:
            responsabilidad_civil = f"${monto}"

    gmo_cov = cov_by_name(["GASTOS MEDICOS", "GASTOS MÉDICOS"]) or {}
    if gmo_cov:
        monto = gmo_cov.get("suma_asegurada")
        if monto:
            gmo = f"${monto}"

    forma_pago = get_field("forma_de_pago", "forma_pago") or "CONTADO"

    result: Dict[str, str] = {
        "company": company,
        "vehicle_name": vehicle_name,
        **fin,
        "Forma de Pago": forma_pago,
        "Daños Materiales": danos_materiales,
        "Robo Total": robo_total,
        "Responsabilidad Civil": responsabilidad_civil,
        "Gastos Medicos Ocupantes": gmo,
        "Asistencia Legal": asistencia_legal,
        "Asistencia Viajes": asistencia_viajes,
        "Accidente al conductor": acc_conductor,
        "Responsabilidad civil catastrofica": rc_cat,
        "Desbielamiento por agua al motor": desb_agua,
    }
    return result

    # Legacy company-specific parsing removed in favor of ADE unified schema
