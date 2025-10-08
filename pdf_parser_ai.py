"""
PDF parsing module using Landing AI's Agentic Document Extraction.
Handles parsing of PDFs from four specific insurance companies:
- HDI Seguros
- Qualitas
- ANA Seguros
- Seguros Atlas

OPTIMIZED VERSION: Uses FREE regex for company ID, then single targeted API call
"""

import os
import json
import requests
import fitz  # PyMuPDF
from typing import Dict, Optional

# Import the free regex-based company identifier from the original parser
from pdf_parser import identify_company

# Get API key from environment
LANDING_AI_API_KEY = os.getenv('LANDING_AI_API_KEY')
LANDING_AI_ENDPOINT = os.getenv('LANDING_AI_ENDPOINT', 'https://api.va.landing.ai/v1/tools/agentic-document-analysis')


def parse_pdf_ai(pdf_content: bytes, filename: str = "document.pdf") -> Optional[Dict[str, str]]:
    """
    Main function to parse PDF content using Landing AI and extract insurance data.
    SUPER OPTIMIZED: Uses FREE regex for company ID, then 1 targeted API call.
    
    Args:
        pdf_content: Raw PDF file content as bytes
        filename: Name of the PDF file (for API upload)
        
    Returns:
        Dictionary with extracted insurance data or None if parsing fails
    """
    if not LANDING_AI_API_KEY:
        print("Error: LANDING_AI_API_KEY not found in environment variables")
        return None
    
    try:
        # Step 1: Use FREE regex-based company identification (instant, no credits!)
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        full_text = ""
        for page_num in range(len(doc)):
            page = doc[page_num]
            full_text += page.get_text()
        doc.close()
        
        # Use the proven regex from pdf_parser.py (FREE!)
        company = identify_company(full_text)
        
        if not company:
            print("Could not identify insurance company")
            return None
        
        print(f"Regex identified company: {company} (0 credits used)")
        
        # Step 2: Create company-specific schema (smaller = fewer tokens = fewer credits!)
        schema = get_company_schema(company)
        
        # Step 3: Single targeted API call
        extracted = call_extraction_api(pdf_content, filename, schema)
        
        if not extracted:
            print("Could not extract data using AI")
            return None
        
        # Map to standard format based on company
        result = {}
        if company == "HDI":
            result = map_hdi_data(extracted)
        elif company == "Qualitas":
            result = map_qualitas_data(extracted)
        elif company == "ANA":
            result = map_ana_data(extracted)
        elif company == "Atlas":
            result = map_atlas_data(extracted)
        else:
            print(f"Unknown company: {company}")
            return None
        
        return result
        
    except Exception as e:
        print(f"Error parsing PDF with AI: {str(e)}")
        return None


def get_company_schema(company: str) -> dict:
    """
    Get company-specific extraction schema (smaller schemas = fewer credits).
    Each company has field names optimized for their specific PDF format.
    """
    # Base schema shared by all companies
    base_schema = {
        "type": "object",
        "properties": {
            "vehicle_name": {
                "type": "string",
                "description": "Full vehicle description including brand, model, and year"
            },
            "Prima_Neta": {
                "type": "string",
                "description": "Prima Neta amount"
            },
            "Recargos": {
                "type": "string",
                "description": "Recargos, Recargos por Financiamiento, or TASA FIN.P.F. (Qualitas) amount"
            },
            "Derechos": {
                "type": "string",
                "description": "Derechos de Póliza or Gastos de Expedición amount"
            },
            "IVA": {
                "type": "string",
                "description": "IVA amount"
            },
            "Prima_Total": {
                "type": "string",
                "description": "Total a Pagar or Prima Total or IMPORTE TOTAL amount"
            },
            "Forma_Pago": {
                "type": "string",
                "description": "FORMA DE PAGO"
            },
            "Danos_Materiales": {
                "type": "string",
                "description": "Daños Materiales suma asegurada"
            },
            "Robo_Total": {
                "type": "string",
                "description": "Robo Total suma asegurada"
            },
            "Responsabilidad_Civil": {
                "type": "string",
                "description": "Responsabilidad Civil amount"
            },
            "Gastos_Medicos": {
                "type": "string",
                "description": "Gastos Médicos Ocupantes amount"
            },
            "Asistencia_Legal": {
                "type": "string",
                "description": "Legal assistance coverage. Field names vary by company: 'DEFENSA JURIDICA Y ASIST. LEGAL' (ANA - amount), 'Gastos Legales' (Qualitas - status AMPARADA/NO AMPARADA), 'ASISTENCIA LEGAL' (Atlas - amount), 'Asistencia Jurídica' or 'Asistencia Legal' (HDI - status Amparada/No Amparada). Extract the value (amount or status)."
            },
            "Asistencia_Viajes": {
                "type": "string",
                "description": "Travel assistance coverage. Field names vary: 'ANA ASISTENCIA' (ANA), 'Asistencia Vial' (Qualitas - status AMPARADA/NO AMPARADA), 'ASISTENCIA EN VIAJES' (Atlas), 'Asistencia en viajes' (HDI - status Amparada/No Amparada). Extract the value (status or if not found, infer from context)."
            },
            "RC_Catastrofica": {
                "type": "string",
                "description": "Catastrophic civil liability coverage. Field names vary: 'RC CATASTROFICA POR MUERTE' (ANA), 'RC Complementaria Personas' (Qualitas), 'RESPONSABILIDAD CIVIL CATASTRÓFICA POR FALLECIMIENTO' (Atlas), 'Responsabilidad Civil en Exceso por Muerte de Personas' (HDI). Extract the amount value."
            }
        },
        "required": ["vehicle_name", "Prima_Total"]
    }
    
    # Add company-specific fields
    if company == "ANA":
        base_schema["properties"]["Desbielamiento"] = {
            "type": "string",
            "description": "Water damage to motor coverage. Field name: 'DESBIELAMIENTO POR AGUA' or 'DESBIELAMIENTO POR AGUA AL MOTOR'. Extract status (AMPARADO/NO AMPARADO) or if not found return N/A. Only present in ANA PDFs."
        }
    
    return base_schema


