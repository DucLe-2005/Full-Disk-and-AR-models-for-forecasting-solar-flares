BEGIN;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'predictions'
          AND column_name = 'prediction_datetime'
    ) AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'predictions'
          AND column_name = 'date'
    ) THEN
        ALTER TABLE predictions RENAME COLUMN prediction_datetime TO date;
    END IF;
END $$;

ALTER TABLE predictions
    ADD COLUMN IF NOT EXISTS prediction_hour timestamp,
    ADD COLUMN IF NOT EXISTS localized_probabilities json NOT NULL DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS heatmaps json NOT NULL DEFAULT '[]';

UPDATE predictions
SET prediction_hour = date_trunc('hour', date)
WHERE prediction_hour IS NULL;

ALTER TABLE predictions
    ALTER COLUMN prediction_hour SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ix_predictions_prediction_hour
    ON predictions (prediction_hour);

ALTER TABLE pipeline_jobs
    ADD COLUMN IF NOT EXISTS requested_prediction_hour timestamp;

CREATE INDEX IF NOT EXISTS ix_pipeline_jobs_requested_prediction_hour
    ON pipeline_jobs (requested_prediction_hour);

COMMIT;
