CREATE TABLE inspection_rule_settings (
    id SMALLINT PRIMARY KEY CHECK (id = 1),
    settings JSONB NOT NULL,
    revision BIGINT NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO inspection_rule_settings(id, settings) VALUES (1,
'{"confidenceThreshold":0.7,"fasteningGapThreshold":3.0,"axisDirection":"Y_POSITIVE","expectedOrder":["bolt","washer","nut"],"alignmentTolerance":10.0,"ruleVersion":"geometry-v1"}');
CREATE TABLE inspection (
    id UUID PRIMARY KEY,
    inspection_time TIMESTAMPTZ NOT NULL,
    status VARCHAR(16) NOT NULL CHECK (status IN ('PROCESSING','COMPLETED','FAILED')),
    original_image_path TEXT NOT NULL,
    processed_image_path TEXT NOT NULL,
    original_content_type VARCHAR(32) NOT NULL,
    overall_result VARCHAR(4) CHECK (overall_result IN ('PASS','FAIL')),
    component_result VARCHAR(8), order_result VARCHAR(8), fastening_result VARCHAR(8),
    bolt_confidence DOUBLE PRECISION, nut_confidence DOUBLE PRECISION, washer_confidence DOUBLE PRECISION,
    fastening_gap DOUBLE PRECISION,
    model_version TEXT,
    rule_snapshot JSONB NOT NULL,
    decision JSONB,
    equipment_id VARCHAR(100), product_code VARCHAR(100), lot_number VARCHAR(100), operator_id VARCHAR(100),
    image_sha256 CHAR(64) NOT NULL,
    failure_code VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    CHECK (status <> 'COMPLETED' OR (decision IS NOT NULL AND model_version IS NOT NULL AND overall_result IS NOT NULL))
);
CREATE INDEX inspection_time_idx ON inspection (inspection_time DESC, id DESC) WHERE status='COMPLETED';
CREATE INDEX inspection_result_time_idx ON inspection (overall_result, inspection_time DESC) WHERE status='COMPLETED';
CREATE INDEX inspection_product_idx ON inspection (product_code, inspection_time DESC);
CREATE INDEX inspection_equipment_idx ON inspection (equipment_id, inspection_time DESC);
CREATE INDEX inspection_lot_idx ON inspection (lot_number, inspection_time DESC);
CREATE TABLE inspection_detection (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    inspection_id UUID NOT NULL REFERENCES inspection(id) ON DELETE CASCADE,
    class_name VARCHAR(64) NOT NULL,
    confidence DOUBLE PRECISION NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    bbox JSONB NOT NULL,
    segmentation JSONB NOT NULL
);
CREATE INDEX detection_inspection_idx ON inspection_detection(inspection_id);
COMMENT ON COLUMN inspection_detection.segmentation IS 'Polygon coordinates, not dense raster masks. Limited by Vision response validation; versioned file/object storage may replace this for large masks.';
