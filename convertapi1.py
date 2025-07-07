from flask import Flask, request, jsonify
import os
import tempfile
import pdfplumber
from pdf2image import convert_from_path
import pytesseract

app = Flask(__name__)

def extract_text_with_tables(file_path):
    extracted_text = ""

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            # Extract plain text
            page_text = page.extract_text()
            if page_text:
                extracted_text += page_text + "\n\n"

            # Extract tables
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    extracted_text += "\t".join([cell if cell else '' for cell in row]) + "\n"
                extracted_text += "\n"

    return extracted_text.strip()

def extract_text_ocr(file_path):
    images = convert_from_path(file_path)
    extracted_text = ""

    for image in images:
        text = pytesseract.image_to_string(image)
        extracted_text += text + "\n\n"

    return extracted_text.strip()

@app.route('/extract-pdf-text', methods=['POST'])
def extract_pdf_text():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    try:
        temp_dir = tempfile.gettempdir()
        file_path = os.path.join(temp_dir, file.filename)
        file.save(file_path)

        # Step 1: Try pdfplumber
        text = extract_text_with_tables(file_path)

        # Step 2: If very little text found, fallback to OCR
        if len(text.strip()) < 50:
            text = extract_text_ocr(file_path)

        os.remove(file_path)

        return jsonify({"data": text}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
