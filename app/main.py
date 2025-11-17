"""
main.py - ThriftKids backend

Features:
- Upload image to GCS
- Store listing metadata in Firestore
- Optional AI-generated description via Gemini (Vertex model) using API key
- BigQuery lightweight event logging (optional)
- Manual description field preferred; AI used only when description is blank and USE_AGENT=true

Environment variables:
- VERTEX_API_KEY   (optional; keep secret; used for Gemini calls)
- GCP_PROJECT      (optional; used by google-cloud clients)
- BUCKET_NAME      (optional; required to store images in GCS)
- BQ_DATASET       (optional; default thriftkids_analytics)
- BQ_TABLE         (optional; default events)
- USE_AGENT        (optional; "true" or "false"; default true)
"""
import os
import json
import uuid
from datetime import datetime
from typing import Optional

from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# Load local .env for development (do NOT commit .env)
load_dotenv()

# Optional Google libraries — only required if using GCS/Firestore/BigQuery
try:
    from google.cloud import storage, firestore, bigquery
    import google.auth
    import google.auth.transport.requests
    GCLOUD_AVAILABLE = True
except Exception:
    GCLOUD_AVAILABLE = False

import requests

# ----------
# Configuration via env
# ----------
VERTEX_API_KEY = os.environ.get("VERTEX_API_KEY")        # keep this secret / use Cloud Run env
PROJECT_ID = os.environ.get("GCP_PROJECT")               # optional
BUCKET_NAME = os.environ.get("BUCKET_NAME")              # required for uploads if you want public hosting
BQ_DATASET = os.environ.get("BQ_DATASET", "thriftkids_analytics")
BQ_TABLE = os.environ.get("BQ_TABLE", "events")
USE_AGENT = os.environ.get("USE_AGENT", "true").lower() == "true"

# Model endpoint template (region+model)
GEMINI_ENDPOINT_TEMPLATE = (
    "https://us-central1-aiplatform.googleapis.com/v1/publishers/google/"
    "models/gemini-2.5-flash-lite:generateContent?key={api_key}"
)

# ----------
# App init
# ----------
app = Flask(__name__)


# ----------
# Helpers: Google clients (lazy init)
# ----------
def get_storage_client():
    if not GCLOUD_AVAILABLE:
        raise RuntimeError("google-cloud-storage not available in this environment")
    return storage.Client(project=PROJECT_ID)


def get_firestore_client():
    if not GCLOUD_AVAILABLE:
        raise RuntimeError("google-cloud-firestore not available in this environment")
    return firestore.Client(project=PROJECT_ID)


def get_bq_client():
    if not GCLOUD_AVAILABLE:
        raise RuntimeError("google-cloud-bigquery not available in this environment")
    return bigquery.Client(project=PROJECT_ID)


# ----------
# Helpers: Upload file to GCS
# ----------
def upload_file_to_gcs(file_stream, filename: str, content_type: str) -> str:
    """
    Upload file_stream to GCS and return a public URL (for demo).
    If public making fails, returns gs:// path.
    """
    if not BUCKET_NAME:
        raise RuntimeError("BUCKET_NAME not set")
    client = get_storage_client()
    bucket = client.bucket(BUCKET_NAME)
    blob_name = f"images/{uuid.uuid4()}_{filename}"
    blob = bucket.blob(blob_name)
    blob.upload_from_file(file_stream, content_type=content_type)
    try:
        blob.make_public()
        return blob.public_url
    except Exception:
        return f"gs://{BUCKET_NAME}/{blob_name}"


# ----------
# Helpers: Gemini (Vertex) model call using API key
# ----------
def call_gemini(prompt: str, timeout: int = 30) -> str:
    """
    Call Gemini publisher model via API key. Returns best-effort text output.
    """
    if not VERTEX_API_KEY:
        raise RuntimeError("VERTEX_API_KEY not set")
    url = GEMINI_ENDPOINT_TEMPLATE.format(api_key=VERTEX_API_KEY)
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ]
    }
    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    # Typical structure: data["candidates"][0]["content"]["parts"][0]["text"]
    try:
        candidates = data.get("candidates")
        if isinstance(candidates, list) and candidates:
            first = candidates[0]
            content = first.get("content") or {}
            parts = content.get("parts") or []
            if parts and isinstance(parts, list):
                part0 = parts[0]
                if isinstance(part0, dict):
                    return part0.get("text") or str(part0)
                return str(part0)
        # fallback
        return json.dumps(data)[:2000]
    except Exception:
        return json.dumps(data)[:2000]


