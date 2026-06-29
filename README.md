# Solar Flare Forecasting

Hourly solar-flare prediction from full-disk HMI magnetograms. The stack includes:

- `app/`: FastAPI API, Postgres repositories, job services, and MinIO helpers.
- `prediction/`: queue worker, prediction pipeline, models, and trained weights.
- `web/`: Next.js dashboard for submitting jobs and viewing results.

## Quick Start

Confirm model weights exist:

```text
prediction/modeling/full_disk/trained_models/
prediction/modeling/active_region/trained_models/
```

Create the environment file and start the stack:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

For development, add the development override. It bind-mounts the API,
frontend, worker, and pipeline source into their containers. FastAPI and
Next.js reload automatically when their source changes.

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

The worker sees source changes immediately through the bind mount, but its
Python process must be restarted to import changed code:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml restart worker
```

Services:

- Dashboard: `http://localhost:3000`
- API: `http://localhost:8000`
- API health: `http://localhost:8000/health`
- MinIO API: `http://localhost:9000`
- MinIO console: `http://localhost:9001`

The model weights are mounted read-only into the worker and manual pipeline containers. They are excluded from the Docker build context to keep rebuilds fast.

## Common Commands

```powershell
# Logs
docker compose logs -f worker
docker compose logs -f api
docker compose logs -f web

# Rebuild one service
docker compose build worker
docker compose up -d worker

# Stop the stack
docker compose down

# Stop and delete database/object-store volumes
docker compose down -v
```

Run one pipeline manually:

```powershell
docker compose --profile manual run --rm pipeline --helioviewer-date "2023-04-19 13:00:00"
```

## Backfill

Queue hourly jobs from `2020-01-01 00:00:00` through `2025-12-31 23:00:00`:

```powershell
docker compose exec api python -m app.scripts.backfill_predictions
```

Custom inclusive range:

```powershell
docker compose exec api python -m app.scripts.backfill_predictions `
  --start-time "2020-01-01" `
  --end-time "2025-12-31"
```

The service skips hours with an existing prediction or an already queued/running job. The worker processes the resulting queue normally.

## Job Flow

1. The API normalizes requested timestamps to the whole hour.
2. It deduplicates by requested hour and inserts a queued job.
3. The worker polls Postgres and claims the oldest queued job.
4. The pipeline requests the closest Helioviewer image.
5. The image is accepted only when its timestamp is within `+/-12` minutes of the requested hour; otherwise the job is marked failed.
6. The worker uploads artifacts to MinIO, saves prediction metadata, and marks the job completed.

The worker processes existing jobs only. It does not currently enqueue a new job automatically at each hour.

## API

- `GET /health`
- `POST /predictions/jobs`
- `POST /predictions/jobs/range`
- `GET /predictions/jobs/{job_id}`
- `GET /history/`

## Pipeline

The pipeline in `prediction/pipeline/run_pipeline.py`:

1. Downloads an HMI JP2 and converts it to a full-disk JPG.
2. Runs the four-fold full-disk classifier.
3. Generates Guided Grad-CAM, Integrated Gradients, and DeepLiftShap maps in memory.
4. Combines them into a consensus heatmap.
5. Runs Canny, DBSCAN, convex-hull buffering, solar-disk masking, and reclustering.
6. Saves the buffered solar mask.
7. Produces padded fixed-size `512x512` active-region crops.
8. Runs active-region model inference.

Every final reclustered hull is retained as an active-region proposal. Consensus and area-weighted scores are stored as metadata but do not filter or rank the hulls.

## Artifact Storage

Local worker artifacts:

```text
data/YYYY/MM/DD/full_disk/
data/YYYY/MM/DD/heat_maps/
data/YYYY/MM/DD/active_regions/
```

MinIO object keys:

```text
predictions/YYYY/MM/DD/HH/full_disk/{filename}
predictions/YYYY/MM/DD/HH/heat_maps/{buffered-mask-filename}
predictions/YYYY/MM/DD/HH/active_regions/{filename}
```

The JP2 is an intermediate input and is not uploaded. The database stores MinIO object keys. The frontend resolves them as:

```text
NEXT_PUBLIC_ARTIFACT_BASE_URL + "/" + object_key
```

With the default Compose configuration:

```text
http://localhost:9000/solar-artifacts/predictions/YYYY/MM/DD/HH/...
```

## Environment

The main settings are defined in `.env.example`:

- `DATABASE_URL`: Postgres connection used by API and worker.
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`.
- `JSOC_EMAIL`: retained for optional JSOC support.
- `DEFAULT_HELIOVIEWER_DATE`: fallback for jobs missing a requested date.

Compose uses service hostnames such as `db` and `minio`. Local processes outside Docker should use reachable hostnames such as `localhost`.

## Local Development

```powershell
# Python dependencies
pip install -r requirements.txt

# API
uvicorn app.main:app --reload

# Worker
python -m prediction.worker.run_worker

# Frontend
cd web
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

## Troubleshooting

- Worker failures: `docker compose logs -f worker`
- Missing images: verify MinIO at `http://localhost:9000` and `NEXT_PUBLIC_ARTIFACT_BASE_URL=http://localhost:9000/solar-artifacts`.
- Stale service image: rebuild only that service with `docker compose build <service>`.
- Clean reset: `docker compose down -v` followed by `docker compose up --build`.
