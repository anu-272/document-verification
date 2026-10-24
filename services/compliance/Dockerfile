FROM python:3.11-slim
RUN apt-get update && apt-get install -y tesseract-ocr libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY services/compliance/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared ./shared
COPY services ./services
COPY norms ./norms
ENV PYTHONPATH=/srv NORMS_DIR=/srv/norms
CMD ["uvicorn", "services.compliance.app.main:app", "--host", "0.0.0.0", "--port", "8005"]
