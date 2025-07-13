import os
import razorpay
from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from dotenv import load_dotenv

load_dotenv("/etc/secrets/secrets.env")

app = Flask(__name__)
CORS(app)

# Razorpay client
razorpay_client = razorpay.Client(
    auth=(os.getenv("RAZORPAY_KEY_ID"), os.getenv("RAZORPAY_KEY_SECRET"))
)

# Store order ID to email mapping
pending_orders = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_order', methods=['POST'])
def create_order():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    # Create Razorpay order
    order = razorpay_client.order.create({
        "amount": 10900,  # ₹109 in paise
        "currency": "INR",
        "payment_capture": 1
    })

    # Save order ID with email
    pending_orders[order['id']] = email

    return jsonify({
        "key": os.getenv("RAZORPAY_KEY_ID"),
        "amount": order['amount'],
        "order_id": order['id']
    })

@app.route('/payment_webhook', methods=['POST'])
def payment_webhook():
    payload = request.get_data(as_text=True)
    signature = request.headers.get('X-Razorpay-Signature')

    try:
        # ✅ SECURE: verify the webhook signature
        razorpay_client.utility.verify_webhook_signature(
            payload,
            signature,
            os.getenv("RAZORPAY_WEBHOOK_SECRET")  # You must set this in Render too!
        )
    except razorpay.errors.SignatureVerificationError:
        print("❌ Invalid Razorpay signature.")
        return "Invalid signature", 400

    data = request.get_json()
    event = data.get('event')

    if event == "payment.captured":
        payment = data['payload']['payment']['entity']
        order_id = payment['order_id']

        # Get email from pending orders
        email = pending_orders.get(order_id)
        if email:
            send_pdf(email)
            print(f" PDF sent to {email}")
        else:
            print("⚠ Email not found for order ID:", order_id)

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

    # Attach the PDF
    with open('master_notes.pdf', 'rb') as file:
        part = MIMEApplication(file.read(), _subtype='pdf')
        part.add_header('Content-Disposition', 'attachment', filename='master_notes.pdf')
        message.attach(part)

    # Send email using Gmail SMTP
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender_email, sender_password)
        server.send_message(message)

    print("📧 Email with PDF sent to", recipient_email)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
    
    