def map_hdi_data(extracted: dict) -> Dict[str, str]:
    """Map unified extracted data to HDI Seguros format."""
    result = {"company": "HDI Seguros"}
    result["vehicle_name"] = extracted.get("vehicle_name", "")
    result["Prima Neta"] = format_currency(extracted.get("Prima_Neta"))
    result["Recargos"] = format_currency(extracted.get("Recargos"))
    result["Derechos de Póliza"] = format_currency(extracted.get("Derechos"))
    result["IVA"] = format_currency(extracted.get("IVA"))
    result["Prima Total"] = format_currency(extracted.get("Prima_Total"))
    result["Forma de Pago"] = "CONTADO"
    result["Daños Materiales"] = format_currency(extracted.get("Danos_Materiales"))
    result["Robo Total"] = format_currency(extracted.get("Robo_Total"))
    result["Responsabilidad Civil"] = format_currency(extracted.get("Responsabilidad_Civil"))
    result["Gastos Medicos Ocupantes"] = format_currency(extracted.get("Gastos_Medicos"))
    result["Asistencia Legal"] = format_currency(extracted.get("Asistencia_Legal", "N/A"))
    result["Asistencia Viajes"] = format_currency(extracted.get("Asistencia_Viajes", "N/A"))
    result["Responsabilidad civil catastrofica"] = format_currency(extracted.get("RC_Catastrofica"))
    result["Desbielamiento por agua al motor"] = "N/A"
    return result


def map_qualitas_data(extracted: dict) -> Dict[str, str]:
    """Map unified extracted data to Qualitas format."""
    result = {"company": "Qualitas"}
    result["vehicle_name"] = extracted.get("vehicle_name", "")
    result["Prima Neta"] = format_currency(extracted.get("Prima_Neta"))
    result["Recargos"] = format_currency(extracted.get("Recargos"))
    result["Derechos de Póliza"] = format_currency(extracted.get("Derechos"))
    result["IVA"] = format_currency(extracted.get("IVA"))
    result["Prima Total"] = format_currency(extracted.get("Prima_Total"))
    result["Forma de Pago"] = "CONTADO"
    result["Daños Materiales"] = format_currency(extracted.get("Danos_Materiales"))
    result["Robo Total"] = format_currency(extracted.get("Robo_Total"))
    result["Responsabilidad Civil"] = format_currency(extracted.get("Responsabilidad_Civil"))
    result["Gastos Medicos Ocupantes"] = format_currency(extracted.get("Gastos_Medicos"))
    result["Asistencia Legal"] = format_currency(extracted.get("Asistencia_Legal", "N/A"))
    result["Asistencia Viajes"] = format_currency(extracted.get("Asistencia_Viajes", "N/A"))
    result["Responsabilidad civil catastrofica"] = format_currency(extracted.get("RC_Catastrofica"))
    result["Desbielamiento por agua al motor"] = "N/A"
    
    return result


