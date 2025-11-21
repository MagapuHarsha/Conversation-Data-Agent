# ===========================================
# FRONTEND: Streamlit UI (Cloud Run Ready)
# ===========================================
FROM python:3.11-slim

WORKDIR /app

# Install minimal system deps for pandas, numpy
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libopenblas-dev \
    liblapack-dev \
    libfreetype6-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Streamlit + dependencies
RUN pip install --no-cache-dir --upgrade pip wheel setuptools
RUN pip install --no-cache-dir -r requirements.txt

# Copy Streamlit app
COPY app.py .

EXPOSE 8080

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8080", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
