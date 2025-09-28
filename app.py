from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid

app = Flask(__name__)
CORS(app)

# Add root route for GET requests

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "message": "Patient Scheme API running"})

@app.route("/generate-card", methods=["POST"])
def generate_card():
    """
    Endpoint to generate a utility card with scheme logic.
    Input: JSON { "family_name": "", "address": "", "income": 0, "scheme": "Silver/Gold/Platinum" }
    Output: JSON with card details
    """
    data = request.json
    income = data.get("income", 0)

    # Business logic: assign scheme
    if income < 100000:
        scheme = "Silver"
        fee = 0
    else:
        scheme = data.get("scheme", "Silver")
        fee = {"Silver": 250, "Gold": 500, "Platinum": 1000}[scheme]

    # Generate unique card number
    card_number = str(uuid.uuid4())[:8]

    result = {
        "family_name": data.get("family_name"),
        "address": data.get("address"),
        "income": income,
        "scheme": scheme,
        "fee": fee,
        "card_number": card_number,
        "discount": {"Silver": "5%", "Gold": "10%", "Platinum": "15%"}[scheme]
    }

    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)