def map_ana_data(extracted: dict) -> Dict[str, str]:
    """Map unified extracted data to ANA Seguros format."""
    result = {"company": "ANA Seguros"}
    result["vehicle_name"] = extracted.get("vehicle_name", "")
    result["Prima Neta"] = format_currency(extracted.get("Prima_Neta"))
    result["Recargos"] = format_currency(extracted.get("Recargos"))
    result["Derechos de Póliza"] = format_currency(extracted.get("Derechos"))
    result["IVA"] = format_currency(extracted.get("IVA"))
    result["Prima Total"] = format_currency(extracted.get("Prima_Total"))
    result["Forma de Pago"] = extracted.get("Forma_Pago", "N/A")
    result["Daños Materiales"] = format_currency(extracted.get("Danos_Materiales"))
    result["Robo Total"] = format_currency(extracted.get("Robo_Total"))
    result["Responsabilidad Civil"] = format_currency(extracted.get("Responsabilidad_Civil"))
    result["Gastos Medicos Ocupantes"] = format_currency(extracted.get("Gastos_Medicos"))
    result["Asistencia Legal"] = format_currency(extracted.get("Asistencia_Legal"))
    result["Asistencia Viajes"] = "Amparada"
    result["Responsabilidad civil catastrofica"] = format_currency(extracted.get("RC_Catastrofica"))
    result["Desbielamiento por agua al motor"] = format_currency(extracted.get("Desbielamiento", "N/A"))
    return result


def map_atlas_data(extracted: dict) -> Dict[str, str]:
    """Map unified extracted data to Seguros Atlas format."""
    result = {"company": "Seguros Atlas"}
    result["vehicle_name"] = extracted.get("vehicle_name", "")
    result["Prima Neta"] = format_currency(extracted.get("Prima_Neta"))
    result["Recargos"] = format_currency(extracted.get("Recargos"))
    result["Derechos de Póliza"] = format_currency(extracted.get("Derechos"))
    result["IVA"] = format_currency(extracted.get("IVA"))
    result["Prima Total"] = format_currency(extracted.get("Prima_Total"))
    result["Forma de Pago"] = extracted.get("Forma_Pago", "CONTADO")
    result["Daños Materiales"] = format_currency(extracted.get("Danos_Materiales"))
    result["Robo Total"] = format_currency(extracted.get("Robo_Total"))
    result["Responsabilidad Civil"] = format_currency(extracted.get("Responsabilidad_Civil"))
    result["Gastos Medicos Ocupantes"] = format_currency(extracted.get("Gastos_Medicos"))
    result["Asistencia Legal"] = format_currency(extracted.get("Asistencia_Legal"))
    result["Asistencia Viajes"] = "Amparada"
    result["Responsabilidad civil catastrofica"] = format_currency(extracted.get("RC_Catastrofica"))
    result["Desbielamiento por agua al motor"] = "N/A"
    return result


def call_extraction_api(pdf_content: bytes, filename: str, schema: dict) -> Optional[dict]:
    """
    Call Landing AI extraction API with the given schema.
    
    Args:
        pdf_content: PDF file content as bytes
        filename: Name of the file
        schema: JSON schema for extraction
        
    Returns:
        Extracted data dictionary or None if failed
    """
    headers = {"Authorization": f"Basic {LANDING_AI_API_KEY}"}
    
    try:
        files = [("pdf", (filename, pdf_content, "application/pdf"))]
        payload = {"fields_schema": json.dumps(schema)}
        
        response = requests.post(
            LANDING_AI_ENDPOINT,
            headers=headers,
            files=files,
            data=payload,
            timeout=90
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("data", {}).get("extracted_schema", {})
        else:
            print(f"Extraction API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error calling extraction API: {str(e)}")
        return None


def format_currency(value: Optional[str]) -> str:
    """
    Format extracted currency value with $ prefix and proper comma separators.
    
    Args:
        value: Extracted value (may already have $, be a plain number, or be text like "AMPARADA")
        
    Returns:
        Formatted currency string, text value (for non-numeric), or "N/A" if invalid
    """
    if not value:
        return "N/A"
    
    value_str = str(value).strip()
    
    if not value_str or value_str.upper() == "N/A":
        return "N/A"
    
    # Check if this is a text value like "AMPARADA", "Amparada", etc (not a number)
    # Remove $ and commas to check if it's numeric
    check_str = value_str.replace("$", "").replace(",", "").replace(" ", "").strip()
    
    # If after removing currency symbols it's not a number, return as-is (capitalize properly)
    try:
        float(check_str)
    except ValueError:
        # Not a number - it's text like "AMPARADA", "AMPARADO", "Amparada", etc
        # Return with proper capitalization (use feminine form for consistency)
        if value_str.upper() in ["AMPARADA", "AMPARADO"]:
            return "Amparada"
        elif value_str.upper() in ["NO AMPARADA", "NO AMPARADO"]:
            return "No Amparada"
        return value_str.capitalize()
    
    # It's a number - format it properly with commas
    try:
        # Remove existing $ and commas
        num_str = value_str.replace("$", "").replace(",", "").replace(" ", "").strip()
        num_value = float(num_str)
        
        # Format with commas and 2 decimal places
        formatted = f"{num_value:,.2f}"
        return f"${formatted}"
    except Exception:
        # If formatting fails, return original with $ if it doesn't have it
        if value_str.startswith("$"):
            return value_str
        return f"${value_str}"
