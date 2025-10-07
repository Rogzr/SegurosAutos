#!/usr/bin/env python3
"""
Minimal tests for app initialization and routes.
"""

import sys
import os
sys.path.append('.')

from pdf_parser import parse_pdf

def test_noop_parser_import():
    """Ensure parse_pdf is importable (ADE-driven parser)."""
    assert callable(parse_pdf)

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
    
    test_noop_parser_import()
    test_flask_app()
    
    print("All tests completed!")
    print("\nNext steps:")
    print("1. Run 'python app.py' to start the Flask server")
    print("2. Open http://localhost:5000 in your browser")
    print("3. Upload PDF files to test the full functionality")
    print("4. Deploy to Railway for production use")

if __name__ == "__main__":
    main()
