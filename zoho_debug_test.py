import smtplib
import ssl

EMAIL = "keys.bots@auramarkett.com"
PASS = "4H6zxc6N8WN8"  # or your latest Zoho app password

try:
    with smtplib.SMTP('smtp.zoho.com', 587, timeout=20) as server:
        server.set_debuglevel(2)
        print("🔌 EHLO:", server.ehlo())
        print("🔒 STARTTLS:", server.starttls(context=ssl.create_default_context()))
        print("🔁 EHLO again:", server.ehlo())
        print("🔐 Logging in...")
        server.login(EMAIL, PASS)
        print("✅ SUCCESS! Logged in and ready to send.")
except Exception as e:
    print(f"❌ FAILED:", str(e))

