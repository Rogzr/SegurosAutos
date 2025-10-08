"""
PDF parsing module using Landing AI's Agentic Document Extraction.
Handles parsing of PDFs from four specific insurance companies:
- HDI Seguros
- Qualitas
- ANA Seguros
- Seguros Atlas
"""

import os
import json
import requests
from typing import Dict, Optional

# Get API key from environment
LANDING_AI_API_KEY = os.getenv('LANDING_AI_API_KEY')
LANDING_AI_ENDPOINT = os.getenv('LANDING_AI_ENDPOINT', 'https://api.va.landing.ai/v1/tools/agentic-document-analysis')


def parse_pdf_ai(pdf_content: bytes, filename: str = "document.pdf") -> Optional[Dict[str, str]]:
    """
    Main function to parse PDF content using Landing AI and extract insurance data.
    
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
        # Step 1: Classify which insurance company
        company = classify_company_ai(pdf_content, filename)
        
        if not company:
            print("Could not identify insurance company using AI")
            return None
        
        print(f"AI identified company: {company}")
        
        # Step 2: Extract fields based on company
        if company == "HDI":
            return extract_hdi_ai(pdf_content, filename)
        elif company == "Qualitas":
            return extract_qualitas_ai(pdf_content, filename)
        elif company == "ANA":
            return extract_ana_ai(pdf_content, filename)
        elif company == "Atlas":
            return extract_atlas_ai(pdf_content, filename)
        
        return None
        
    except Exception as e:
        print(f"Error parsing PDF with AI: {str(e)}")
        return None


def classify_company_ai(pdf_content: bytes, filename: str) -> Optional[str]:
    """
    Classify which insurance company the PDF is from using Landing AI.
    
    Args:
        pdf_content: Raw PDF file content as bytes
        filename: Name of the PDF file
        
    Returns:
        Company identifier ("HDI", "Qualitas", "ANA", "Atlas") or None
    """
    headers = {"Authorization": f"Basic {LANDING_AI_API_KEY}"}
    
    # Define classification schema
    classification_schema = {
        "type": "object",
        "properties": {
            "company": {
                "type": "string",
                "enum": ["HDI", "Qualitas", "ANA", "Atlas"],
                "description": "The insurance company that issued this quotation. HDI Seguros should be 'HDI', Qualitas/Quálitas should be 'Qualitas', ANA Seguros should be 'ANA', and Seguros Atlas should be 'Atlas'."
            }
        },
        "required": ["company"]
    }
    
    try:
        files = [("pdf", (filename, pdf_content, "application/pdf"))]
        payload = {"fields_schema": json.dumps(classification_schema)}
        
        response = requests.post(
            LANDING_AI_ENDPOINT,
            headers=headers,
            files=files,
            data=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            company = result.get("data", {}).get("extracted_schema", {}).get("company")
            return company
        else:
            print(f"Classification API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"Error in company classification: {str(e)}")
        return None


def extract_hdi_ai(pdf_content: bytes, filename: str) -> Dict[str, str]:
    """Extract fields from HDI Seguros PDF using Landing AI."""
    
    schema = {
        "type": "object",
        "properties": {
            "vehicle_name": {
                "type": "string",
                "description": "The full vehicle description including brand, model, and year (e.g., VOLKSWAGEN JETTA 2024)"
            },
            "Prima_Neta": {
                "type": "string",
                "description": "Prima Neta amount in currency format"
            },
            "Recargos": {
                "type": "string",
                "description": "Recargos or Recargos por Financiamiento amount"
            },
            "Derechos": {
                "type": "string",
                "description": "Derechos de Póliza or Gastos de Expedición amount"
            },
            "IVA": {
                "type": "string",
                "description": "IVA (tax) amount"
            },
            "Prima_Total": {
                "type": "string",
                "description": "Total a Pagar or Prima Total amount"
            },
            "Danos_Materiales": {
                "type": "string",
                "description": "Daños Materiales coverage limit amount"
            },
            "Robo_Total": {
                "type": "string",
                "description": "Robo Total coverage limit amount"
            },
            "Responsabilidad_Civil": {
                "type": "string",
                "description": "Responsabilidad Civil (Límite Único y Combinado) amount"
            },
            "Gastos_Medicos": {
                "type": "string",
                "description": "Gastos Médicos Ocupantes (Límite Único Combinado) amount"
            },
            "Asistencia_Legal": {
                "type": "string",
                "description": "Asistencia Jurídica or Asistencia Legal status (Amparada or No Amparada)"
            },
            "Asistencia_Viajes": {
                "type": "string",
                "description": "Asistencia en viajes status (Amparada or No Amparada)"
            },
            "RC_Catastrofica": {
                "type": "string",
                "description": "Responsabilidad Civil en Exceso por Muerte de Personas amount"
            }
        },
        "required": ["vehicle_name", "Prima_Total"]
    }
    
    extracted = call_extraction_api(pdf_content, filename, schema)
    
    if not extracted:
        return {"company": "HDI Seguros"}
    
    # Map to standard format
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
    result["Asistencia Legal"] = extracted.get("Asistencia_Legal", "N/A")
    result["Asistencia Viajes"] = extracted.get("Asistencia_Viajes", "N/A")
    result["Responsabilidad civil catastrofica"] = format_currency(extracted.get("RC_Catastrofica"))
    result["Desbielamiento por agua al motor"] = "N/A"
    
    return result


def extract_qualitas_ai(pdf_content: bytes, filename: str) -> Dict[str, str]:
    """Extract fields from Qualitas PDF using Landing AI."""
    
    schema = {
        "type": "object",
        "properties": {
            "vehicle_name": {
                "type": "string",
                "description": "The full vehicle description including brand, model, and year"
            },
            "Prima_Neta": {
                "type": "string",
                "description": "Prima Neta amount"
            },
            "Recargos": {
                "type": "string",
                "description": "Recargos amount"
            },
            "Derechos": {
                "type": "string",
                "description": "Derechos de Póliza, Gastos de Expedición, or GTOS. EXPEDICION POL. amount"
            },
            "IVA": {
                "type": "string",
                "description": "IVA amount"
            },
            "Prima_Total": {
                "type": "string",
                "description": "IMPORTE TOTAL or Prima Total amount"
            },
            "Danos_Materiales": {
                "type": "string",
                "description": "Daños materiales suma asegurada amount"
            },
            "Robo_Total": {
                "type": "string",
                "description": "Robo total suma asegurada amount"
            },
            "Responsabilidad_Civil": {
                "type": "string",
                "description": "Responsabilidad Civil amount per event"
            },
            "Gastos_Medicos": {
                "type": "string",
                "description": "Gastos Medicos Ocupantes amount"
            },
            "Gastos_Legales": {
                "type": "string",
                "description": "Gastos Legales status (AMPARADA or NO AMPARADA)"
            },
            "Asistencia_Vial": {
                "type": "string",
                "description": "Asistencia Vial status (AMPARADA or NO AMPARADA)"
            },
            "RC_Complementaria": {
                "type": "string",
                "description": "RC Complementaria Personas amount"
            }
        },
        "required": ["vehicle_name", "Prima_Total"]
    }
    
    extracted = call_extraction_api(pdf_content, filename, schema)
    
    if not extracted:
        return {"company": "Qualitas"}
    
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
    result["Asistencia Legal"] = extracted.get("Gastos_Legales", "N/A")
    result["Asistencia Viajes"] = extracted.get("Asistencia_Vial", "N/A")
    result["Responsabilidad civil catastrofica"] = format_currency(extracted.get("RC_Complementaria"))
    result["Desbielamiento por agua al motor"] = "N/A"
    
    return result


def extract_ana_ai(pdf_content: bytes, filename: str) -> Dict[str, str]:
    """Extract fields from ANA Seguros PDF using Landing AI."""
    
    schema = {
        "type": "object",
        "properties": {
            "vehicle_name": {
                "type": "string",
                "description": "The full vehicle description including brand, model, and year"
            },
            "Prima_Neta": {
                "type": "string",
                "description": "Prima Neta amount"
            },
            "Recargos": {
                "type": "string",
                "description": "Recargos amount"
            },
            "Derechos": {
                "type": "string",
                "description": "Derechos de Póliza amount"
            },
            "IVA": {
                "type": "string",
                "description": "IVA amount"
            },
            "Prima_Total": {
                "type": "string",
                "description": "PRIMA TOTAL amount"
            },
            "Forma_Pago": {
                "type": "string",
                "description": "FORMA DE PAGO"
            },
            "Danos_Materiales": {
                "type": "string",
                "description": "DAÑOS MATERIALES suma asegurada"
            },
            "Robo_Total": {
                "type": "string",
                "description": "ROBO TOTAL suma asegurada"
            },
            "Responsabilidad_Civil": {
                "type": "string",
                "description": "RESPONSABILIDAD CIVIL amount"
            },
            "Gastos_Medicos": {
                "type": "string",
                "description": "GASTOS MEDICOS OCUPANTES amount"
            },
            "Defensa_Juridica": {
                "type": "string",
                "description": "DEFENSA JURIDICA Y ASIST. LEGAL amount"
            },
            "RC_Catastrofica": {
                "type": "string",
                "description": "RC CATASTROFICA POR MUERTE amount"
            },
            "Desbielamiento": {
                "type": "string",
                "description": "DESBIELAMIENTO POR AGUA amount"
            }
        },
        "required": ["vehicle_name", "Prima_Total"]
    }
    
    extracted = call_extraction_api(pdf_content, filename, schema)
    
    if not extracted:
        return {"company": "ANA Seguros"}
    
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
    result["Asistencia Legal"] = format_currency(extracted.get("Defensa_Juridica"))
    result["Asistencia Viajes"] = "Amparada"
    result["Responsabilidad civil catastrofica"] = format_currency(extracted.get("RC_Catastrofica"))
    result["Desbielamiento por agua al motor"] = format_currency(extracted.get("Desbielamiento"))
    
    return result


def extract_atlas_ai(pdf_content: bytes, filename: str) -> Dict[str, str]:
    """Extract fields from Seguros Atlas PDF using Landing AI."""
    
    schema = {
        "type": "object",
        "properties": {
            "vehicle_name": {
                "type": "string",
                "description": "The full vehicle description including brand, model, and year"
            },
            "Prima_Neta": {
                "type": "string",
                "description": "PRIMA NETA amount"
            },
            "Recargos": {
                "type": "string",
                "description": "Recargos amount"
            },
            "Derechos": {
                "type": "string",
                "description": "Derechos de Póliza amount"
            },
            "IVA": {
                "type": "string",
                "description": "IVA amount"
            },
            "Prima_Total": {
                "type": "string",
                "description": "PRIMA TOTAL amount"
            },
            "Forma_Pago": {
                "type": "string",
                "description": "FORMA DE PAGO"
            },
            "Danos_Materiales": {
                "type": "string",
                "description": "DAÑOS MATERIALES suma asegurada"
            },
            "Robo_Total": {
                "type": "string",
                "description": "ROBO TOTAL suma asegurada"
            },
            "Responsabilidad_Civil": {
                "type": "string",
                "description": "RESPONSABILIDAD CIVIL (LUC) amount"
            },
            "Gastos_Medicos": {
                "type": "string",
                "description": "GASTOS MEDICOS OCUPANTES (LUC) amount"
            },
            "Asistencia_Legal": {
                "type": "string",
                "description": "ASISTENCIA LEGAL amount"
            },
            "RC_Catastrofica": {
                "type": "string",
                "description": "RESPONSABILIDAD CIVIL CATASTRÓFICA POR FALLECIMIENTO amount"
            }
        },
        "required": ["vehicle_name", "Prima_Total"]
    }
    
    extracted = call_extraction_api(pdf_content, filename, schema)
    
    if not extracted:
        return {"company": "Seguros Atlas"}
    
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
        # Not a number - it's text like "AMPARADA", "Amparada", etc
        # Return with proper capitalization
        if value_str.upper() == "AMPARADA":
            return "Amparada"
        elif value_str.upper() == "NO AMPARADA":
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

