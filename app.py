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
    'Desbielamiento por agua al motor',
    # Breakdown rows (shown al final de la tabla)
    'Prima Neta',
    'Recargos',
    'Derechos de Póliza',
    'IVA',
    'Prima Total'
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
    detected_vehicle = ''
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
        # Capture vehicle name if any parser provided it
        if not detected_vehicle and row.get('vehicle_name'):
            detected_vehicle = row.get('vehicle_name')
    
    # Build header colors for non-export view (used to color summary rows)
    header_colors: list[str] = []
    color_map = {
        'ANA': '#FE1034',
        'ANA SEGUROS': '#FE1034',
        'HDI': '#006729',
        'HDI SEGUROS': '#006729',
        'QUALITAS': '#666678',
        'QUÁLITAS': '#666678',
        'SEGUROS ATLAS': '#D0112B',
        'ATLAS': '#D0112B'
    }
    for item in parsed_data:
        name = (item.get('company') or '').upper()
        color_val = '#0b4a6a'
        for key, c in color_map.items():
            if key in name:
                color_val = c
                break
        header_colors.append(color_val)

    remaining = 78.0
    num_cols = max(len(parsed_data), 1)
    company_col_width = f"{remaining/num_cols:.2f}%"

    # Hide Atlas-specific row if no Atlas quotation uploaded
    has_atlas = any('ATLAS' in (row.get('company','').upper()) for row in parsed_data)
    dyn_fields = [f for f in MASTER_FIELDS if has_atlas or f != 'Atlas Cero Plus por PT de DM']

    return render_template('results.html', 
                         data=parsed_data, 
                         fields=dyn_fields,
                         errors=errors,
                         today_str=datetime.now().strftime('%d/%m/%Y'),
                         vehicle_name=detected_vehicle,
                         header_colors=header_colors,
                         company_col_width=company_col_width)

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
        # Support base64 generated from browser with UTF-8 characters
        try:
            decoded_data = base64.b64decode(data_json).decode('utf-8')
        except Exception:
            # Try URL-safe and Latin-1 fallbacks then re-encode to UTF-8
            decoded_bytes = base64.b64decode(data_json + '==')
            try:
                decoded_data = decoded_bytes.decode('utf-8')
            except UnicodeDecodeError:
                decoded_data = decoded_bytes.decode('latin-1')
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
        
        # Helper: build data URI for static images so WeasyPrint embeds them reliably
        import base64, mimetypes
        def _data_uri(static_filename: str) -> str:
            file_path = os.path.join(app.root_path, 'static', static_filename)
            mime = mimetypes.guess_type(file_path)[0] or 'image/png'
            with open(file_path, 'rb') as f:
                b64 = base64.b64encode(f.read()).decode('ascii')
            return f"data:{mime};base64,{b64}"

        # Header logo (requested strategos_footer.png at the top)
        strategos_logo = _data_uri('strategos_footer.png')

        # Company logos map (filenames must exist in /static)
        logo_map = {
            'ANA SEGUROS': _data_uri('ana_logo.png'),
            'ANA': _data_uri('ana_logo.png'),
            'SEGUROS ATLAS': _data_uri('atlas_logo.png'),
            'ATLAS': _data_uri('atlas_logo.png'),
            'HDI SEGUROS': _data_uri('hdi_logo.png'),
            'HDI': _data_uri('hdi_logo.png'),
            'QUÁLITAS': _data_uri('qualitas_logo.png'),
            'QUALITAS': _data_uri('qualitas_logo.png'),
        }
        # Build lists aligned with data order
        company_logos = []
        header_colors = []
        color_map = {
            'ANA': '#FE1034',            # ANA red (brand)
            'ANA SEGUROS': '#FE1034',
            'HDI': '#006729',            # HDI green (brand)
            'HDI SEGUROS': '#006729',
            'QUALITAS': '#666678',       # Quálitas gray (brand)
            'QUÁLITAS': '#666678',
            'SEGUROS ATLAS': '#D0112B',  # Atlas red (brand)
            'ATLAS': '#D0112B'
        }
        for item in parsed_data:
            name = (item.get('company') or '').upper()
            # Find a matching key in map
            logo = None
            for key, val in logo_map.items():
                if key in name:
                    logo = val
                    break
            company_logos.append(logo)
            # Color
            color_val = '#0b4a6a'
            for key, c in color_map.items():
                if key in name:
                    color_val = c
                    break
            header_colors.append(color_val)
        
        # Render HTML with export flag
        # Width for company columns (keep 22% for coverages column)
        remaining = 78.0
        num_cols = max(len(parsed_data), 1)
        company_col_width = f"{remaining/num_cols:.2f}%"

        # Hide Atlas-specific row for export as well if no Atlas present
        has_atlas_export = any('ATLAS' in (row.get('company','').upper()) for row in parsed_data)
        dyn_fields_export = [f for f in MASTER_FIELDS if has_atlas_export or f != 'Atlas Cero Plus por PT de DM']

        html_content = render_template('results.html',
                                     data=parsed_data,
                                     fields=dyn_fields_export,
                                     is_export=True,
                                     logo_url=strategos_logo,
                                     company_logos=company_logos,
                                     header_colors=header_colors,
                                     company_col_width=company_col_width,
                                     today_str=date_str,
                                     vehicle_name=vehicle_name)
        
        # Configure fonts for WeasyPrint
        font_config = FontConfiguration()
        
        # Create PDF with WeasyPrint
        pdf_buffer = io.BytesIO()
        
        # Additional CSS for PDF export
        pdf_css = CSS(string='''
            @page {
                size: A4 portrait;
                margin: 12mm;
            }
            body {
                font-family: Arial, sans-serif;
                font-size: 11px;
                color: #1f2c36;
            }
            table {
                width: 100%;
                border-collapse: separate;
                border-spacing: 3px;
                margin-top: 10px;
                table-layout: fixed;
            }
            th, td {
                border: 1px solid #cfd8dc;
                padding: 8px 10px;
                text-align: left;
                vertical-align: middle;
                word-wrap: break-word;
                background: #ffffff;
                border-radius: 6px;
            }
            th {
                background: #eef2f6;
                color: #1f2c36;
                font-weight: bold;
            }
            /* Coverage column cells */
            td.field-name {
                background: #0b4a6a;
                color: #fff;
                font-weight: 700;
            }
            /* Brand highlight for summary rows in PDF as well */
            td.field-value.summary { color:#fff; font-weight:700; text-align:center; }
            thead th:first-child { width: 22%; }
            .logo {
                max-width: 150px;
                max-height: 50px;
            }
            .export-button {
                display: none;
            }
            .meta {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 18px;
                margin: 6px 0 10px 0;
                color: #4a5961;
            }
            .meta .vehiculo { font-weight: 600; color: #0b4a6a; line-height: 1.2; }
            .meta .vehiculo .vehiculo-name { margin-top: 2px; font-weight: 700; color: #163d52; }
            th.company-header-cell { text-align: center; }
            .company-header-inner { display:flex; align-items:center; justify-content:center; height: 100%; width: 100%; }
            .company-header-inner img { height: 24px; object-fit: contain; margin: 4px auto; display:block; }
            /* Center values */
            td.field-value { text-align: center; }
        ''', font_config=font_config)
        
        # Server-side safety: recompute IVA and Prima Total in case client didn't
        try:
            for item in parsed_data:
                def to_num(s: str) -> float:
                    import re
                    if not s:
                        return 0.0
                    n = re.sub(r"[^0-9.,-]", "", str(s)).replace(",", "")
                    try:
                        return float(n)
                    except Exception:
                        return 0.0
                pn = to_num(item.get('Prima Neta'))
                rec = to_num(item.get('Recargos'))
                der = to_num(item.get('Derechos de Póliza'))
                iva = (pn + rec + der) * 0.16
                total = pn + rec + der + iva
                item['IVA'] = f"${iva:,.2f}"
                item['Prima Total'] = f"${total:,.2f}"
        except Exception:
            pass

        html_content = render_template('results.html',
                                     data=parsed_data,
                                     fields=MASTER_FIELDS,
                                     is_export=True,
                                     logo_url=strategos_logo,
                                     company_logos=company_logos,
                                     header_colors=header_colors,
                                     company_col_width=company_col_width,
                                     today_str=date_str,
                                     vehicle_name=vehicle_name)

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
