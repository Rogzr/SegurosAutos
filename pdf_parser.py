"""
PDF parsing module for insurance quotation documents.
Handles parsing of PDFs from four specific insurance companies:
- HDI Seguros
- Qualitas
- ANA Seguros
- Seguros Atlas
"""

import fitz  # PyMuPDF
import re
from typing import Dict, Optional, List

def load_brands() -> List[str]:
    """Load brands from brands.json. Returns empty list if not present."""
    import json
    import os
    try:
        path = os.path.join(os.path.dirname(__file__), 'brands.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list) and data:
                return [str(x).upper() for x in data]
    except Exception:
        pass
    return []

BRANDS = load_brands()

def extract_vehicle(text: str) -> str:
    """Best-effort vehicle descriptor extraction from PDF text."""
    upper = text.upper().replace('\n', ' ')
    patterns: List[str] = []
    if BRANDS:
        brands_pattern = r'(?:' + '|'.join([b.replace('-', r'\-') for b in BRANDS]) + r')'
        patterns.append(rf'{brands_pattern}\s+[A-Z0-9][A-Z0-9\- ]{{2,60}}')
    # Generic fallbacks that don't depend on brand list
    patterns.append(r'DESCRIPCION DEL VEHICULO ASEGURADO\s+([A-Z0-9 ,\-]+)')
    patterns.append(r'VEH[ÍI]CULO\s*[:]*\s*([A-Z0-9 ,\-]{3,60})')
    candidate = ''
    import re
    for p in patterns:
        m = re.search(p, upper)
        if m:
            candidate = m.group(0) if m.lastindex is None else m.group(1)
            break
    if not candidate:
        return ''
    # Normalize
    candidate = candidate.strip()
    # If starts with VW, expand to VOLKSWAGEN
    if candidate.startswith('VW '):
        candidate = candidate.replace('VW ', 'VOLKSWAGEN ', 1)
    # Remove noisy tokens
    noise_tokens = [
        'AUTOMOVILES NACIONALES', 'AUTOMOVILES', 'PARTICULAR', 'NORMAL', 'SERVICIO',
        'DESCRIPCION DEL VEHICULO ASEGURADO', 'DESC', 'AMPLIA', 'PLAN', 'USO',
        'L4', 'TSI', 'ABS', 'BA', 'AC', 'AUT', 'AUTO', '5 OCUP', '5P', '5PTAS',
        '1.4T', '2.0T', 'CVT', 'TIPTRONIC', 'AT', 'MT','SUMA ASEGURADA', 'SUM', 'RIESGOS'
    ]
    for t in noise_tokens:
        candidate = candidate.replace(' ' + t + ' ', ' ')
        if candidate.endswith(' ' + t):
            candidate = candidate[:-(len(t)+1)]
    # Collapse whitespace
    candidate = ' '.join(candidate.split())
    return candidate

def _extract_amount_after(text: str, anchors: List[str], lookahead_chars: int = 250) -> Optional[str]:
    """Find first currency-like amount immediately after any of the anchor patterns.
    Returns amount string with thousands and decimals, without leading $.
    """
    import re
    upper = text.upper()
    for a in anchors:
        try:
            m = re.search(a.upper(), upper)
            if not m:
                continue
            start = m.end()
            window = upper[start:start + lookahead_chars]
            # Match $ 616,000.00 or 616,000.00 etc.
            m2 = re.search(r'\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)', window)
            if m2:
                return m2.group(1)
        except Exception:
            continue
    return None

def _first_amount(text: str) -> Optional[str]:
    """Return first currency-looking amount in text."""
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
    Main function to parse PDF content and extract insurance data.
    
    Args:
        pdf_content: Raw PDF file content as bytes
        
    Returns:
        Dictionary with extracted insurance data or None if parsing fails
    """
    try:
        # Open PDF from bytes
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
        # Extract text from all pages
        full_text = ""
        for page_num in range(len(doc)):
            page = doc[page_num]
            full_text += page.get_text()
        
        doc.close()
        
        # Identify company and parse accordingly
        company = identify_company(full_text)
        
        if not company:
            return None
        
        # Parse based on company type
        if company == "HDI":
            return parse_hdi(full_text)
        elif company == "Qualitas":
            return parse_qualitas(full_text)
        elif company == "ANA":
            return parse_ana(full_text)
        elif company == "Atlas":
            return parse_atlas(full_text)
        
        return None
        
    except Exception as e:
        print(f"Error parsing PDF: {str(e)}")
        return None

def identify_company(text: str) -> Optional[str]:
    """
    Identify the insurance company from PDF text.
    
    Args:
        text: Full text content of the PDF
        
    Returns:
        Company identifier or None if not recognized
    """
    text_upper = text.upper()
    
    # Check for Atlas - look for "ATLAS" in the text
    if "ATLAS" in text_upper and "SEGUROS ATLAS" not in text_upper:
        return "Atlas"
    # Check for ANA - look for "ANA" but not in other company contexts
    elif "ANA" in text_upper and "HDI" not in text_upper and "ATLAS" not in text_upper and "QUALITAS" not in text_upper:
        return "ANA"
    # Check for HDI
    elif "HDI SEGUROS" in text_upper or "HDI" in text_upper:
        return "HDI"
    # Check for Qualitas
    elif "QUÁLITAS" in text_upper or "QUALITAS" in text_upper:
        return "Qualitas"
    
    return None

def parse_hdi(text: str) -> Dict[str, str]:
    """
    Parse HDI Seguros PDF format.
    
    Args:
        text: Full text content of the PDF
        
    Returns:
        Dictionary with extracted insurance data
    """
    result = {"company": "HDI Seguros"}
    result["vehicle_name"] = extract_vehicle(text)
    
    # Totals (standardized)
    prima_total = _extract_amount_after(text, ['Total a Pagar', 'IMPORTE TOTAL', 'TOTAL A PAGAR', 'Prima Total', 'PRIMA TOTAL'])
    prima_neta = _extract_amount_after(text, ['PRIMA NETA','Prima Neta'])
    recargos = _extract_amount_after(text, ['Recargos'])
    derechos = _extract_amount_after(text, ['Derechos de Póliza','Derechos de Poliza','Derechos'])
    fin = _compute_financials(prima_neta, prima_total, recargos, derechos)
    result.update(fin)
    
    # Forma de Pago: Standardize to "CONTADO"
    result["Forma de Pago"] = "CONTADO"
    
    # Daños Materiales amount (limit)
    dm_amount = _extract_amount_after(text, [
        'Daños Materiales', 'DAÑOS MATERIALES'
    ])
    if dm_amount:
        result["Daños Materiales"] = f"${dm_amount}"
    else:
        result["Daños Materiales"] = "N/A"
    
    # Robo Total amount and deductible
    rt_amount = _extract_amount_after(text, ['Robo Total', 'ROBO TOTAL','Limite de Responsabilidad'])
    if rt_amount:
        result["Robo Total"] = f"${rt_amount}"
    else:
        result["Robo Total"] = "N/A"
    
    
    # Responsabilidad Civil
    rc_match = re.search(r'Responsabilidad Civil (Límite Único y Combinado)[:\s]*([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Responsabilidad Civil"] = f"${rc_match.group(1)}" if rc_match else "N/A"
    
    # Gastos Medicos Ocupantes
    gmo_match = re.search(r'Gastos Médicos Ocupantes  (Límite Único Combinado)[:\s]*([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Gastos Medicos Ocupantes"] = f"${gmo_match.group(1)}" if gmo_match else "N/A"
    
    # Asistencia Legal
    al_match = re.search(r'Asistencia Jurídica[:\s]*(Amparada|No Amparada)', text, re.IGNORECASE)
    result["Asistencia Legal"] = f"{al_match.group(1)}" if al_match else "N/A"
    
    # ASistencia Viajes
    av_match = re.search(r'Asistencia en viajes[:\s]*(Amparada|No Amparada)', text, re.IGNORECASE)
    result["Asistencia Viajes"] = f"{av_match.group(1)}" if av_match else "N/A"
    
    # Accidente al conductor
    ac_match = re.search(r'Accidentes Automovilísticos al Conductor[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Accidente al conductor"] = f"${ac_match.group(1)}" if ac_match else "N/A"
    
    # Responsabilidad civil catastrofica
    rcc_match = re.search(r'Responsabilidad Civil en Exceso por Muerte de Personas[:\s]*([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Responsabilidad civil catastrofica"] = rcc_match.group(1) if rcc_match else "N/A"
    # Desbielamiento por agua al motor: Not present in HDI
    result["Desbielamiento por agua al motor"] = "N/A"
    
    return result

def parse_qualitas(text: str) -> Dict[str, str]:
    """
    Parse Qualitas PDF format.

    Args:
        text: Full text content of the PDF

    Returns:
        Dictionary with extracted insurance data
    """
    result = {"company": "Qualitas"}
    result["vehicle_name"] = extract_vehicle(text)

    # Totals (standardized)
    prima_total = _extract_amount_after(text, ['IMPORTE TOTAL', 'PRIMA TOTAL'])
    prima_neta = _extract_amount_after(text, ['PRIMA NETA', 'Prima Neta'])
    recargos = _extract_amount_after(text, ['Recargos'])
    derechos = _extract_amount_after(text, ['Derechos de Póliza', 'Derechos de Poliza'])
    fin = _compute_financials(prima_neta, prima_total, recargos, derechos)
    result.update(fin)

    # Forma de Pago
    result["Forma de Pago"] = "CONTADO"

    dm_amount = _extract_amount_after(text, ['Daños materiales', 'DAÑOS MATERIALES', 'SUMA ASEGURADA'])
    if dm_amount:
        result["Daños Materiales"] = f"${dm_amount}"
    else:
        result["Daños Materiales"] = "N/A"

    rt_amount = _extract_amount_after(text, ['Robo total', 'ROBO TOTAL', 'SUMA ASEGURADA'])
    if rt_amount:
        result["Robo Total"] = f"${rt_amount}"
    else:
        result["Robo Total"] = "N/A"

    # Responsabilidad Civil
    rc_match = re.search(r'Responsabilidad Civil[:\s]*\$?\s*([0-9,]+\.?\d*)', text, re.IGNORECASE)
    if not rc_match:
        # Try to match pattern like "Responsabilidad Civil $ 2,000,000.00 POR EVENTO"
        rc_match = re.search(r'Responsabilidad Civil[^\d$]*\$?\s*([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Responsabilidad Civil"] = f"${rc_match.group(1)}" if rc_match else "N/A"

    # Gastos Medicos Ocupantes
    gmo_match = re.search(r'Gastos Medicos Ocupantes[:\s]*\$?\s*([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Gastos Medicos Ocupantes"] = f"${gmo_match.group(1)}" if gmo_match else "N/A"

    # Asistencia Legal
    al_match = re.search(r'Gastos Legales[:\s]*(Amparada|No Amparada)', text, re.IGNORECASE)
    result["Asistencia Legal"] = f"{al_match.group(1)}" if al_match else "N/A"

    # Asistencia Viajes
    av_match = re.search(r'Asistencia Vial[:\s]*(Amparada|No Amparada)', text, re.IGNORECASE)
    result["Asistencia Viajes"] = f"{av_match.group(1)}" if av_match else "N/A"

    # Accidente al conductor
    ac_match = re.search(r'Muerte del Conductor X AA[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Accidente al conductor"] = f"${ac_match.group(1)}" if ac_match else "N/A"

    # Responsabilidad civil catastrofica
    # Match "RC Complementaria Personas" followed by any non-digit, then a $ and the first amount (e.g. $ 2,000,000.00)
    rcc_match = re.search(r'RC Complementaria Personas[^\d$]*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.\d{2})?)', text, re.IGNORECASE)
    result["Responsabilidad civil catastrofica"] = f"${rcc_match.group(1)}" if rcc_match else "N/A"

    # Desbielamiento por agua al motor: Not present in Qualitas
    result["Desbielamiento por agua al motor"] = "N/A"

    return result

def parse_ana(text: str) -> Dict[str, str]:
    """
    Parse ANA Seguros PDF format.
    
    Args:
        text: Full text content of the PDF
        
    Returns:
        Dictionary with extracted insurance data
    """
    result = {"company": "ANA Seguros"}
    result["vehicle_name"] = extract_vehicle(text)
    
    # Totals (standardized)
    prima_total = _extract_amount_after(text, ['PRIMA TOTAL', 'TOTAL'])
    prima_neta = _extract_amount_after(text, ['PRIMA NETA','Prima Neta'])
    recargos = _extract_amount_after(text, ['Recargos'])
    derechos = _extract_amount_after(text, ['Derechos de Póliza','Derechos de Poliza'])
    fin = _compute_financials(prima_neta, prima_total, recargos, derechos)
    result.update(fin)
    
    # Forma de Pago
    fp_match = re.search(r'FORMA DE PAGO[:\s]*([A-Z\s]+)', text, re.IGNORECASE)
    result["Forma de Pago"] = fp_match.group(1).strip() if fp_match else "N/A"
    
    dm_amount = _extract_amount_after(text, ['DAÑOS MATERIALES', 'SUMA ASEGURADA'])
    if dm_amount:
        result["Daños Materiales"] = f"${dm_amount}"
    else:
        result["Daños Materiales"] = "N/A"
    
    rt_amount = _extract_amount_after(text, ['ROBO TOTAL', 'SUMA ASEGURADA'])
    if rt_amount:
        result["Robo Total"] = f"${rt_amount}"
    else:
        result["Robo Total"] = "N/A"
    
    # Responsabilidad Civil
    rc_match = re.search(r'RESPONSABILIDAD CIVIL[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Responsabilidad Civil"] = f"${rc_match.group(1)}" if rc_match else "N/A"
    
    # Gastos Medicos Ocupantes
    gmo_match = re.search(r'GASTOS MEDICOS OCUPANTES[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Gastos Medicos Ocupantes"] = f"${gmo_match.group(1)}" if gmo_match else "N/A"
    
    # Asistencia Legal
    al_match = re.search(r'DEFENSA JURIDICA Y ASIST\. LEGAL[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Asistencia Legal"] = f"${al_match.group(1)}" if al_match else "N/A"
    
    # Asistencia Viajes: Derived from "ANA ASISTENCIA"
    result["Asistencia Viajes"] = "AMPARADA"
    
    # Accidente al conductor
    ac_match = re.search(r'GASTOS POR MUERTE ACCIDENTAL[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Accidente al conductor"] = f"${ac_match.group(1)}" if ac_match else "N/A"
    
    # Responsabilidad civil catastrofica
    rcc_match = re.search(r'RC CATASTROFICA POR MUERTE[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Responsabilidad civil catastrofica"] = f"${rcc_match.group(1)}" if rcc_match else "N/A"
    
    # Desbielamiento por agua al motor
    dam_match = re.search(r'DESBIELAMIENTO POR AGUA[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Desbielamiento por agua al motor"] = f"${dam_match.group(1)}" if dam_match else "N/A"
    
    return result

def parse_atlas(text: str) -> Dict[str, str]:
    """
    Parse Seguros Atlas PDF format.
    
    Args:
        text: Full text content of the PDF
        
    Returns:
        Dictionary with extracted insurance data
    """
    result = {"company": "Seguros Atlas"}
    result["vehicle_name"] = extract_vehicle(text)
    
    # Totals (standardized)
    prima_total = _extract_amount_after(text, ['PRIMA TOTAL', 'TOTAL'])
    prima_neta = _extract_amount_after(text, ['PRIMA NETA','Prima Neta'])
    recargos = _extract_amount_after(text, ['Recargos'])
    derechos = _extract_amount_after(text, ['Derechos de Póliza','Derechos de Poliza'])
    fin = _compute_financials(prima_neta, prima_total, recargos, derechos)
    result.update(fin)
    
    # Forma de Pago (fallback to CONTADO if not found)
    fp_match = re.search(r'FORMA DE PAGO[:\s]*([A-Z\s]+)', text, re.IGNORECASE)
    result["Forma de Pago"] = fp_match.group(1).strip() if fp_match else "CONTADO"
    
    dm_amount = _extract_amount_after(text, ['DAÑOS MATERIALES', 'Suma Asegurada', 'SUMA ASEGURADA'])
    if dm_amount:
        result["Daños Materiales"] = f"${dm_amount}"
    else:
        result["Daños Materiales"] = "N/A"
    
    rt_amount = _extract_amount_after(text, ['ROBO TOTAL', 'Suma Asegurada', 'SUMA ASEGURADA'])
    if rt_amount:
        result["Robo Total"] = f"${rt_amount}"
    else:
        result["Robo Total"] = "N/A"
    
    # Responsabilidad Civil
    rc_match = re.search(r'RESPONSABILIDAD CIVIL\s*(?:\(LUC\))?[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Responsabilidad Civil"] = f"${rc_match.group(1)}" if rc_match else "N/A"
    
    # Gastos Medicos Ocupantes
    gmo_match = re.search(r'GASTOS MEDICOS OCUPANTES\s*(?:\(LUC\))?[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Gastos Medicos Ocupantes"] = f"${gmo_match.group(1)}" if gmo_match else "N/A"
    
    # Asistencia Legal
    al_match = re.search(r'ASISTENCIA LEGAL[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Asistencia Legal"] = f"${al_match.group(1)}" if al_match else "N/A"
    
    # Asistencia Viajes
    # av_match = re.search(r'ASISTENCIA EN VIAJES[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    #result["Asistencia Viajes"] = f"${av_match.group(1)}" if av_match else "N/A"
    result["Asistencia Viajes"] = "AMPARADA"

    # Accidente al conductor
    ac_match = re.search(r'ACCIDENTE AL CONDUCTOR[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Accidente al conductor"] = f"${ac_match.group(1)}" if ac_match else "N/A"
    
    # Responsabilidad civil catastrofica
    rcc_match = re.search(r'RESPONSABILIDAD CIVIL CATASTRÓFICA POR FALLECIMIENTO[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Responsabilidad civil catastrofica"] = f"${rcc_match.group(1)}" if rcc_match else "N/A"
    
    # Desbielamiento por agua al motor: Not present in Atlas
    result["Desbielamiento por agua al motor"] = "N/A"
    
    return result
