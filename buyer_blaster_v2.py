import smtplib
import ssl
import base64
from email.mime.text import MIMEText

# CONFIG
ZOHO_EMAIL = "keys.bots@auramarkett.com"
ZOHO_PASS = "4H6zxc6N8WN8"
SMTP_SERVER = "smtp.zoho.com"
SMTP_PORT = 587

# Sample buyers
buyers = [
    {"email": "examplebuyer1@gmail.com", "criteria": "Miami"},
    {"email": "examplebuyer2@gmail.com", "criteria": "Orlando"},
]

# Sample property
property_info = {
    "location": "Miami",
    "price": "$250,000",
    "beds": 3,
    "baths": 2,
    "link": "https://yourdeal.com/property/123"
}

def send_email(to, subject, body):
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) as server:
            server.set_debuglevel(2)
            print("🔌 Connecting and starting EHLO...")
            print("EHLO response:", server.ehlo())

            print("🔒 Starting TLS...")
            print("STARTTLS response:", server.starttls(context=context))

            print("🔁 Post-TLS EHLO...")
            print("Post-TLS EHLO:", server.ehlo())

            print("🔐 Authenticating with AUTH PLAIN...")
            auth_string = base64.b64encode(f"\0{ZOHO_EMAIL}\0{ZOHO_PASS}".encode()).decode()
            code, response = server.docmd("AUTH PLAIN", auth_string)
            if code != 235:
                raise smtplib.SMTPAuthenticationError(code, response)

            msg = MIMEText(body)
            msg['From'] = ZOHO_EMAIL
            msg['To'] = to
            msg['Subject'] = subject

            print(f"📨 Sending email to {to}...")
            server.sendmail(ZOHO_EMAIL, to, msg.as_string())
            print(f"✅ Email successfully sent to {to}")
            return True

    except Exception as e:
        print(f"❌ Email send failed: {e}")
        return False

def match_buyers():
    for buyer in buyers:
        if buyer["criteria"].lower() in property_info["location"].lower():
            message = (
                f"🗺️ New Property Match!\n\n"
                f"Location: {property_info['location']}\n"
                f"Price: {property_info['price']}\n"
                f"Beds: {property_info['beds']}, Baths: {property_info['baths']}\n"
                f"Link: {property_info['link']}\n\n"
                f"🔑 Let us know if you're interested!"
            )
            send_email(buyer['email'], "🔥 New Property Match!", message)

if __name__ == "__main__":
    match_buyers()

