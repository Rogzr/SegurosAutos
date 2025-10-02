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
    
    # Prima: Find "Total a Pagar" or "Prima Neta"
    prima_match = re.search(r'Total a Pagar[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    if not prima_match:
        # Try "Prima Neta" pattern
        prima_match = re.search(r'Prima Neta[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    if not prima_match:
        # Try general "Prima" pattern
        prima_match = re.search(r'Prima[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Prima"] = f"${prima_match.group(1)}" if prima_match else "N/A"
    
    # Forma de Pago: Standardize to "CONTADO"
    result["Forma de Pago"] = "CONTADO"
    
    # Daños Materiales: Combine Límite and Deducible
    danos_match = re.search(r'Daños Materiales.*?Límite de Responsabilidad[:\s]*\$?([0-9,]+\.?\d*).*?Deducible[:\s]*([0-9]+\.?\d*)%', text, re.IGNORECASE | re.DOTALL)
    if danos_match:
        result["Daños Materiales"] = f"${danos_match.group(1)} Deducible {danos_match.group(2)}%"
    else:
        result["Daños Materiales"] = "N/A"
    
    # Robo Total: Combine Límite and Deducible
    robo_match = re.search(r'Robo Total.*?Límite de Responsabilidad[:\s]*\$?([0-9,]+\.?\d*).*?Deducible[:\s]*([0-9]+\.?\d*)%', text, re.IGNORECASE | re.DOTALL)
    if robo_match:
        result["Robo Total"] = f"${robo_match.group(1)} Deducible {robo_match.group(2)}%"
    else:
        result["Robo Total"] = "N/A"
    
    # Responsabilidad Civil
    rc_match = re.search(r'Responsabilidad Civil \(Límite Único y Combinado\)[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Responsabilidad Civil"] = f"${rc_match.group(1)}" if rc_match else "N/A"
    
    # Gastos Medicos Ocupantes
    gmo_match = re.search(r'Gastos Médicos Ocupantes[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Gastos Medicos Ocupantes"] = f"${gmo_match.group(1)}" if gmo_match else "N/A"
    
    # Asistencia Legal
    al_match = re.search(r'Asistencia Jurídica[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Asistencia Legal"] = f"${al_match.group(1)}" if al_match else "N/A"
    
    # Asistencia Viajes
    av_match = re.search(r'Asistencia en viajes[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Asistencia Viajes"] = f"${av_match.group(1)}" if av_match else "N/A"
    
    # Accidente al conductor
    ac_match = re.search(r'Accidentes Automovilísticos al Conductor[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Accidente al conductor"] = f"${ac_match.group(1)}" if ac_match else "N/A"
    
    # Responsabilidad civil catastrofica
    rcc_match = re.search(r'Responsabilidad Civil en Exceso por Muerte de Personas[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Responsabilidad civil catastrofica"] = f"${rcc_match.group(1)}" if rcc_match else "N/A"
    
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
    
    # Prima: Find "IMPORTE TOTAL"
    prima_match = re.search(r'IMPORTE TOTAL[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Prima"] = f"${prima_match.group(1)}" if prima_match else "N/A"
    
    # Forma de Pago
    result["Forma de Pago"] = "CONTADO"
    
    # Daños Materiales: Combine SUMA ASEGURADA and DEDUCIBLE
    danos_match = re.search(r'Daños materiales.*?SUMA ASEGURADA[:\s]*\$?([0-9,]+\.?\d*).*?DEDUCIBLE[:\s]*([0-9]+\.?\d*)%', text, re.IGNORECASE | re.DOTALL)
    if danos_match:
        result["Daños Materiales"] = f"${danos_match.group(1)} Deducible {danos_match.group(2)}%"
    else:
        result["Daños Materiales"] = "N/A"
    
    # Robo Total: Combine SUMA ASEGURADA and DEDUCIBLE
    robo_match = re.search(r'Robo total.*?SUMA ASEGURADA[:\s]*\$?([0-9,]+\.?\d*).*?DEDUCIBLE[:\s]*([0-9]+\.?\d*)%', text, re.IGNORECASE | re.DOTALL)
    if robo_match:
        result["Robo Total"] = f"${robo_match.group(1)} Deducible {robo_match.group(2)}%"
    else:
        result["Robo Total"] = "N/A"
    
    # Responsabilidad Civil
    rc_match = re.search(r'Responsabilidad Civil[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Responsabilidad Civil"] = f"${rc_match.group(1)}" if rc_match else "N/A"
    
    # Gastos Medicos Ocupantes
    gmo_match = re.search(r'Gastos Medicos Ocupantes[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Gastos Medicos Ocupantes"] = f"${gmo_match.group(1)}" if gmo_match else "N/A"
    
    # Asistencia Legal
    al_match = re.search(r'Gastos Legales[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Asistencia Legal"] = f"${al_match.group(1)}" if al_match else "N/A"
    
    # Asistencia Viajes
    av_match = re.search(r'Asistencia Vial[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Asistencia Viajes"] = f"${av_match.group(1)}" if av_match else "N/A"
    
    # Accidente al conductor
    ac_match = re.search(r'Muerte del Conductor X AA[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Accidente al conductor"] = f"${ac_match.group(1)}" if ac_match else "N/A"
    
    # Responsabilidad civil catastrofica
    rcc_match = re.search(r'RC Complementaria Personas[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
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
    
    # Prima: Find "PRIMA TOTAL" or look for total amount
    prima_match = re.search(r'PRIMA TOTAL[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    if not prima_match:
        # Look for the total amount at the end
        prima_match = re.search(r'TOTAL[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Prima"] = f"${prima_match.group(1)}" if prima_match else "N/A"
    
    # Forma de Pago
    fp_match = re.search(r'FORMA DE PAGO[:\s]*([A-Z\s]+)', text, re.IGNORECASE)
    result["Forma de Pago"] = fp_match.group(1).strip() if fp_match else "N/A"
    
    # Daños Materiales: Combine SUMA ASEGURADA and DEDUCIBLE
    danos_match = re.search(r'DAÑOS MATERIALES.*?SUMA ASEGURADA[:\s]*\$?([0-9,]+\.?\d*).*?DEDUCIBLE[:\s]*([0-9]+\.?\d*)%', text, re.IGNORECASE | re.DOTALL)
    if danos_match:
        result["Daños Materiales"] = f"${danos_match.group(1)} Deducible {danos_match.group(2)}%"
    else:
        result["Daños Materiales"] = "N/A"
    
    # Robo Total: Combine SUMA ASEGURADA and DEDUCIBLE
    robo_match = re.search(r'ROBO TOTAL.*?SUMA ASEGURADA[:\s]*\$?([0-9,]+\.?\d*).*?DEDUCIBLE[:\s]*([0-9]+\.?\d*)%', text, re.IGNORECASE | re.DOTALL)
    if robo_match:
        result["Robo Total"] = f"${robo_match.group(1)} Deducible {robo_match.group(2)}%"
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
    
    # Prima: Find in "Prima Total" column of summary table
    prima_match = re.search(r'Prima Total[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    if not prima_match:
        # Look for the total amount pattern
        prima_match = re.search(r'TOTAL[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Prima"] = f"${prima_match.group(1)}" if prima_match else "N/A"
    
    # Forma de Pago
    result["Forma de Pago"] = "CONTADO"
    
    # Daños Materiales: Combine Suma Asegurada and % Deducible
    danos_match = re.search(r'DAÑOS MATERIALES.*?Suma Asegurada[:\s]*\$?([0-9,]+\.?\d*).*?% Deducible[:\s]*([0-9]+\.?\d*)%', text, re.IGNORECASE | re.DOTALL)
    if danos_match:
        result["Daños Materiales"] = f"${danos_match.group(1)} Deducible {danos_match.group(2)}%"
    else:
        result["Daños Materiales"] = "N/A"
    
    # Robo Total: Combine Suma Asegurada and % Deducible
    robo_match = re.search(r'ROBO TOTAL.*?Suma Asegurada[:\s]*\$?([0-9,]+\.?\d*).*?% Deducible[:\s]*([0-9]+\.?\d*)%', text, re.IGNORECASE | re.DOTALL)
    if robo_match:
        result["Robo Total"] = f"${robo_match.group(1)} Deducible {robo_match.group(2)}%"
    else:
        result["Robo Total"] = "N/A"
    
    # Responsabilidad Civil
    rc_match = re.search(r'RESPONSABILIDAD CIVIL \(LUC\)[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Responsabilidad Civil"] = f"${rc_match.group(1)}" if rc_match else "N/A"
    
    # Gastos Medicos Ocupantes
    gmo_match = re.search(r'GASTOS MEDICOS OCUPANTES \(LUC\)[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Gastos Medicos Ocupantes"] = f"${gmo_match.group(1)}" if gmo_match else "N/A"
    
    # Asistencia Legal
    al_match = re.search(r'ASISTENCIA LEGAL[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Asistencia Legal"] = f"${al_match.group(1)}" if al_match else "N/A"
    
    # Asistencia Viajes
    av_match = re.search(r'ASISTENCIA EN VIAJES[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Asistencia Viajes"] = f"${av_match.group(1)}" if av_match else "N/A"
    
    # Accidente al conductor
    ac_match = re.search(r'ACCIDENTE AL CONDUCTOR[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Accidente al conductor"] = f"${ac_match.group(1)}" if ac_match else "N/A"
    
    # Responsabilidad civil catastrofica
    rcc_match = re.search(r'RESPONSABILIDAD CIVIL CATASTROFICA POR FALLECIMIENTO[:\s]*\$?([0-9,]+\.?\d*)', text, re.IGNORECASE)
    result["Responsabilidad civil catastrofica"] = f"${rcc_match.group(1)}" if rcc_match else "N/A"
    
    # Desbielamiento por agua al motor: Not present in Atlas
    result["Desbielamiento por agua al motor"] = "N/A"
    
    return result
