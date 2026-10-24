import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aicte:aicte@localhost:5432/aicte")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "aicte-documents")
AZURE_DI_ENDPOINT = os.getenv("AZURE_DI_ENDPOINT", "")
AZURE_DI_KEY = os.getenv("AZURE_DI_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
ANOMALY_THRESHOLD = float(os.getenv("ANOMALY_THRESHOLD", "0.4"))
USE_MOCK_VERIFICATION = os.getenv("USE_MOCK_VERIFICATION", "true").lower() == "true"
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
ADVISORY_DISCLAIMER = "Preliminary indicator only. Human verification required."
