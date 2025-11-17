# ThriftKids - demo

Quick start:
1. Copy `.env.example` → `.env` and fill values (or set env vars in Cloud Run)
2. Add 3 small images to `app/static/sample_images/` (jpg/png)
3. Install deps and run locally:
   - python -m venv venv
   - source venv/bin/activate
   - pip install -r app/requirements.txt
   - python app/main.py
4. To seed demo (uploads images to GCS and creates 3 listings), run:
   - gcloud auth application-default login
   - export GCP_PROJECT=...
   - export BUCKET_NAME=...
   - export VERTEX_API_KEY=...
   - python scripts/seed_demo.py
5. Deploy to Cloud Run with env var VERTEX_API_KEY set (use Cloud Run console or gcloud)
