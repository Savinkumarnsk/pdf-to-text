from flask import Flask, request, send_file, jsonify
import os
import tempfile
import fitz  # PyMuPDF
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from PIL import Image


app = Flask(__name__)

def extract_text_with_tables(file_path):
    extracted_text = ""

    # Extract text and tables using pdfplumber
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            # Extract text
            text = page.extract_text()
            if text:
                extracted_text += text + "\n\n"

            # Extract tables
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    extracted_text += '\t'.join([cell if cell else '' for cell in row]) + '\n'
                extracted_text += '\n'

    return extracted_text.strip()

def preprocess_image(image):
    gray = image.convert('L')  # Grayscale
    bw = gray.point(lambda x: 0 if x < 180 else 255, '1')  # Binarization
    return bw

def extract_text_ocr(file_path):
    images = convert_from_path(file_path, dpi=300)
    extracted_text = ""

    for image in images:
        processed_image = preprocess_image(image)
        text = pytesseract.image_to_string(processed_image)
        extracted_text += text + "\n\n"

    return extracted_text.strip()

def smart_text_extraction(file_path):
    text = extract_text_with_tables(file_path)

    # If text is too small, assume it's an image PDF and fallback to OCR
    if len(text.strip()) < 50:
        text = extract_text_ocr(file_path)

    return text.strip()

@app.route('/extract-pdf-text', methods=['POST'])
def extract_pdf_text():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        temp_dir = tempfile.gettempdir()
        pdf_file_path = os.path.join(temp_dir, file.filename)
        file.save(pdf_file_path)

        text = smart_text_extraction(pdf_file_path)

        if not text.strip():
            os.remove(pdf_file_path)
            return jsonify({"error": "No text could be extracted"}), 400

        # Save extracted text to a .txt file
        text_file_path = os.path.join(temp_dir, f"{os.path.splitext(file.filename)[0]}.txt")
        with open(text_file_path, 'w', encoding='utf-8') as f:
            f.write(text)

        os.remove(pdf_file_path)  # Clean up uploaded PDF

        return send_file(text_file_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

