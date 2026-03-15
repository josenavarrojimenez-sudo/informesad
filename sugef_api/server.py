#!/usr/bin/env python3
"""
Portal de Firma Digital - Adelante Desarrollos
Permite al cliente firmar autorizaciones SUGEF con nombre, cédula y firma digital.
"""
from PIL import Image
import os, json, base64, io, tempfile, urllib.request, urllib.parse


def safe_b64decode(s: str) -> bytes:
    """Decode base64 string, auto-fixing missing padding and ignoring whitespace."""
    if s is None:
        return b""
    s = s.strip()
    # Remove whitespace/newlines
    s = "".join(s.split())
    # Fix missing padding
    missing = (-len(s)) % 4
    if missing:
        s += "=" * missing
    return base64.b64decode(s)

# ... (rest of imports)

def compress_image(image_bytes, max_size_kb=150, is_signature=False):
    """Compress image to stay under a very small size."""
    img = Image.open(io.BytesIO(image_bytes))
    
    # Signatures should remain transparent and in PNG format
    if is_signature:
        output = io.BytesIO()
        # Resize signature if it's crazy large, but keep it as transparent PNG
        if max(img.width, img.height) > 600:
            scale = 600 / max(img.width, img.height)
            img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
        img.save(output, format="PNG", optimize=True)
        return output.getvalue()

    # Regular photos should be flattened to JPEG with white background
    if img.mode in ("RGBA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "RGBA":
            background.paste(img, mask=img.split()[3])
        else:
            background.paste(img)
        img = background
    
    # Resize regular photos
    max_dim = 900
    if max(img.width, img.height) > max_dim:
        scale = max_dim / max(img.width, img.height)
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    
    quality = 65
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=True)
    
    # Aggressive loop to force size down for regular photos
    while output.tell() > max_size_kb * 1024 and quality > 10:
        quality -= 10
        if quality < 35:
            img = img.resize((int(img.width * 0.7), int(img.height * 0.7)), Image.LANCZOS)
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        
    return output.getvalue()
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, make_response
import pymupdf as fitz

# SMTP (Google Workspace)
import smtplib
from email.message import EmailMessage

app = Flask(__name__, static_folder='.')

@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, bypass-tunnel-reminder'
    return response

@app.route('/submit', methods=['OPTIONS'])
def submit_options():
    return make_response('', 200)

PDF_DIR = os.path.join(os.path.dirname(__file__), 'pdfs')
# Token file location:
# - Render Secret Files mount under /etc/secrets/<filename>
# - Local dev uses workspace path
TOKEN_FILE = '/etc/secrets/ms-token.json' if os.path.exists('/etc/secrets/ms-token.json') else '/data/.openclaw/workspace/ms-token.json'
CLIENT_ID = 'adbc90ee-fd38-4706-ac40-f9c187e91b34'
TENANT_ID = '27272476-d569-411c-ab78-6d3f3b7596e5'
DEST_EMAILS = [
    'willem@adelantedesarrollos.com',
    'luiscarlos@adelantedesarrollos.com',
    'hazel@adelantedesarrollos.com',
    'j@adelante.cr',
]
FROM_EMAIL = 'j@adelante.cr'

