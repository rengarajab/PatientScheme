# app.py
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import utils

load_dotenv()

app = Flask(__name__)
CORS(app)  # enable CORS for Lovable frontends (adjust origins in production)


def _get_bearer_token():
    auth = request.headers.get("Authorization", "")
    if not auth:
        return None
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def require_auth():
    """Helper to extract user info from Authorization header; returns (user_id, error)"""
    token = _get_bearer_token()
    if not token:
        return None, ("Missing Authorization Bearer token", 401)
    user_parsed = utils.get_user_from_token(token)
    if user_parsed.get("error"):
        return None, (user_parsed["error"], 401)
    # user_parsed['data'] may be { 'user': {...} } depending on the SDK
    data = user_parsed.get("data")
    if isinstance(data, dict) and data.get("user"):
        user = data["user"]
    else:
        # sometimes get_user returns {'id':..., ...} under data directly; try common shapes:
        user = data if isinstance(data, dict) else None

    if not user:
        return None, ("Invalid token / could not resolve user", 401)
    user_id = user.get("id") or user.get("user", {}).get("id")
    if not user_id:
        # fallback: try data['id']
        user_id = data.get("id") if isinstance(data, dict) else None
    if not user_id:
        return None, ("Unable to determine user id", 401)
    return user_id, None


@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "message": "Patient Scheme API running"})


# AUTH routes ------------------------------------------------

@app.route("/register", methods=["POST"])
def register():
    body = request.get_json(force=True)
    email = body.get("email")
    password = body.get("password")
    name = body.get("name")
    if not email or not password:
        return jsonify({"error": "email & password required"}), 400
    resp = utils.register_user(email, password, user_metadata={"name": name} if name else None)
    return jsonify(resp)


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(force=True)
    email = body.get("email")
    password = body.get("password")
    if not email or not password:
        return jsonify({"error": "email & password required"}), 400
    resp = utils.login_user(email, password)
    return jsonify(resp)


@app.route("/forgot-password", methods=["POST"])
def forgot_password():
    body = request.get_json(force=True)
    email = body.get("email")
    redirect_to = body.get("redirect_to")  # optional
    if not email:
        return jsonify({"error": "email required"}), 400
    resp = utils.send_password_reset(email, redirect_to)
    return jsonify(resp)


# FAMILY endpoints (protected) --------------------------------

@app.route("/create-family", methods=["POST"])
def create_family():
    user_id, err = require_auth()
    if err:
        return jsonify({"error": err[0]}), err[1]
    body = request.get_json(force=True)
    family_name = body.get("family_name")
    address = body.get("address", "")
    annual_income = int(body.get("annual_income", 0))
    members = body.get("members", [])  # list of {name, relation, age}
    chosen_scheme = body.get("chosen_scheme")
    if not family_name:
        return jsonify({"error": "family_name required"}), 400

    res = utils.create_family(user_id, family_name, address, annual_income, members, chosen_scheme)
    if res.get("error"):
        return jsonify({"error": res["error"]}), 400
    return jsonify(res)


@app.route("/families", methods=["GET"])
def get_families():
    user_id, err = require_auth()
    if err:
        return jsonify({"error": err[0]}), err[1]
    res = utils.get_families_for_user(user_id)
    return jsonify(res)


@app.route("/family/<int:family_id>", methods=["PUT"])
def update_family(family_id):
    user_id, err = require_auth()
    if err:
        return jsonify({"error": err[0]}), err[1]
    updates = request.get_json(force=True)
    # optional: ensure the family belongs to user (additional security check)
    # implement a check if needed
    res = utils.update_family(family_id, updates)
    return jsonify(res)


@app.route("/member/<int:member_id>", methods=["PUT"])
def update_member(member_id):
    user_id, err = require_auth()
    if err:
        return jsonify({"error": err[0]}), err[1]
    updates = request.get_json(force=True)
    res = utils.update_member(member_id, updates)
    return jsonify(res)


@app.route("/member/<int:member_id>", methods=["DELETE"])
def remove_member(member_id):
    user_id, err = require_auth()
    if err:
        return jsonify({"error": err[0]}), err[1]
    res = utils.delete_member(member_id)
    return jsonify(res)


if __name__ == "__main__":
    # run with: python app.py
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
