from flask import Flask, request, jsonify, send_from_directory
import fitz  # PyMuPDF
import re
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS if frontend and backend are on different origins

UPLOAD_FOLDER = 'uploads'
EXTRACTED_FOLDER = 'extracted'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXTRACTED_FOLDER, exist_ok=True)

def extract_text_from_pdf(pdf_path):
    """Extract text from each page of the PDF."""
    document = fitz.open(pdf_path)
    text = ""
    for page_num in range(document.page_count):
        page = document.load_page(page_num)
        text += page.get_text()
    return text

def parse_transactions(text):
    """Parse transactions from the extracted text."""
    # Refined regex pattern based on the provided sample document
    transaction_pattern = re.compile(
        r'(\d{2}/\d{2})\s+([A-Za-z0-9\s\*\-&,]+?)\s+(-?\d+\.\d{2})'
    )
    transactions = []

    for match in transaction_pattern.findall(text):
        date, description, amount = match
        # Filter out invalid entries by ensuring the description does not contain certain patterns
        if any(substring in description for substring in ["- 0 -", "INTEREST CHARGES"]):
            continue
        transactions.append({
            "date": date,
            "description": description.strip(),
            "amount": float(amount),
        })

    return transactions

def format_transactions_as_text(transactions):
    """Format transactions as plain text."""
    lines = []
    for transaction in transactions:
        lines.append(f"Date: {transaction['date']}\nDescription: {transaction['description']}\nAmount: ${transaction['amount']:.2f}\n")
    return "\n".join(lines)

@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    app.logger.info('Received a request at /upload-pdf')
    
    if 'pdf' not in request.files:
        app.logger.error('No file part in the request')
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['pdf']
    if file.filename == '':
        app.logger.error('No selected file')
        return jsonify({'error': 'No selected file'}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    app.logger.info(f'Saving file to {file_path}')
    file.save(file_path)

    text = extract_text_from_pdf(file_path)
    app.logger.info(f'Extracted text from PDF:\n{text}')  # Log the extracted text

    transactions = parse_transactions(text)
    app.logger.info(f'Parsed Transactions: {transactions}')

    # Save transactions to a plain text file in the extracted folder
    txt_filename = os.path.splitext(file.filename)[0] + '.txt'
    txt_path = os.path.join(EXTRACTED_FOLDER, txt_filename)
    with open(txt_path, 'w') as txt_file:
        txt_file.write(format_transactions_as_text(transactions))
    app.logger.info(f'Saved parsed transactions to {txt_path}')
    
    return jsonify(transactions)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/extracted/<filename>')
def extracted_file(filename):
    return send_from_directory(EXTRACTED_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
