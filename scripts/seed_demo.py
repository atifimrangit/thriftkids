"""
Seed 3 demo listings:
- requires google-cloud libs and valid ADC credentials (gcloud auth application-default login)
- env vars: GCP_PROJECT, BUCKET_NAME, VERTEX_API_KEY
"""
import os
import json
import uuid
from google.cloud import storage, firestore
import google.auth.transport.requests, google.auth
import requests

PROJECT = os.environ.get("GCP_PROJECT")
BUCKET = os.environ.get("BUCKET_NAME")
AGENT_KEY = os.environ.get("VERTEX_API_KEY")
IMAGES_DIR = os.path.join("app", "static", "sample_images")

def upload_image(path):
    client = storage.Client(project=PROJECT)
    bucket = client.bucket(BUCKET)
    blob_name = f"demo/{uuid.uuid4()}_{os.path.basename(path)}"
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(path)
    try:
        blob.make_public()
        return blob.public_url
    except:
        return f"gs://{BUCKET}/{blob_name}"

def get_adc_token():
    creds, _ = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds.token

def call_gemini(prompt):
    # Use the same endpoint as in main.py with API key
    url = f"https://us-central1-aiplatform.googleapis.com/v1/publishers/google/models/gemini-2.5-flash-lite:generateContent?key={AGENT_KEY}"
    payload = {"contents":[{"role":"user","parts":[{"text":prompt}]}]}
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return json.dumps(data)

def main():
    db = firestore.Client(project=PROJECT)
    files = sorted([f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(('.jpg','.jpeg','.png'))])[:3]
    for f in files:
        path = os.path.join(IMAGES_DIR, f)
        print("Uploading:", path)
        url = upload_image(path)
        title = f"Demo {os.path.splitext(f)[0]}"
        size = "6-12m"
        age_group = "Infant"
        cond = "Good"
        notes = "Demo sample"

        prompt = f"Write a short 1-2 sentence marketplace description: {title}, size {size}, age group {age_group}, condition {cond}, notes: {notes}"
        try:
            desc = call_gemini(prompt)
        except Exception as e:
            print("Gemini call failed:", e)
            desc = f"{title} - {notes} (fallback)"
        doc_ref = db.collection("listings").document()
        doc = {
            "title": title,
            "size": size,
            "age_group": age_group,
            "condition": cond,
            "notes": notes,
            "image_url": url,
            "description": desc,
            "created_at": firestore.SERVER_TIMESTAMP
        }
        doc_ref.set(doc)
        print("Created:", doc_ref.id)
        print("Desc:", desc[:200])

if __name__ == "__main__":
    main()
