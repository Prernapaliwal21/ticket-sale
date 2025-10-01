"""
Script to generate tickets without payment and create PDFs using the same HTML template as in Flask app.
"""

import os
import uuid
import random
import json
from datetime import datetime
from pymongo import MongoClient
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import qrcode
import time
from io import BytesIO
import base64
from flask import Flask

# Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb+srv://paliwalp353_db_user:AVJJDdrC8f8bwehx@ticket-sale.18tiuy4.mongodb.net/festival_booking?retryWrites=true&w=majority&tls=true")
MONGO_DB = os.getenv("MONGO_DB", "festival_booking")
REG_COLLECTION = os.getenv("REG_COLLECTION", "registrations")
TICKET_PRICE_INR = int(os.getenv("TICKET_PRICE_INR", 200))
GST_RATE = float(os.getenv("GST_RATE", 3.0))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./generated_pdfs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# MongoDB connection
mongo_client = MongoClient(MONGO_URL, tls=True, tlsAllowInvalidCertificates=False)
db = mongo_client[MONGO_DB]
tickets_collection = db[REG_COLLECTION]

# Jinja2 environment (assumes Flask templates directory structure)
template_dir = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(loader=FileSystemLoader(template_dir))
ticket_template = env.get_template("tickets_pdf.html")

# Flask app for context
app = Flask(__name__)


def generate_qr_token():
    return str(uuid.uuid4()) + "-" + str(int(datetime.now().timestamp()))


def create_qr_code(ticket_data):
    qr_data = {
        "registration_id": ticket_data["registration_id"],
        "qr_token": ticket_data["qr_token"],
        "name": ticket_data["name"],
        "event": "Mona Squad Dandiya Festival 2025",
        "timestamp": str(int(time.time())),
    }
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(json.dumps(qr_data))
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()


def create_registrations(name, num_tickets):
    registrations = []
    gst_per_ticket = round(TICKET_PRICE_INR * (GST_RATE / 100), 2)
    price_per_ticket = round(TICKET_PRICE_INR + gst_per_ticket, 2)
    for i in range(num_tickets):
        registration_id = f"MONA-{datetime.now().strftime('%Y%m%d')}-{random.randint(10000,99999)}-{i+1:02d}"
        qr_token = generate_qr_token()
        ticket_data = {
            "registration_id": registration_id,
            "qr_token": qr_token,
            "name": name,
            "phone": "N/A",
            "price_per_ticket": price_per_ticket,
            "payment_id": f"NOPAY-{uuid.uuid4().hex[:12]}",
            "order_id": f"NOPAY-{uuid.uuid4().hex[:12]}",
            "created_at": datetime.now().isoformat(),
            "is_scanned": False
        }
        ticket_data["qr_code"] = create_qr_code(ticket_data)
        registrations.append(ticket_data)
    return registrations


def insert_registrations(registrations):
    tickets_collection.insert_many(registrations)


def generate_pdf(registrations, output_path):
    import base64

    # Read and encode logo as base64
    logo_file = os.path.join(os.path.dirname(__file__), 'static/images', 'mona-squad-logo.png')
    with open(logo_file, 'rb') as f:
        logo_base64 = base64.b64encode(f.read()).decode()

    # Use Flask app context to render_template
    with app.app_context():
        from flask import render_template
        html_content = render_template(
            "ticket_pdf_migration.html",
            registrations=registrations,
            logo_base64=logo_base64
        )

    pdf = HTML(string=html_content).write_pdf()
    with open(output_path, "wb") as f:
        f.write(pdf)

    print(f"PDF generated: {output_path}")



def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate ticket PDFs without payment")
    parser.add_argument("--name", required=True, help="Name for tickets")
    parser.add_argument("--max-per-pdf", type=int, default=5, help="Max tickets per PDF")
    parser.add_argument("--num-pdfs", type=int, default=1, help="Number of PDFs to generate")
    args = parser.parse_args()

    all_regs = []
    for pdf_index in range(1, args.num_pdfs + 1):
        regs = create_registrations(args.name, args.max_per_pdf)
        insert_registrations(regs)
        output_file = os.path.join(OUTPUT_DIR, f"tickets_{regs[0]['order_id']}_part_{pdf_index}.pdf")
        generate_pdf(regs, output_file)
        all_regs.extend(regs)

    print(f"Total registrations created: {len(all_regs)}")


if __name__ == "__main__":
    main()