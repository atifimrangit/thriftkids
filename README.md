ThriftKids — AI-Powered Kidswear Resale App (Cloud Run + Vertex AI)

ThriftKids is a lightweight, serverless web app designed to make buying and selling gently used kids’ clothing simple — while promoting sustainability and reducing textile waste.

The app lets users upload an item, auto-generates a clean product description using Vertex AI Gemini, and instantly publishes the listing. Everything runs on Google Cloud Run, Firestore, and Cloud Storage, making the system scalable with minimal maintenance or cost.

🌍 Why ThriftKids?

Children outgrow clothes quickly — often after wearing them just 3–5 times. This accelerates textile waste, contributing to more than 92 million tons of global waste each year.

ThriftKids enables parents to circulate kidswear instead of discarding it, while showcasing how Generative AI can remove friction in peer-to-peer listing workflows.

🏗️ Architecture Overview

Tech Stack:

Cloud Run – Serverless hosting for the Flask backend

Firestore – NoSQL database for storing listings

Cloud Storage – Stores uploaded images

Vertex AI Gemini (2.5 Flash Lite) – Generates product descriptions

Bootstrap – Clean, responsive UI

Python + Flask – Core application logic

High-Level Flow:

User fills listing form + uploads image

Image uploaded to Cloud Storage

Metadata saved to Firestore

If no manual description, Gemini generates one

Listing shown instantly on the UI


🚀 Features

Upload kidswear image + details

AI-generated product description using Gemini 2.5 Flash Lite

Clean Bootstrap UI with responsive cards

Instant listing display

Fully serverless architecture

Extremely low cost to run (fits $5 free credit easily)

📦 Repository Structure
thriftkids/
│
├── app/
│   ├── main.py                # Flask backend
│   ├── Dockerfile             # Cloud Run image
│   ├── requirements.txt       # Python dependencies
│   ├── templates/
│   │   └── index.html         # UI template
│   └── static/                # Optional static files
│
├── scripts/
│   └── seed_demo_no_images.py # Optional Firestore seeding script
│
├── docs/
│   └── architecture.png       # Architecture diagram (optional)
│
└── README.md

🧰 Prerequisites

Before deploying, ensure you have:

Google Cloud Project with billing enabled

Cloud Run API enabled

Firestore in “Native Mode”

Cloud Storage bucket created

Vertex AI API enabled

Python 3.10+ (optional for local dev)

⚙️ Setup & Deployment
1. Clone the Repository
git clone https://github.com/<your-username>/thriftkids.git
cd thriftkids/app

2. Build with Cloud Build
gcloud builds submit --tag gcr.io/$PROJECT_ID/thriftkids

3. Deploy to Cloud Run
gcloud run deploy thriftkids \
  --image gcr.io/$PROJECT_ID/thriftkids \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT=$PROJECT_ID,BUCKET_NAME=$BUCKET_NAME,VERTEX_API_KEY=$VERTEX_API_KEY,USE_AGENT=true

4. Visit Your App

Cloud Run will give you a public URL.
Open it in the browser to test your marketplace.

🤖 AI Description Generation

The app uses:

POST https://us-central1-aiplatform.googleapis.com/v1/publishers/google/models/gemini-2.5-flash-lite:generateContent


It sends:

item title

size

age group

condition

optional notes

and returns a natural, marketplace-ready description.

If a user manually enters the description, the AI call is skipped.

🧪 Optional: Seed Demo Data

To quickly generate sample listings:

python3 scripts/seed_demo_no_images.py


This creates listings without needing sample images.

📸 Screenshots

Add your UI screenshots here:



🧭 Roadmap

Planned enhancements:

Fabric detection using Vision API

“Waste saved” score per garment

Estimated CO₂ impact

Smart pricing suggestions

User accounts + wishlists

🙌 Acknowledgements

Built as part of the Google Build & Blog Marathon.
Special thanks to the Google Cloud Run and Vertex AI teams for the tools that made this project possible.