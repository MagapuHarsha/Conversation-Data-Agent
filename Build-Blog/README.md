# Conversational Data Agent  
# Note this method is end to end implementation only in cloud.
# To run the application locally you to directly clone the project, install all the dependencies, make sure to create a env file with the format given below.

Backend: Flask (Cloud Run)  
Frontend: Streamlit (Cloud Run)


env format:

PROJECT_ID=""
REGION=""
BUCKET_NAME=""
MODEL_RESOURCE=""

DB_USER=""
DB_PASS=""
DB_NAME=""
INSTANCE_CONNECTION_NAME=""



This project provides a complete data analysis agent with:
- File upload (CSV, XLSX, JSON)
- Automatic summaries & charts
- Data quality checks
- Trend detection
- NL → Data analysis for files
- NL → SQL generation for databases (BigQuery / CloudSQL)
- Fully containerized backend + frontend, deployed on Cloud Run

---

# 📁 Project Structure

Build-Blog/
│── backend/
│ ├── main.py
│ ├── analysis_utils.py
│ ├── sql_agent.py
│ ├── gcp_helpers.py
│ ├── vertex_ai_client.py
│ ├── requirements.txt
│ └── Dockerfile
│
└── streamlit_frontend/
├── app.py
├── requirements.txt
└── Dockerfile


# 🚀 Deployment Overview

You will deploy **two Cloud Run services**:

| Component | Cloud Run Service | Description |
|----------|------------------|-------------|
| Backend | `data-agent` | Flask API |
| Frontend | `streamlit-frontend` | Streamlit UI |


# make sure to deploy backend and call it to the front end in app.py use the variable BACKEND in app.py to connect with the backend.
---

# 🖥 Backend (Flask)

## ▶ Run Backend Locally
cd backend
pip install -r requirements.txt
python main.py

yaml
Copy code
Runs on:  
`http://localhost:8080`

---

# 🐳 Backend: Build Docker Image
Run **inside `/backend`**:

gcloud builds submit --tag gcr.io/BUILD-BLOG-478807/data-agent-backend:v1 .

yaml
Copy code

---

# ☁ Backend: Deploy to Cloud Run
gcloud run deploy data-agent
--image gcr.io/build-and-blog-478807/data-agent-backend:v1
--region europe-west1
--allow-unauthenticated

mathematica
Copy code

Cloud Run will give you a URL like:

https://data-agent-xxxxx.europe-west1.run.app

yaml
Copy code

Use it in the frontend.

---

# 🌍 Backend Environment Variables (Cloud Run)

| Variable | Meaning |
|---------|---------|
| PROJECT_ID | GCP project |
| BUCKET_NAME | GCS bucket name |
| INSTANCE_CONNECTION_NAME | CloudSQL |
| DB_USER | SQL user |
| DB_PASS | SQL pass |
| DB_NAME | SQL DB name |

---

# 🎨 Frontend (Streamlit)

## ▶ Run Locally

cd streamlit_frontend
pip install -r requirements.txt
streamlit run app.py

yaml
Copy code

Runs on: `http://localhost:8501`

---

# 🔗 Set Backend URL in `app.py`

Inside `streamlit_frontend/app.py`:

```python
API_URL = "https://data-agent-XXXXX.europe-west1.run.app"
🐳 Frontend: Build Docker Image
Run inside /streamlit_frontend:

bash
Copy code
gcloud builds submit --tag gcr.io/build-and-blog-478807/streamlit-frontend:v1 .
☁ Frontend: Deploy to Cloud Run
lua
Copy code
gcloud run deploy streamlit-frontend \
  --image gcr.io/build-and-blog-478807/streamlit-frontend:v1 \
  --region europe-west1 \
  --allow-unauthenticated
You get:

arduino
Copy code
https://streamlit-frontend-xxxxx.europe-west1.run.app
Open it in browser.

🛠 Troubleshooting
❌ 404 Not Found (Frontend)
You built from the wrong folder.
Build must run from:

bash
Copy code
Build-Blog/streamlit_frontend
❌ Charts missing / Matplotlib errors
Your Dockerfile must include:

Copy code
libopenblas-dev
liblapack-dev
libfreetype6-dev
libpng-dev
❌ Backend Error / Missing summary
Backend didn't return correct JSON — usually because wrong endpoint or bad URL.

❌ Service Unavailable
Container failed to boot → fix Dockerfile or entrypoint.


🎯 Summary

You now have:

Full backend API for data upload, summarize, NL queries

Streamlit frontend UI

CI-ready Dockerfiles for both

Cloud Run–ready deployment flow

✔ Final Commands (Copy/Paste)
Backend
cd backend
gcloud builds submit --tag gcr.io/build-and-blog-478807/data-agent-backend:v1 .
gcloud run deploy data-agent \
  --image gcr.io/build-and-blog-478807/data-agent-backend:v1 \
  --region europe-west1 \
  --allow-unauthenticated

Frontend
cd streamlit_frontend
gcloud builds submit --tag gcr.io/build-and-blog-478807/streamlit-frontend:v1 .
gcloud run deploy streamlit-frontend \
  --image gcr.io/build-and-blog-478807/streamlit-frontend:v1 \
  --region europe-west1 \
  --allow-unauthenticated