# ----------
# Helpers: BigQuery logging (best-effort)
# ----------
def log_event_bq(event_type: str, payload: dict):
    """
    Insert a minimal event row to BigQuery. Non-fatal if errors occur.
    Schema expected: event_time STRING, event_type STRING, payload STRING
    """
    if not GCLOUD_AVAILABLE:
        return
    try:
        bq = get_bq_client()
        table_id = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"
        rows = [{
            "event_time": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "payload": json.dumps(payload)
        }]
        errors = bq.insert_rows_json(table_id, rows)
        if errors:
            print("BigQuery insert errors:", errors)
    except Exception as e:
        print("BigQuery logging failed:", e)


# ----------
# Routes
# ----------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return "OK", 200


@app.route("/api/test-ai")
def test_ai():
    """
    Test route to check Gemini is reachable. Only works if VERTEX_API_KEY is set.
    """
    if not VERTEX_API_KEY:
        return jsonify({"error": "VERTEX_API_KEY not configured"}), 400
    try:
        sample = "Write a friendly one-sentence listing description for a blue baby romper, size 6-12 months."
        out = call_gemini(sample)
        return jsonify({"ok": True, "response": out})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/listings", methods=["GET"])
def list_listings():
    """
    Returns listings from Firestore if available, otherwise returns empty list.
    """
    try:
        db = get_firestore_client()
        docs = db.collection("listings").order_by("created_at", direction=firestore.Query.DESCENDING).stream()
        results = []
        for d in docs:
            doc = d.to_dict()
            doc["id"] = d.id
            # normalize created_at if possible
            try:
                if "created_at" in doc and hasattr(doc["created_at"], "to_datetime"):
                    doc["created_at"] = doc["created_at"].to_datetime().isoformat()
            except Exception:
                pass
            results.append(doc)
        log_event_bq("list_listings", {"count": len(results)})
        return jsonify(results)
    except Exception as e:
        print("list_listings error (falling back to empty):", e)
        return jsonify([]), 200


@app.route("/api/listings", methods=["POST"])
def create_listing():
    """
    Accepts multipart/form-data:
    - title (required)
    - size (optional)
    - age_group (optional)
    - condition (optional)
    - notes (optional)
    - description (optional)  <-- manual user-provided description
    - image (required file)
    """
    title = request.form.get("title")
    size = request.form.get("size", "")
    age_group = request.form.get("age_group", "")
    condition = request.form.get("condition", "")
    notes = request.form.get("notes", "")
    user_description = request.form.get("description", "").strip()
    image = request.files.get("image")

    if not title or not image:
        return jsonify({"error": "title and image required"}), 400

    # upload image if possible
    try:
        if BUCKET_NAME and GCLOUD_AVAILABLE:
            image_url = upload_file_to_gcs(image.stream, image.filename, image.content_type)
        else:
            # fallback: save to /tmp and return a path (not public). For demo we return filename
            temp_name = f"/tmp/{uuid.uuid4()}_{image.filename}"
            image.save(temp_name)
            image_url = f"file://{temp_name}"
    except Exception as e:
        print("Image upload error:", e)
        return jsonify({"error": "image upload failed"}), 500

    # choose description: prefer user-provided; else call model if allowed; else fallback template
    if user_description:
        description = user_description
    else:
        prompt = (
            f"Write a 1-2 sentence friendly marketplace listing description for a kids clothing item. "
            f"Title: {title}. Size: {size}. Age group: {age_group}. Seller condition: {condition}. Notes: {notes}."
        )
        if USE_AGENT and VERTEX_API_KEY:
            try:
                description = call_gemini(prompt)
            except Exception as e:
                print("AI call failed:", e)
                description = f"{title} — Size {size}. {notes}"
        else:
            description = f"{title} — Size {size}. {notes}"

    # persist to Firestore if available
    listing_doc = {
        "title": title,
        "size": size,
        "age_group": age_group,
        "condition": condition,
        "notes": notes,
        "image_url": image_url,
        "description": description,
    }

    try:
        if GCLOUD_AVAILABLE:
            db = get_firestore_client()
            doc_ref = db.collection("listings").document()
            db_doc = {**listing_doc, "created_at": firestore.SERVER_TIMESTAMP}
            doc_ref.set(db_doc)
            listing_doc["id"] = doc_ref.id
        else:
            # no Firestore available: include a generated id and a created_at timestamp
            listing_doc["id"] = str(uuid.uuid4())
            listing_doc["created_at"] = datetime.utcnow().isoformat()
        log_event_bq("create_listing", {"id": listing_doc["id"], "title": title})
        return jsonify(listing_doc), 201
    except Exception as e:
        print("Failed to write to Firestore (returning object):", e)
        # return listing back to client so demo still works
        listing_doc["id"] = str(uuid.uuid4())
        listing_doc["created_at"] = datetime.utcnow().isoformat()
        return jsonify(listing_doc), 201


# ----------
# Run (local only)
# ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