SMTP_HOST = os.environ.get('SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASS = os.environ.get('SMTP_PASS', '')

# Which PDFs to process (name → file)
DOCS = {
    '1. Autorización SUGEF 4.2': '02_SUGEF_4.2_BN.pdf',
    '2. Formulario SUGEF': '04_Formulario_SUGEF.pdf',
    '3. SUGEF 1': 'SUGEF_1.pdf',
    '4. SUGEF 6': 'SUGEF_6.pdf',
    '5. SUGEF 7': 'SUGEF_7.pdf',
    '6. SUGEF Banco Popular 2024': '06_SUGEF_BP_2024.pdf',
    '7. Autorización Específica Persona Física': '07_Formato_SUGEF_4.2.pdf',
}


def get_access_token():
    with open(TOKEN_FILE) as f:
        data = json.load(f)
    # Try current token first
    access_token = data.get('access_token', '')
    # Quick check by trying; if expired, refresh
    try:
        req = urllib.request.Request(
            'https://graph.microsoft.com/v1.0/me',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            if r.status == 200:
                return access_token
    except:
        pass
    # Refresh
    payload = urllib.parse.urlencode({
        'client_id': CLIENT_ID,
        'grant_type': 'refresh_token',
        'refresh_token': data.get('refresh_token', ''),
        'scope': 'Mail.Send offline_access'
    }).encode()
    req = urllib.request.Request(
        f'https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token',
        data=payload, method='POST'
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        new_data = json.load(r)
    new_data_full = {**data, **new_data}
    with open(TOKEN_FILE, 'w') as f:
        json.dump(new_data_full, f)
    return new_data['access_token']


def flatten_pdf(pdf_bytes, dpi=200):
    """Rasterize every page to look like a scanned document.
    Uses JPEG compression + scanner-style metadata so no image layers are detectable."""
    import struct, zlib
    src = fitz.open(stream=pdf_bytes, filetype="pdf")
    out_doc = fitz.open()
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    for page in src:
        pix = page.get_pixmap(matrix=mat, alpha=False)
        # Use JPEG (like real scanners) instead of PNG
        img_bytes = pix.tobytes("jpeg", jpg_quality=92)
        new_page = out_doc.new_page(width=page.rect.width, height=page.rect.height)
        new_page.insert_image(new_page.rect, stream=img_bytes)
    # Set scanner-like metadata to make it look like a scanned document
    out_doc.set_metadata({
        "producer": "Canon iR-ADV C5235 PDF",
        "creator": "Canon iR-ADV C5235 PDF",
        "title": "",
        "author": "",
        "subject": "",
        "keywords": "",
    })
    output = io.BytesIO()
    out_doc.save(output)
    out_doc.close()
    src.close()
    return output.getvalue()


def fill_pdf(pdf_path, nombre, cedula, firma_png_bytes, is_landscape=False):
    """Fills a PDF with name, cedula and signature on all pages."""
    doc = fitz.open(pdf_path)
    sig_img_bytes = firma_png_bytes
    today = datetime.now().strftime('%d/%m/%Y')

    for page in doc:
        w, h = page.rect.width, page.rect.height
        text = page.get_text()

        # BCR form usually has two "Firma de la persona" labels.
        # Jose wants to keep only the FIRST one.
        is_bcr_second_page = (pdf_path.endswith('04_Formulario_SUGEF.pdf') and page.number > 0)

        # Fill "Yo, _____" with name
        yo_hits = page.search_for("Yo,")
        for hit in yo_hits[:1]:
            # Place name sitting on the line
            name_x = hit.x1 + 3
            name_y = hit.y1 + 1 # Lowered slightly
            page.insert_text((name_x, name_y), nombre,
                             fontsize=9, color=(0, 0, 0))

        # Fill cedula — ignore header field, focus on inline paragraph patterns
        id_hits = (
            page.search_for("identificación número") or
            page.search_for("cédula de identidad número") or
            page.search_for("Identificación del usuario autorizado (documento")
        )
        for hit in id_hits[:1]:
            id_x = hit.x1 + 5
            id_y = hit.y1 + 1 # Lowered slightly
            page.insert_text((id_x, id_y), cedula,
                             fontsize=9, color=(0, 0, 0))

        # Fill date only if there's a clear blank date field (avoid overlapping format hints)
        fecha_hits = page.search_for("Fecha:")
        for hit in fecha_hits[:1]:
            # Only insert if the area after the label looks blank
            page.insert_text((hit.x1 + 5, hit.y1 + 1), today,
                             fontsize=9, color=(0, 0, 0))

        # Place signature image above "Firma de la persona"
        if not is_bcr_second_page:
            firma_hits = page.search_for("Firma de la persona")
            for hit in firma_hits[:1]:
                # Base size — capped to 90% of page width to avoid clipping
                max_w = w * 0.9
                sig_w = min(2768, max_w)
                sig_h = 1054 * (sig_w / 2768)

                # Landscape: 60% of base
                if is_landscape:
                    sig_w = sig_w * 0.6
                    sig_h = sig_h * 0.6
                
                # Center horizontally relative to the "Firma de la persona" text
                text_center_x = (hit.x0 + hit.x1) / 2
                
                # ANCHORING: The CSS line is at top:50% of the FULL viewport,
                # but the canvas is viewport - 72px (button bar). So strokes land at ~55% of canvas height.
                # PDF signature line is just above the text label (hit.y0 - 8).
                # Formula: bottom_anchor = pdf_line_y + sig_h * (1 - 0.55) = pdf_line_y + sig_h * 0.45
                pdf_line_y = hit.y0 - 3
                bottom_anchor = pdf_line_y + sig_h * 0.45
                
                sig_rect = fitz.Rect(
                    text_center_x - (sig_w / 2), 
                    bottom_anchor - sig_h, # Top
                    text_center_x + (sig_w / 2), 
                    bottom_anchor          # Bottom
                )
                page.insert_image(sig_rect, stream=sig_img_bytes)

    output = io.BytesIO()
    doc.save(output)
    doc.close()
    return output.getvalue()

    output = io.BytesIO()
    doc.save(output)
    doc.close()
    return output.getvalue()


def send_email_graph(token, nombre, cedula, attachments, asesor="No especificado", tipo_ingreso="No especificado"):
    """Send email via Microsoft Graph with PDF attachments."""
    attach_list = []
    for fname, content in attachments:
        attach_list.append({
            "@odata.type": "#microsoft.graph.fileAttachment",
            "name": fname,
            "contentType": "application/pdf" if fname.lower().endswith('.pdf') else ("image/png" if fname.lower().endswith('.png') else "image/jpeg"),
            "contentBytes": base64.b64encode(content).decode()
        })

    body = {
        "message": {
            "subject": f"SUGEF: {nombre}",
            "body": {
                "contentType": "Text",
                "content": (
                    f"Estimado equipo de Adelante Desarrollos,\n\n"
                    f"Se adjuntan las autorizaciones SUGEF firmadas digitalmente por:\n\n"
                    f"Nombre: {nombre}\n"
                    f"Cédula: {cedula}\n"
                    f"Asesor de Ventas: {asesor}\n"
                    f"Tipo de Ingreso: {tipo_ingreso}\n"
                    f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
                    f"Documentos adjuntos: {len(attachments)}\n\n"
                    f"Saludos,\nPortal de Firmas Adelante"
                )
            },
            "toRecipients": [{"emailAddress": {"address": e}} for e in DEST_EMAILS],
            "attachments": attach_list
        },
        "saveToSentItems": True
    }

    try:
        data = json.dumps(body).encode()
        req = urllib.request.Request(
            f'https://graph.microsoft.com/v1.0/me/sendMail',
            data=data,
            headers={
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            },
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 202
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode()
        print(f"Graph API Error: {e.code} {e.reason}")
        print(error_msg)
        # Log to a persistent file we can definitely read
        with open('/tmp/graph_error.log', 'w') as fe:
            fe.write(f"{e.code} {e.reason}\n{error_msg}")
        raise e





def send_email_smtp(nombre, cedula, attachments, asesor="No especificado", tipo_ingreso="No especificado"):
    """Send email via SMTP (Google Workspace/Gmail)."""
    if not (SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASS):
        raise RuntimeError("SMTP is not configured (missing SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASS)")

    msg = EmailMessage()
    msg['Subject'] = f"SUGEF: {nombre}"
    msg['From'] = SMTP_USER
    msg['To'] = ", ".join(DEST_EMAILS)
    msg.set_content(
        "Estimado equipo de Adelante Desarrollos,\n\n"
        "Se adjuntan las autorizaciones SUGEF firmadas digitalmente por:\n\n"
        f"Nombre: {nombre}\n"
        f"Cédula: {cedula}\n"
        f"Asesor de Ventas: {asesor}\n"
        f"Tipo de Ingreso: {tipo_ingreso}\n"
        f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
        f"Documentos adjuntos: {len(attachments)}\n\n"
        "Saludos,\nPortal de Firmas Adelante\n"
    )

    for fname, content in attachments:
        if fname.lower().endswith('.pdf'):
            maintype, subtype = 'application', 'pdf'
        elif fname.lower().endswith('.png'):
            maintype, subtype = 'image', 'png'
        else:
            maintype, subtype = 'image', 'jpeg'
        msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=fname)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    return True

def generate_summary_pdf(nombre, cedula, asesor, tipo_ingreso, photos_count):
    """Generates a summary PDF with the form data."""
    doc = fitz.open()
    page = doc.new_page()
    
    # Simple summary layout
    y = 50
    page.insert_text((50, y), "Resumen de Autorización SUGEF - Adelante Desarrollos", fontsize=16, color=(0.06, 0.23, 0.37))
    y += 40
    
    data = [
        ("Nombre Completo:", nombre),
        ("Cédula:", cedula),
        ("Asesor de Ventas:", asesor),
        ("Tipo de Ingreso:", tipo_ingreso),
        ("Documentos Adjuntos:", f"{photos_count} fotos/archivos"),
        ("Fecha de Envío:", datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
    ]
    
    for label, value in data:
        # Use standard fonts that are always available in PyMuPDF
        page.insert_text((50, y), label, fontsize=11, fontname="helv")
        page.insert_text((180, y), value, fontsize=11, fontname="helv")
        y += 25
        
    y += 20
    page.insert_text((50, y), "Este documento certifica que el cliente ha completado el formulario de autorización digital.", fontsize=10, color=(0.4, 0.4, 0.4))
    
    output = io.BytesIO()
    doc.save(output)
    doc.close()
    return output.getvalue()


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/submit', methods=['POST'])
def submit():
    try:
        data = request.get_json()
        nombre = data.get('nombre', '').strip()
        cedula = data.get('cedula', '').strip()
        asesor = data.get('asesor', '').strip() or "No especificado"
        tipo_ingreso = (data.get('tipoIngreso') or '').strip() or "No especificado"
        firma_b64 = data.get('firma', '')
        photos_list = data.get('photos', []) # List of b64 strings

        if not nombre or not cedula or not firma_b64:
            return jsonify({'ok': False, 'error': 'Faltan datos'}), 400

        # Decode signature PNG
        if ',' in firma_b64:
            firma_b64 = firma_b64.split(',')[1]
        firma_bytes = safe_b64decode(firma_b64)
        
        # Also compress signature image
        try:
            firma_bytes = compress_image(firma_bytes, max_size_kb=50, is_signature=True)
        except:
            pass

        # Fill each PDF
        attachments = []
        
        # Add Summary PDF first
        summary_pdf = generate_summary_pdf(nombre, cedula, asesor, tipo_ingreso, len(photos_list))
        attachments.append((f"{cedula}_Resumen_Formulario.pdf", summary_pdf))

        is_landscape = data.get('isLandscape', False)

        for doc_name, pdf_file in DOCS.items():
            pdf_path = os.path.join(PDF_DIR, pdf_file)
            if not os.path.exists(pdf_path):
                continue
            filled = fill_pdf(pdf_path, nombre, cedula, firma_bytes, is_landscape=is_landscape)
            # Convert each page to PNG and attach as images
            base_name = pdf_file.replace('_', ' ').replace('.pdf', '')
            tmp_doc = fitz.open(stream=filled, filetype="pdf")
            zoom = 200 / 72
            mat = fitz.Matrix(zoom, zoom)
            for page_num, page in enumerate(tmp_doc):
                pix = page.get_pixmap(matrix=mat, alpha=False)
                png_bytes = pix.tobytes("png")
                suffix = f"_p{page_num+1}" if len(tmp_doc) > 1 else ""
                clean_name = f"{cedula}_{base_name}{suffix}.png"
                attachments.append((clean_name, png_bytes))
            tmp_doc.close()

        # Attach multiple photos if provided
        for i, photo_obj in enumerate(photos_list):
            # photos_list might be a list of strings (backward compatibility) or list of objects
            if isinstance(photo_obj, dict):
                b64 = photo_obj.get('data', '')
                label = photo_obj.get('label', f'foto_{i+1}')
            else:
                b64 = photo_obj
                label = f'foto_{i+1}'

            if b64:
                if ',' in b64:
                    img_data = b64.split(',')[1]
                    mime_prefix = b64.split(',')[0]
                    # Ensure extension is simple and standard for Graph API content types
                    ext = 'pdf' if 'pdf' in mime_prefix else 'jpg'
                else:
                    img_data = b64
                    ext = 'jpg'
                id_bytes = safe_b64decode(img_data)
                
                # Compress images to avoid "IncomingBytes limit" from Microsoft Graph
                if ext != 'pdf':
                    try:
                        id_bytes = compress_image(id_bytes)
                        ext = 'jpg' # Force jpg after compression
                    except Exception as ce:
                        print(f"Compression failed for photo {i+1}: {ce}")

                # Remove accents/special chars from filename to be safe with Graph API
                safe_label = label.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
                attachments.append((f'{cedula}_{safe_label}_{i+1}.{ext}', id_bytes))

        # Save PDFs to disk for debugging
        tmp_dir = '/tmp/portal_pdfs'
        os.makedirs(tmp_dir, exist_ok=True)
        for clean_name, pdf_bytes in attachments:
            path = os.path.join(tmp_dir, clean_name)
            with open(path, 'wb') as f:
                f.write(pdf_bytes)

        # Send email (prefer SMTP if configured; fallback to Microsoft Graph)
        if SMTP_HOST and SMTP_USER and SMTP_PASS:
            ok = send_email_smtp(nombre, cedula, attachments, asesor=asesor, tipo_ingreso=tipo_ingreso)
        else:
            token = get_access_token()
            ok = send_email_graph(token, nombre, cedula, attachments, asesor=asesor, tipo_ingreso=tipo_ingreso)

        if ok:
            return jsonify({'ok': True, 'docs': len(attachments)})
        else:
            return jsonify({'ok': False, 'error': 'Error enviando email'}), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'ok': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(__import__('os').environ.get('PORT','5000')))
