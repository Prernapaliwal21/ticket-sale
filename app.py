from flask import Flask, render_template, request, jsonify , make_response
import os
import razorpay
import random
import time
import hmac
import hashlib
import qrcode
import json
from io import BytesIO
import base64
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from datetime import datetime
import uuid
import secrets
from pymongo import MongoClient
from weasyprint import HTML


app = Flask(__name__)

# Configuration
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_your_key_id_here")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "your_key_secret_here")
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# MongoDB connection
mongo_client = MongoClient("mongodb://localhost:27017/")  # update if needed
db = mongo_client["festival_booking"]
logins_collection = db["logins"]
tickets_collection = db["tickets"]
users_collection = db["users"]

TICKET_PRICE_INR = 100
MAX_TICKETS = 10


admin_sessions = {}


def generate_qr_token():
    return str(uuid.uuid4()) + "-" + str(int(time.time()))


def create_qr_code(ticket_data):
    qr_data = {
        "ticket_id": ticket_data["ticket_id"],
        "qr_token": ticket_data["qr_token"],
        "name": ticket_data["name"],
        "event": "Mona Squad Festival 2025",
        "timestamp": str(int(time.time())),
    }
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(json.dumps(qr_data))
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()


def generate_pdf_tickets(tickets_data):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    title = Paragraph(
        "<b>Mona Squad Festival 2025 - Entry Tickets</b>", styles["Title"]
    )
    story.append(title)
    story.append(Spacer(1, 20))

    for i, ticket in enumerate(tickets_data, 1):
        ticket_header = Paragraph(
            f"<b>Ticket #{i} - ID: {ticket['ticket_id']}</b>", styles["Heading2"]
        )
        story.append(ticket_header)
        story.append(Spacer(1, 10))

        details = f"""
<b>Event:</b> Mona Squad Festival 2025<br/>
<b>Name:</b> {ticket["name"]}<br/>
<b>Phone:</b> {ticket["phone"]}<br/>
<b>Price:</b> Rs.{ticket["price_per_ticket"]}<br/>
<b>Generated:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}<br/>
<b>Valid:</b> Single Entry Only<br/>
"""
        details_para = Paragraph(details, styles["Normal"])
        story.append(details_para)
        story.append(Spacer(1, 15))

        qr_img_data = base64.b64decode(ticket["qr_code"])
        qr_img_buffer = BytesIO(qr_img_data)
        qr_image = Image(qr_img_buffer, width=200, height=200)

        story.append(qr_image)
        story.append(Spacer(1, 30))

        if i < len(tickets_data):
            story.append(PageBreak())

    doc.build(story)
    buffer.seek(0)
    return buffer


@app.route("/")
def index():
    return render_template(
        "index.html",
        razorpay_key_id=RAZORPAY_KEY_ID,
        price=TICKET_PRICE_INR,
        max_tickets=MAX_TICKETS,
    )


@app.route("/create-order", methods=["POST"])
def create_order():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    quantity = int(data.get("quantity") or 1)

    total_amount = TICKET_PRICE_INR * quantity * 100
    order_data = {
        "amount": total_amount,
        "currency": "INR",
        "receipt": f"MONA_{int(time.time())}_{random.randint(1000, 9999)}",
        "notes": {
            "name": name,
            "phone": phone,
            "quantity": str(quantity),
        },
    }
    order = razorpay_client.order.create(data=order_data)

    return jsonify(
        {
            "order_id": order["id"],
            "amount": order["amount"],
            "currency": order["currency"],
            "name": name,
            "phone": phone,
            "quantity": quantity,
        }
    )


@app.route("/success")
def success():
    payment_id = request.args.get("payment_id")
    order_id = request.args.get("order_id")

    tickets = list(tickets_collection.find({"payment_id": payment_id}, {"_id": 0}))
    if not tickets:
        return "Invalid payment or tickets not found", 400

    total_amount = len(tickets) * TICKET_PRICE_INR

    return render_template(
        "success.html",
        tickets=tickets,
        payment_id=payment_id,
        order_id=order_id,
        quantity=len(tickets),
        price=TICKET_PRICE_INR,
        total=total_amount,
    )


