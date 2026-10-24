CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Module 1
CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id TEXT NOT NULL,
  minio_key TEXT NOT NULL,
  filename TEXT,
  content_sha256 TEXT,
  doc_type TEXT,
  status TEXT NOT NULL DEFAULT 'UPLOADED',
  extracted_json JSONB,
  ocr_confidence REAL,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE IF NOT EXISTS pipeline_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES documents(id),
  stage TEXT, status TEXT, error_msg TEXT,
  started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ,
  retry_count INT DEFAULT 0
);
-- Module 2
CREATE TABLE IF NOT EXISTS validation_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id TEXT, rule_id TEXT, status TEXT, severity TEXT,
  message TEXT, plain_message TEXT, evidence JSONB, created_at TIMESTAMPTZ DEFAULT now()
);
-- Module 3
CREATE TABLE IF NOT EXISTS anomaly_flags (
  flag_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID, flag_type TEXT, confidence_score REAL, region JSONB,
  reason TEXT, gemini_explanation TEXT, reviewed_by_human BOOLEAN DEFAULT false,
  reviewer TEXT, review_outcome TEXT, advisory_disclaimer TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
-- Module 4
CREATE TABLE IF NOT EXISTS verification_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID, source TEXT, status TEXT, query_params JSONB,
  source_response JSONB, evidence_hash TEXT, attempts INT DEFAULT 0,
  checked_at TIMESTAMPTZ DEFAULT now()
);
-- Module 5
CREATE TABLE IF NOT EXISTS compliance_findings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id TEXT, norm_key TEXT, required NUMERIC, observed NUMERIC,
  finding TEXT, evidence JSONB, advisory_disclaimer TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
-- Module 6: append-only event store
CREATE TABLE IF NOT EXISTS event_store (
  id BIGSERIAL PRIMARY KEY,
  event_id UUID UNIQUE NOT NULL,
  event_type TEXT NOT NULL,
  aggregate_id TEXT NOT NULL,
  payload JSONB NOT NULL,
  actor TEXT NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL
);
CREATE OR REPLACE FUNCTION forbid_mutation() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'event_store is append-only'; END; $$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS no_update ON event_store;
CREATE TRIGGER no_update BEFORE UPDATE OR DELETE ON event_store
  FOR EACH ROW EXECUTE FUNCTION forbid_mutation();
DROP TRIGGER IF EXISTS no_truncate ON event_store;
CREATE TRIGGER no_truncate BEFORE TRUNCATE ON event_store
  FOR EACH STATEMENT EXECUTE FUNCTION forbid_mutation();

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT,
  role TEXT CHECK (role IN ('INSTITUTION','OFFICER','ADMIN'))
);
CREATE TABLE IF NOT EXISTS alert_rules (
  id SERIAL PRIMARY KEY, name TEXT, event_type TEXT, condition JSONB,
  channels TEXT[], notify_role TEXT
);

-- Read side (CQRS)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_application_status AS
SELECT application_id,
       count(*) AS documents,
       count(*) FILTER (WHERE status='PROCESSED') AS processed
FROM documents GROUP BY application_id;
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_deficiency_summary AS
SELECT application_id, severity, count(*) AS failed
FROM validation_results WHERE status='FAILED' GROUP BY application_id, severity;
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_verification_status AS
SELECT d.application_id, v.status, count(*) AS n
FROM verification_results v JOIN documents d ON d.id=v.document_id
GROUP BY d.application_id, v.status;
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_anomaly_queue AS
SELECT f.flag_id, f.document_id, d.application_id, f.flag_type, f.confidence_score, f.created_at
FROM anomaly_flags f JOIN documents d ON d.id=f.document_id
WHERE f.reviewed_by_human = false ORDER BY f.confidence_score DESC;

-- Row-level security (defence in depth). The API sets `SET app.role` / `SET app.current_app` per request
-- when connecting as the low-privilege `aicte_api` role; table owners bypass RLS unless FORCE is set.
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS doc_scope ON documents;
CREATE POLICY doc_scope ON documents USING (
  coalesce(current_setting('app.role', true), 'OFFICER') IN ('OFFICER','ADMIN')
  OR application_id = current_setting('app.current_app', true));
