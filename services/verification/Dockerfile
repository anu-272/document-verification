FROM python:3.11-slim
WORKDIR /srv
COPY services/verification/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared ./shared
COPY services ./services
ENV PYTHONPATH=/srv
CMD ["uvicorn", "services.verification.app.main:app", "--host", "0.0.0.0", "--port", "8004"]
