# utils.py
import os
import uuid
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()  # read .env

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your .env")

# Create Supabase client using service role key (server-side)
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def _resp_data(resp):
    """Helper to standardize supabase-py responses."""
    # supabase-py response objects often have .data and .error attributes
    try:
        data = getattr(resp, "data", None)
        error = getattr(resp, "error", None)
        if data is not None or error is not None:
            return {"data": data, "error": error}
    except Exception:
        pass
    # fallback
    try:
        return dict(resp)
    except Exception:
        return {"raw": str(resp)}


### AUTH helpers

def register_user(email: str, password: str, user_metadata: dict | None = None):
    """
    Register user via Supabase Auth.
    Returns supabase response (data / error).
    """
    body = {"email": email, "password": password}
    if user_metadata:
        # pass as options.data per supabase docs
        body["options"] = {"data": user_metadata}
    resp = supabase.auth.sign_up(body)
    return _resp_data(resp)


def login_user(email: str, password: str):
    """
    Sign in user (email + password). Returns session & user details (if success).
    """
    resp = supabase.auth.sign_in_with_password({"email": email, "password": password})
    return _resp_data(resp)


def send_password_reset(email: str, redirect_to: str | None = None):
    """
    Send password reset email. 'redirect_to' optional.
    """
    if redirect_to:
        resp = supabase.auth.reset_password_for_email(email, {"redirect_to": redirect_to})
    else:
        resp = supabase.auth.reset_password_for_email(email)
    return _resp_data(resp)


def get_user_from_token(access_token: str):
    """Validate access token and return user object (or None)."""
    try:
        # supabase.auth.get_user accepts a JWT (access token)
        resp = supabase.auth.get_user(access_token)
        parsed = _resp_data(resp)
        # parsed['data'] likely contains {'user': {...}} or directly user
        return parsed
    except Exception as e:
        return {"error": str(e)}


### FAMILY / MEMBER CRUD

def _generate_card_number():
    return f"CARD-{uuid.uuid4().hex[:10].upper()}"


def create_family(user_id: str, family_name: str, address: str, annual_income: int,
                  members: list[dict], chosen_scheme: str | None = None):
    """
    Insert family and members. Applies business rule:
      - if annual_income < 100000 => scheme_type = 'Silver' (free)
      - else use chosen_scheme if provided, otherwise 'Silver'.
    Returns created family record and inserted member records.
    """
    # apply scheme logic
    if annual_income < 100000:
        scheme = "Silver"
    else:
        scheme = chosen_scheme if chosen_scheme in ("Silver", "Gold", "Platinum") else "Silver"

    card_number = _generate_card_number()

    # insert family
    family_payload = {
        "user_id": user_id,
        "family_name": family_name,
        "address": address,
        "annual_income": annual_income,
        "scheme_type": scheme,
        "card_number": card_number,
    }
    fam_resp = supabase.table("families").insert(family_payload).execute()
    fam_parsed = _resp_data(fam_resp)
    if fam_parsed.get("error"):
        return {"error": fam_parsed["error"]}

    # extract inserted family id
    family_rows = fam_parsed.get("data")
    if not family_rows:
        return {"error": "Family insert returned no data."}
    family_record = family_rows[0]
    family_id = family_record.get("id")

    # insert members if provided
    member_rows = []
    if members:
        # each member dict: {name, relation, age}
        to_insert = []
        for m in members:
            to_insert.append({
                "family_id": family_id,
                "name": m.get("name"),
                "relation": m.get("relation"),
                "age": m.get("age"),
            })
        mem_resp = supabase.table("family_members").insert(to_insert).execute()
        mem_parsed = _resp_data(mem_resp)
        if mem_parsed.get("error"):
            return {"error": mem_parsed["error"]}
        member_rows = mem_parsed.get("data")

    return {"family": family_record, "members": member_rows}


def get_families_for_user(user_id: str):
    """
    Return families with nested members for the user.
    Uses a referenced select: "*, family_members(*)"
    """
    resp = supabase.table("families").select("*, family_members(*)").eq("user_id", user_id).execute()
    return _resp_data(resp)


def update_family(family_id: int, updates: dict):
    resp = supabase.table("families").update(updates).eq("id", family_id).execute()
    return _resp_data(resp)


def update_member(member_id: int, updates: dict):
    resp = supabase.table("family_members").update(updates).eq("id", member_id).execute()
    return _resp_data(resp)


def delete_member(member_id: int):
    resp = supabase.table("family_members").delete().eq("id", member_id).execute()
    return _resp_data(resp)
