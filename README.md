# AICTE Approval Validation Platform

AI-enabled **decision-support** platform for preliminary validation of AICTE approval applications
(EoA etc.). All AI output is advisory; scrutiny, inspection and final decisions rest with AICTE officials.

Architecture: event-driven microservices on a Redis-Streams bus with a shared, append-only audit store.

| # | Module | Path | Pattern | Port |
|---|--------|------|---------|------|
| 1 | Ingestion & OCR | `services/ingestion` | Pipeline (Celery) | 8001 |
| 2 | Validation Engine | `services/validation` + `rules/` | Rules engine + Strategy | 8002 |
| 3 | Anomaly & Forgery | `services/anomaly` | Fan-out/Scatter-Gather | 8003 |
| 4 | External Verification | `services/verification` | Adapter + State machine + Circuit breaker | 8004 |
| 5 | Infrastructure Compliance | `services/compliance` + `norms/` | Multi-modal AI + Norm engine | 8005 |
| 6 | Dashboard, Alerts, Audit | `services/dashboard` + `frontend/` | CQRS + Event sourcing + WebSocket | 8006 / 3000 |

Event flow: `document.uploaded` → (M1) → `document.processed` → M2, M3, M4, M5 in parallel →
`validation.completed`, `anomaly.flagged|cleared`, `verification.completed`, `compliance.completed` → M6 event store.

## Run
```bash
cp .env.example .env
docker compose up --build -d
docker compose exec dashboard-api python -m services.dashboard.seed   # officer1/officer123, admin/admin123
open http://localhost:3000
curl -F application_id=APP-1001 -F files=@your.pdf http://localhost:8001/api/v1/documents/upload
```
Works offline with fallbacks: Tesseract (no Azure key), keyword classifier (no LayoutLM weights),
template Gemini explanations (no key), synthetic AICTE records & mock issuing authorities (`USE_MOCK_VERIFICATION=true`).

## Configuration points
- `rules/*.json` – checklists per application category (edit per Approval Process Handbook; versioned in Git)
- `norms/*.json` – infrastructure norms per programme/intake
- `AICTE_RECORDS_URL` – read-only AICTE records API (otherwise synthetic data in `services/validation/app/records.py`)
- `NAAC_URL/KEY`, `NBA_URL/KEY`, `DIGILOCKER_URL/KEY`, `MCA21_URL/KEY`, `AISHE_URL/KEY` – only with authorised access; otherwise status is `SOURCE_UNAVAILABLE` → manual review
- `ELA_CNN_WEIGHTS` (train with `services/anomaly/train_ela.py`), `YOLO_WEIGHTS`, `LAYOUTLM_MODEL_DIR`
- `ANOMALY_THRESHOLD` (default 0.4)

## Safeguards
Role-based JWT access (INSTITUTION / OFFICER / ADMIN) + PostgreSQL RLS; DB triggers make `event_store` immutable;
SHA-256 evidence hash for every source response; anomaly flags carry evidence, region and advisory disclaimer;
no module bypasses access controls or assumes access to restricted databases.

## Known gaps / next steps
- Fine-tuned YOLO (AICTE equipment) and LayoutLMv3 / ELA-CNN weights must be trained on authorised data.
- Programme→norm-set mapping and application category come from the AICTE records API (stubbed).
- Real issuing-authority API contracts differ; adapt `services/verification/app/adapters.py` per agreement.
- Use synthetic/anonymised data for demos; run `pytest tests/` (needs service deps installed).
