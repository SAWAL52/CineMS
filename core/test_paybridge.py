import os
from dotenv import load_dotenv
from pathlib import Path
from paybridge_np import PayBridgeNP, PayBridgeError, AuthenticationError

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

api_key = os.getenv("PAYBRIDGENP_API_KEY")

if not api_key:
    raise ValueError("PayBridge API key was not loaded")

client = PayBridgeNP(api_key=api_key)

try:
    session = client.checkout.create({
        "amount": 10000,  # NPR 100, in paisa
        "currency": "NPR",
        "returnUrl": "http://127.0.0.1:8000/payment/return/",
        "cancelUrl": "http://127.0.0.1:8000/payment/cancel/",
        "metadata": {
            "orderId": "TEST-001"
        },
        "customer": {
            "name": "Test Customer",
            "email": "test@example.com",
        },
    })

    print("Checkout session created!")
    print("Session ID:", session.get("id"))
    print("Checkout URL:", session["checkout_url"])

except AuthenticationError:
    print("Authentication failed. Check your API key.")

except PayBridgeError as e:
    print("PayBridge API error:", str(e))
    print("HTTP status:", e.status_code)

except Exception as e:
    print("Unexpected error:", type(e).__name__, str(e))
