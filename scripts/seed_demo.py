#!/usr/bin/env python3
"""
Seed N demo listings WITHOUT requiring local image files.

- Uses placeholder image URLs so the UI can render images.
- Optionally calls Gemini via VERTEX_API_KEY to generate descriptions.
- Writes documents to Firestore `listings` collection.

Env vars:
  GCP_PROJECT      (required)
  VERTEX_API_KEY   (optional) - if present, script will call Gemini for descriptions
  COUNT            (optional) - number of demo records to create (default 3)

Usage:
  export GCP_PROJECT="your-project-id"
  export VERTEX_API_KEY="..."   # optional
  python3 scripts/seed_demo_no_images.py
"""
import os
import json
import uuid
from datetime import datetime
from google.cloud import firestore
import requests

PROJECT = os.environ.get("GCP_PROJECT")
API_KEY = os.environ.get("VERTEX_API_KEY")  # optional
COUNT = int(os.environ.get("COUNT", "3"))

if not PROJECT:
    raise SystemExit("ERROR: Please set GCP_PROJECT environment variable before running.")

# simple placeholder images (these are public)
PLACEHOLDER_IMAGES = [
    "https://via.placeholder.com/400x400.png?text=ThriftKids+1",
    "https://via.placeholder.com/400x400.png?text=ThriftKids+2",
    "https://via.placeholder.com/400x400.png?text=ThriftKids+3",
    "https://via.placeholder.com/400x400.png?text=ThriftKids+4",
    "https://via.placeholder.com/400x400.png?text=ThriftKids+5",
]

def call_gemini(prompt: str) -> str | None:
    if not API_KEY:
        return None
    url = f"https://us-central1-aiplatform.googleapis.com/v1/publishers/google/models/gemini-2.5-flash-lite:generateContent?key={API_KEY}"
    payload = {"contents":[{"role":"user","parts":[{"text":prompt}]}]}
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None

def create_demo_doc(db, idx: int):
    title = f"Demo Item #{idx+1}"
    size = ["0-3m","3-6m","6-12m","12-18m","18-24m"][idx % 5]
    age_group = ["Infant","Infant","Toddler","Toddler","Child"][idx % 5]
    condition = ["New","Like New","Good","Fair","New"][idx % 5]
    notes = "Seeded demo listing"

    # choose placeholder image in rotation
    image_url = PLACEHOLDER_IMAGES[idx % len(PLACEHOLDER_IMAGES)]

    # build prompt for AI (only used if API_KEY is present)
    prompt = (
        f"Write a friendly 1-2 sentence marketplace listing description for a kids clothing item. "
        f"Title: {title}. Size: {size}. Age group: {age_group}. Condition: {condition}. Notes: {notes}."
    )

    description = None
    if API_KEY:
        try:
            description = call_gemini(prompt)
        except Exception as e:
            print("AI call failed (falling back):", e)
            description = None

    if not description:
        description = f"{title} — Size {size}. {notes}"

    doc = {
        "title": title,
        "size": size,
        "age_group": age_group,
        "condition": condition,
        "notes": notes,
        "image_url": image_url,
        "description": description,
        "seeded": True,
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    doc_ref = db.collection("listings").document()
    doc_ref.set(doc)
    return doc_ref.id, description

def main():
    db = firestore.Client(project=PROJECT)
    created = []
    for i in range(COUNT):
        doc_id, desc = create_demo_doc(db, i)
        print(f"Created listing id={doc_id} preview=\"{desc[:120]}\"")
        created.append(doc_id)
    print(f"\nSeed complete: created {len(created)} listings.")

if __name__ == "__main__":
    main()
