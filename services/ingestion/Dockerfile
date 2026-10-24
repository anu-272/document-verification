FROM python:3.11-slim
RUN apt-get update && apt-get install -y tesseract-ocr libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY services/ingestion/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && python -m spacy download en_core_web_sm || true
COPY shared ./shared
COPY services ./services
ENV PYTHONPATH=/srv
CMD ["uvicorn", "services.ingestion.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
