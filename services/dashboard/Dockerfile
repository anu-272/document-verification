FROM python:3.11-slim
WORKDIR /srv
COPY services/dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shared ./shared
COPY services ./services
COPY rules ./rules
ENV PYTHONPATH=/srv RULES_DIR=/srv/rules
CMD ["uvicorn", "services.dashboard.app.main:app", "--host", "0.0.0.0", "--port", "8006"]
