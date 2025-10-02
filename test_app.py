#!/usr/bin/env python3
"""
Test script for the Insurance PDF Parser
Tests the company identification and parsing functionality
"""

import sys
import os
sys.path.append('.')

from pdf_parser import identify_company, parse_hdi, parse_qualitas, parse_ana, parse_atlas

def test_company_identification():
    """Test company identification from text samples."""
    print("Testing Company Identification...")
    
    test_cases = [
        ("HDI SEGUROS policy document", "HDI"),
        ("Seguros Atlas quotation", "Atlas"),
        ("ANA SEGUROS insurance", "ANA"),
        ("Qualitas insurance policy", "Qualitas"),
        ("Unknown insurance company", None)
    ]
    
    for text, expected in test_cases:
        result = identify_company(text)
        status = "PASS" if result == expected else "FAIL"
        print(f"{status}: '{text[:30]}...' -> {result} (expected: {expected})")
    
    print()

def test_parsing_functions():
    """Test parsing functions with sample data."""
    print("Testing Parsing Functions...")
    
    # Sample HDI text
    hdi_sample = """
    HDI SEGUROS
    Total a Pagar: $15,000.00
    Daños Materiales
    Límite de Responsabilidad: $500,000
    Deducible: 5%
    Robo Total
    Límite de Responsabilidad: $500,000
    Deducible: 10%
    Responsabilidad Civil (Límite Único y Combinado): $1,000,000
    Gastos Médicos Ocupantes: $50,000
    Asistencia Jurídica: $25,000
    Asistencia en viajes: $10,000
    Accidentes Automovilísticos al Conductor: $100,000
    Responsabilidad Civil en Exceso por Muerte de Personas: $2,000,000
    """
    
    try:
        hdi_result = parse_hdi(hdi_sample)
        print("PASS: HDI parsing successful")
        print(f"   Company: {hdi_result.get('company', 'N/A')}")
        print(f"   Prima: {hdi_result.get('Prima', 'N/A')}")
        print(f"   Daños Materiales: {hdi_result.get('Daños Materiales', 'N/A')}")
    except Exception as e:
        print(f"FAIL: HDI parsing failed: {e}")
    
    print()

def test_flask_app():
    """Test Flask app creation."""
    print("Testing Flask App...")
    
    try:
        from app import app, check_weasyprint_availability
        
        print("PASS: Flask app created successfully")
        print(f"   Routes: {[rule.rule for rule in app.url_map.iter_rules()]}")
        
        weasyprint_available = check_weasyprint_availability()
        print(f"   WeasyPrint available: {weasyprint_available}")
        
    except Exception as e:
        print(f"FAIL: Flask app test failed: {e}")
    
    print()

def main():
    """Run all tests."""
    print("Insurance PDF Parser Test Suite")
    print("=" * 50)
    
    test_company_identification()
    test_parsing_functions()
    test_flask_app()
    
    print("All tests completed!")
    print("\nNext steps:")
    print("1. Run 'python app.py' to start the Flask server")
    print("2. Open http://localhost:5000 in your browser")
    print("3. Upload PDF files to test the full functionality")
    print("4. Deploy to Railway for production use")

if __name__ == "__main__":
    main()
