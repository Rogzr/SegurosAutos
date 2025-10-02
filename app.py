"""
Flask web application for insurance PDF comparison.
Allows users to upload multiple insurance quotation PDFs, parse them,
and generate a comparison table that can be exported as PDF.
"""

import os
import io
from flask import Flask, render_template, request, send_file, url_for
try:
    # Wrap WSGI Flask app so it can run under ASGI servers (uvicorn)
    from asgiref.wsgi import WsgiToAsgi  # type: ignore
except Exception:  # asgiref may be missing locally
    WsgiToAsgi = None  # type: ignore
from datetime import datetime
from pdf_parser import parse_pdf

# WeasyPrint availability will be checked at runtime
WEASYPRINT_AVAILABLE = None

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Master field list for consistent table structure
MASTER_FIELDS = [
    'Prima',
    'Forma de Pago',
    'Daños Materiales',
    'Deducible - DM',
    'Robo Total',
    'Deducible - RT',
    'Responsabilidad Civil',
    'Gastos Medicos Ocupantes',
    'Asistencia Legal',
    'Asistencia Viajes',
    'Atlas Cero Plus por PT de DM',
    'Accidente al conductor',
    'Responsabilidad civil catastrofica',
    'Desbielamiento por agua al motor'
]

@app.route('/')
def index():
    """Render the main upload page."""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_files():
    """
    Process uploaded PDF files and display comparison results.
    """
    if 'files' not in request.files:
        return render_template('index.html', error="No files selected")
    
    files = request.files.getlist('files')
    
    if not files or all(file.filename == '' for file in files):
        return render_template('index.html', error="No files selected")
    
    parsed_data = []
    errors = []
    
    # Process each uploaded file
    for file in files:
        if file and file.filename.lower().endswith('.pdf'):
            try:
                # Read PDF content
                pdf_content = file.read()
                
                # Parse the PDF
                result = parse_pdf(pdf_content)
                
                if result:
                    parsed_data.append(result)
                else:
                    errors.append(f"Could not parse {file.filename}")
                    
            except Exception as e:
                errors.append(f"Error processing {file.filename}: {str(e)}")
        else:
            errors.append(f"Invalid file type: {file.filename}")
    
    if not parsed_data:
        return render_template('index.html', error="No valid PDFs could be parsed")
    
    # Sort data alphabetically by company name for consistent display
    parsed_data.sort(key=lambda x: x.get('company', ''))

    # Global hard-coded overrides/defaults for highlighted rows
    for row in parsed_data:
        # Ensure consistent defaults
        row.setdefault('Asistencia Viajes', 'AMPARADA')
        row['Atlas Cero Plus por PT de DM'] = 'AMPARADA'
        row['Accidente al conductor'] = '$100,000.00'
        # Hardcoded deductibles and limits based on example
        # These apply to all companies unless overridden later
        if 'Daños Materiales' in row and row['Daños Materiales'] and row['Daños Materiales'] != 'N/A':
            # Keep original limit text; set a standard deductible line
            row['Deducible - DM'] = '3%'
        else:
            row['Deducible - DM'] = '3%'

        if 'Robo Total' in row and row['Robo Total'] and row['Robo Total'] != 'N/A':
            row['Deducible - RT'] = '5%'
        else:
            row['Deducible - RT'] = '5%'

        # Atlas-specific coverage present in the example
        if row.get('company') == 'Seguros Atlas':
            row['Desbielamiento por agua al motor'] = 'AMPARADA'
    
    return render_template('results.html', 
                         data=parsed_data, 
                         fields=MASTER_FIELDS,
                         errors=errors,
                         today_str=datetime.now().strftime('%d/%m/%Y'),
                         vehicle_name='')

@app.route('/export')
def export_pdf():
    """
    Export the comparison table as a PDF file.
    This route is deprecated - use the export with data route instead.
    """
    return render_template('index.html', error="Please process files first, then use the export button")

def check_weasyprint_availability():
    """Check if WeasyPrint is available and cache the result."""
    global WEASYPRINT_AVAILABLE
    if WEASYPRINT_AVAILABLE is None:
        try:
            from weasyprint import HTML, CSS
            from weasyprint.text.fonts import FontConfiguration
            WEASYPRINT_AVAILABLE = True
        except Exception as e:
            # On Windows, WeasyPrint raises OSError due to missing GTK/Pango libs.
            print(f"WeasyPrint not available: {e}")
            print("PDF export will not be available in local development (Windows). Deploy to Railway for full export.")
            WEASYPRINT_AVAILABLE = False
    return WEASYPRINT_AVAILABLE

