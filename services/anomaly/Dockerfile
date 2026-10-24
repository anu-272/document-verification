FROM python:3.11-slim
RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /srv
COPY services/anomaly/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared ./shared
COPY services ./services
ENV PYTHONPATH=/srv
CMD ["uvicorn", "services.anomaly.app.main:app", "--host", "0.0.0.0", "--port", "8003"]
