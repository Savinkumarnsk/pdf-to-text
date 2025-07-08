#it gives in a need structure but it cant understand the tables in given pdf
from flask import Flask, request, send_file, jsonify
import os
import tempfile
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract
from PIL import Image, ImageFilter, ImageOps
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- PyMuPDF: Best for Digital PDFs ---
def extract_text_pymupdf(file_path):
    try:
        doc = fitz.open(file_path)
        extracted_text = ""

        for page in doc:
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: (b[1], b[0]))  # Top-to-bottom, left-to-right
            for block in blocks:
                extracted_text += block[4].strip() + "\n\n"

        doc.close()
        return extracted_text.strip()

    except Exception as e:
        logging.error(f"[PyMuPDF] Extraction failed: {e}")
        return ""

# --- Preprocess Image for OCR ---
def preprocess_image(image):
    image = image.convert('L')  # Grayscale
    image = ImageOps.autocontrast(image)
    image = image.filter(ImageFilter.MedianFilter(size=3))
    return image

# --- OCR: Best for Scanned PDFs ---
def extract_text_ocr(file_path):
    try:
        images = convert_from_path(file_path, dpi=300)
        extracted_text = ""

        for img in images:
            preprocessed = preprocess_image(img)
            text = pytesseract.image_to_string(preprocessed, lang='eng', config='--oem 3 --psm 6')
            extracted_text += text + "\n\n"

        return extracted_text.strip()

    except Exception as e:
        logging.error(f"[OCR] Extraction failed: {e}")
        return ""

# --- Flask Endpoint ---
@app.route('/convert-pdf-to-textfile', methods=['POST'])
def convert_pdf_to_txt_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    try:
        # Save PDF temporarily
        temp_dir = tempfile.gettempdir()
        pdf_path = os.path.join(temp_dir, file.filename)
        file.save(pdf_path)

        # Extract text using PyMuPDF or OCR
        text = extract_text_pymupdf(pdf_path)
        if len(text.strip()) < 50:
            logging.info("[Fallback] Switching to OCR...")
            text = extract_text_ocr(pdf_path)

        # Save to .txt file
        txt_filename = os.path.splitext(file.filename)[0] + ".txt"
        txt_path = os.path.join(temp_dir, txt_filename)

        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text)

        # Send the .txt file as download
        return send_file(txt_path, as_attachment=True)

    except Exception as e:
        logging.error(f"[Error] {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except:
            pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