@app.route('/export/<path:data_json>')
def export_pdf_with_data(data_json):
    """
    Export PDF with data passed as JSON in URL.
    This is a workaround for the stateless nature of HTTP.
    """
    if not check_weasyprint_availability():
        return "PDF export not available in local development. Please deploy to Railway for full functionality.", 503
    
    import json
    import base64
    from weasyprint import HTML, CSS
    from weasyprint.text.fonts import FontConfiguration
    
    try:
        # Decode the base64 encoded JSON data
        decoded_data = base64.b64decode(data_json).decode('utf-8')
        payload = json.loads(decoded_data)
        # Support both legacy (list) and new {data, meta}
        if isinstance(payload, dict) and 'data' in payload:
            parsed_data = payload.get('data') or []
            vehicle_name = (payload.get('meta') or {}).get('vehicle_name', '')
            date_str = (payload.get('meta') or {}).get('date', datetime.now().strftime('%d/%m/%Y'))
        else:
            parsed_data = payload
            vehicle_name = ''
            date_str = datetime.now().strftime('%d/%m/%Y')
        
        # Sort data alphabetically by company name
        parsed_data.sort(key=lambda x: x.get('company', ''))
        
        # Generate external URLs for logos
        strategos_logo = url_for('static', filename='strategos_logo.jpg', _external=True)
        # Company logos map (filenames must exist in /static)
        logo_map = {
            'ANA': url_for('static', filename='ana_logo.png', _external=True),
            'ANA SEGUROS': url_for('static', filename='ana_logo.png', _external=True),
            'SEGUR0S ATLAS': url_for('static', filename='atlas_logo.png', _external=True),
            'SEGUROS ATLAS': url_for('static', filename='atlas_logo.png', _external=True),
            'HDI': url_for('static', filename='hdi_logo.png', _external=True),
            'HDI SEGUROS': url_for('static', filename='hdi_logo.png', _external=True),
            'QUALITAS': url_for('static', filename='qualitas_logo.png', _external=True),
            'QUÁLITAS': url_for('static', filename='qualitas_logo.png', _external=True),
        }
        # Build list aligned with data order
        company_logos = []
        for item in parsed_data:
            name = (item.get('company') or '').upper()
            # Find a matching key in map
            logo = None
            for key, val in logo_map.items():
                if key in name:
                    logo = val
                    break
            company_logos.append(logo)
        
        # Render HTML with export flag
        html_content = render_template('results.html',
                                     data=parsed_data,
                                     fields=MASTER_FIELDS,
                                     is_export=True,
                                     logo_url=strategos_logo,
                                     company_logos=company_logos,
                                     today_str=date_str,
                                     vehicle_name=vehicle_name)
        
        # Configure fonts for WeasyPrint
        font_config = FontConfiguration()
        
        # Create PDF with WeasyPrint
        pdf_buffer = io.BytesIO()
        
        # Additional CSS for PDF export
        pdf_css = CSS(string='''
            @page {
                size: A4 landscape;
                margin: 1cm;
            }
            body {
                font-family: Arial, sans-serif;
                font-size: 10px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            th, td {
                border: 1px solid #333;
                padding: 8px;
                text-align: left;
            }
            th {
                background-color: #f0f0f0;
                font-weight: bold;
            }
            .logo {
                max-width: 150px;
                max-height: 50px;
            }
            .export-button {
                display: none;
            }
        ''', font_config=font_config)
        
        HTML(string=html_content).write_pdf(pdf_buffer, stylesheets=[pdf_css], font_config=font_config)
        
        pdf_buffer.seek(0)
        
        return send_file(pdf_buffer, 
                       as_attachment=True, 
                       download_name='comparison.pdf',
                       mimetype='application/pdf')
        
    except Exception as e:
        return f"Error generating PDF: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

# Expose ASGI-compatible app for uvicorn in production
if WsgiToAsgi is not None:
    asgi_app = WsgiToAsgi(app)
else:
    # Fallback so local dev doesn't break if asgiref isn't installed yet
    asgi_app = app
