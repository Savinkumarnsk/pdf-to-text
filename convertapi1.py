from flask import Flask, request, jsonify
import os
import tempfile
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract

app = Flask(__name__)

def extract_text_pymupdf(file_path):
    doc = fitz.open(file_path)
    extracted_text = ""

    for page in doc:
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: (b[1], b[0]))
        for block in blocks:
            extracted_text += block[4].strip() + "\n\n"

    doc.close()
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

        # Step 1: Try PyMuPDF
        text = extract_text_pymupdf(file_path)

        # Step 2: If PyMuPDF returns too little text, fallback to OCR
        if len(text.strip()) < 50:
            text = extract_text_ocr(file_path)

        os.remove(file_path)

        return jsonify({"data": text}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

