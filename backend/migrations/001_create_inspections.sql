CREATE TABLE IF NOT EXISTS inspections (
    id BIGSERIAL PRIMARY KEY,
    inspection_time TIMESTAMPTZ NOT NULL,
    overall_result VARCHAR(20) NOT NULL CHECK (overall_result IN ('NORMAL', 'DEFECT')),
    missing_component_result VARCHAR(20) NOT NULL
        CHECK (missing_component_result IN ('NORMAL', 'DEFECT', 'NOT_EVALUATED')),
    alignment_result VARCHAR(20) NOT NULL
        CHECK (alignment_result IN ('NORMAL', 'DEFECT', 'NOT_EVALUATED')),
    fastening_result VARCHAR(20) NOT NULL
        CHECK (fastening_result IN ('NORMAL', 'DEFECT', 'NOT_EVALUATED')),
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    defect_image_path TEXT,
    event_key VARCHAR(120) UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_inspections_inspection_time
    ON inspections (inspection_time DESC);

CREATE INDEX IF NOT EXISTS ix_inspections_overall_result
    ON inspections (overall_result);