@app.route("/verify-payment", methods=["POST"])
def verify_payment():
    data = request.get_json(force=True)
    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_signature = data.get("razorpay_signature")

    generated_signature = hmac.new(
        RAZORPAY_KEY_SECRET.encode("utf-8"),
        f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    payment = razorpay_client.payment.fetch(razorpay_payment_id)
    if payment.get("status") != "captured":
        # ❌ Payment not completed
        return jsonify({"success": False, "redirect_url": "/"})
    
    
    if generated_signature != razorpay_signature:
        return jsonify({"success": False, "error": "Signature mismatch"}), 400

    order = razorpay_client.order.fetch(razorpay_order_id)
    quantity = int(order["notes"].get("quantity", "1"))
    name = order["notes"].get("name", "Guest")
    phone = order["notes"].get("phone", "N/A")

    tickets = []
    for i in range(quantity):
        ticket_id = f"MONA-{datetime.now().strftime('%Y%m%d')}-{random.randint(10000, 99999)}-{i + 1:02d}"
        qr_token = generate_qr_token()

        ticket_data = {
            "ticket_id": ticket_id,
            "qr_token": qr_token,
            "name": name,
            "phone": phone,
            "price_per_ticket": TICKET_PRICE_INR,
            "payment_id": razorpay_payment_id,
            "order_id": razorpay_order_id,
            "created_at": datetime.now().isoformat(),
            "is_scanned": False,
        }
        ticket_data["qr_code"] = create_qr_code(ticket_data)
        tickets.append(ticket_data)

    # ✅ Save tickets in MongoDB
    tickets_collection.insert_many(tickets)


    redirect_url = (
        f"/success?payment_id={razorpay_payment_id}&order_id={razorpay_order_id}"
    )

    for t in tickets:
        if "_id" in t:
            t["_id"] = str(t["_id"])  # or just delete: del t["_id"]

    return jsonify({"success": True, "tickets": tickets, "redirect_url": redirect_url})


@app.route("/admin/validate-qr", methods=["POST"])
def admin_validate_qr():
    data = request.get_json(force=True)
    qr_data = data.get("qr_data", "").strip()
    admin_token = data.get("admin_token", "")

    if admin_token not in admin_sessions:
        return jsonify({"valid": False, "message": "Unauthorized"}), 401

    try:
        decoded_qr = json.loads(qr_data)
    except json.JSONDecodeError:
        return jsonify({"valid": False, "message": "Invalid QR code format"})

    if "qr_token" not in decoded_qr:
        return jsonify({"valid": False, "message": "QR token missing"})

    print(decoded_qr)  # For debugging
    ticket_found = tickets_collection.find_one({"qr_token": decoded_qr["qr_token"]}, {"_id": 0})
    print(ticket_found)  # For debugging
    if not ticket_found:
        return jsonify({"valid": False, "message": "Invalid QR - Not Found"})


    if ticket_found.get("is_scanned"):
        return jsonify(
            {
                "valid": False,
                "message": "DUPLICATE - Already scanned",
                "ticket_id": ticket_found["ticket_id"],
                "holder_name": ticket_found["name"],
            }
        )

    tickets_collection.update_one(
        {"ticket_id": ticket_found["ticket_id"]},
        {"$set": {"is_scanned": True, "scanned_at": datetime.now().isoformat()}}
    )


    return jsonify(
        {
            "valid": True,
            "message": "ENTRY APPROVED",
            "ticket_details": {
                "ticket_id": ticket_found["ticket_id"],
                "name": ticket_found["name"],
                "phone": ticket_found["phone"],
                "price_paid": f"Rs.{ticket_found['price_per_ticket']}",
                "entry_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
        }
    )


@app.route('/download-pdf/<payment_id>')
def download_pdf(payment_id):
    tickets = list(tickets_collection.find({"payment_id": payment_id}, {"_id": 0}))
    if not tickets:
        return "No tickets found", 404

    # Render ticket-only template
    html_content = render_template("tickets_pdf.html", tickets=tickets)

    pdf = HTML(string=html_content, base_url=request.host_url).write_pdf()

    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=tickets_{payment_id}.pdf'
    return response
    

@app.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json(force=True)
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    user = users_collection.find_one(
        {"email": email, "password": password, "role": "admin"}
    )

    if user:
        token = secrets.token_hex(32)
        admin_sessions[token] = {"created_at": datetime.now(), "active": True}

        logins_collection.insert_one({
            "user_type": "admin",
            "email": email,
            "session_token": token,
            "login_time": datetime.now()
        })

        return jsonify({"success": True, "token": token})
    else:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401




@app.route("/admin/logins")
def admin_logins():
    logs = list(logins_collection.find({}, {"_id": 0}))
    return jsonify(logs)


@app.route("/admin/stats")
def admin_stats():
    total_tickets = tickets_collection.count_documents({})
    tickets_scanned = tickets_collection.count_documents({"is_scanned": True})
    pending_entries = total_tickets - tickets_scanned
    total_revenue = total_tickets * TICKET_PRICE_INR

    return jsonify(
        {
            "total_tickets_sold": total_tickets,
            "tickets_scanned": tickets_scanned,
            "pending_entries": pending_entries,
            "total_revenue": total_revenue,
        }
    )


@app.route("/admin/scanner")
def admin_scanner():
    return render_template("admin_scanner.html")


@app.route("/scanner")
def scanner():
    return render_template("scanner.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
