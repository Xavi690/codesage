import os
import threading
import time
import requests
import razorpay
from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# ✅ Load .env from Render secret file path
load_dotenv("/etc/secrets/.env")

app = Flask(__name__)
CORS(app)

# ✅ Razorpay client setup with environment variables
razorpay_client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
)

# ✅ Store email per order
pending_orders = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_order', methods=['POST'])
def create_order():
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        # ✅ Create Razorpay order
        order = razorpay_client.order.create({
            "amount": 200,  # ₹109 in paise
            "currency": "INR",
            "payment_capture": 1
        })

        pending_orders[order['id']] = email
        print(f"✅ Created order: {order['id']} for {email}")

        return jsonify({
            "key": os.getenv("RAZORPAY_KEY_ID"),
            "amount": order['amount'],
            "order_id": order['id']
        })

    except Exception as e:
        print("❌ Error in /create_order:", e)
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/payment_webhook', methods=['POST'])
def payment_webhook():
    payload = request.get_data(as_text=True)
    signature = request.headers.get('X-Razorpay-Signature')

    try:
        # ✅ Verify webhook authenticity
        razorpay_client.utility.verify_webhook_signature(
            payload,
            signature,
            os.getenv("RAZORPAY_WEBHOOK_SECRET")
        )
    except razorpay.errors.SignatureVerificationError:
        print("❌ Invalid Razorpay signature.")
        return "Invalid signature", 400

    data = request.get_json()
    event = data.get('event')

    if event == "payment.captured":
        payment = data['payload']['payment']['entity']
        order_id = payment['order_id']
        email = pending_orders.get(order_id)

        if email:
            send_pdf(email)
            print(f"📧 PDF sent to {email}")
        else:
            print("⚠ Email not found for order:", order_id)

    return '', 200

def send_pdf(recipient_email):
    sender_email = os.getenv("EMAIL_USER")
    sender_password = os.getenv("EMAIL_PASS")

    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = recipient_email
    message['Subject'] = 'Your CodeSage Master Notes'

    body = 'Thank you for purchasing the premium notes. Find the attached PDF below.'
    message.attach(MIMEText(body, 'plain'))

    with open('master_notes.pdf', 'rb') as file:
        part = MIMEApplication(file.read(), _subtype='pdf')
        part.add_header('Content-Disposition', 'attachment', filename='master_notes.pdf')
        message.attach(part)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender_email, sender_password)
        server.send_message(message)

    print("✅ Email with PDF sent to", recipient_email)

# ✅ Self-ping function to prevent Render sleeping
def self_ping():
    while True:
        try:
            print("🔁 Self-pinging to keep app awake...")
            requests.get("https://codesage-kcd4.onrender.com/")
        except Exception as e:
            print("❌ Self-ping failed:", e)
        time.sleep(300)  # every 5 minutes

if __name__ == '__main__':
    # 🔁 Start background self-ping thread
    threading.Thread(target=self_ping, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    
