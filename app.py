from flask import Flask, request, render_template, redirect
import json, uuid, hashlib, base64
import smtplib
from email.message import EmailMessage
import requests

app = Flask(__name__)

# 🔧 Replace with real values
PHONEPE_MERCHANT_ID = "YOUR_MERCHANT_ID"
PHONEPE_SALT_KEY = "YOUR_SALT_KEY"
PHONEPE_HOST = "https://api.phonepe.com/apis/hermes"
REDIRECT_URL = "http://localhost:5000/callback"
WEBHOOK_URL = "http://localhost:5000/webhook"  # Optional

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pay', methods=['POST'])
def pay():
    email = request.form['email']
    txn_id = str(uuid.uuid4())

    payload = {
        "merchantId": PHONEPE_MERCHANT_ID,
        "merchantTransactionId": txn_id,
        "merchantUserId": email,
        "amount": 9900,
        "redirectUrl": REDIRECT_URL,
        "redirectMode": "POST",
        "callbackUrl": WEBHOOK_URL,
        "paymentInstrument": {
            "type": "PAY_PAGE"
        }
    }

    payload_str = base64.b64encode(json.dumps(payload).encode()).decode()
    checksum_str = f"{payload_str}/pg/v1/pay{PHONEPE_SALT_KEY}"
    x_verify = hashlib.sha256(checksum_str.encode()).hexdigest() + "###1"

    headers = {
        "Content-Type": "application/json",
        "X-VERIFY": x_verify
    }

    res = requests.post(f"{PHONEPE_HOST}/pg/v1/pay", json={"request": payload_str}, headers=headers)
    response = res.json()

    if response.get("success"):
        redirect_url = response["data"]["instrumentResponse"]["redirectInfo"]["url"]
        return redirect(redirect_url)
    else:
        return "Error creating PhonePe payment."

@app.route('/callback', methods=['POST'])
def callback():
    email = request.form.get("merchantUserId")
    send_pdf_to_customer(email)
    return "Payment successful! Your notes have been emailed."

def send_pdf_to_customer(email):
    msg = EmailMessage()
    msg['Subject'] = 'Your CodeSage Master Notes'
    msg['From'] = 'youremail@gmail.com'
    msg['To'] = email
    msg.set_content('Dear Student,\n\nThank you for your payment. Please find your PDF notes attached.\n\n— Team CodeSage')

    with open("master_notes.pdf", "rb") as f:
        msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename='master_notes.pdf')

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login("xavitimes1@gmail.com",
                    "hwyfiltzsbrhmyri")
        smtp.send_message(msg)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
    