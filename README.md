# Solar Flare Forecasting

This project forecasts solar flare risk from full-disk HMI magnetogram imagery. It has three application areas:

- `app/`: FastAPI backend for health checks, job creation, job status, prediction history, database models, and MinIO upload helpers.
- `web/`: Next.js frontend dashboard for requesting predictions, polling job status, browsing history, and viewing saved artifacts.
- `prediction/`: Long-running prediction worker, pipeline stages, model definitions, trained weights, and magnetogram download/preprocessing helpers.

The default production-like workflow is Docker Compose: the frontend queues a prediction job through FastAPI, the worker polls Postgres for queued jobs, the prediction pipeline generates artifacts, artifacts are uploaded to MinIO, and prediction metadata is saved in Postgres.

## Project Structure

```text
app/
  api/                 FastAPI routers, schemas, repositories
  core/                Settings, database session, schema creation, MinIO storage
  models/              SQLAlchemy models for predictions and pipeline jobs
  services/            Backend service layer
  Dockerfile           Backend container
  main.py              FastAPI app entrypoint

web/
  app/                 Next.js app routes and dashboard page
  lib/                 Frontend API clients, artifact helpers, TypeScript types
  public/              Static frontend assets
  Dockerfile           Frontend container
  package.json         Frontend dependencies and scripts

prediction/
  worker/              Polling worker entrypoint
  pipeline/            Pipeline orchestration and stages
  modeling/            Model code and trained weights
  download_mag/        FITS/JP2 download and preprocessing helpers
  Dockerfile           Worker container
  Dockerfile.pipeline  Manual one-shot pipeline container

requirements/          Shared Python dependency include files
scripts/               Utility scripts and SQL migrations
data/                  Local generated artifacts; not a production artifact store
docker-compose.yml     Full local stack
```

## Services

Docker Compose starts these services:

- `db`: Postgres 16 database.
- `minio`: S3-compatible artifact storage.
- `createbuckets`: Initializes the MinIO bucket and enables browser downloads.
- `api`: FastAPI backend on `http://localhost:8000`.
- `web`: Next.js frontend on `http://localhost:3000`.
- `worker`: Long-running prediction worker that polls `pipeline_jobs`.
- `pipeline`: Manual one-shot pipeline container under the `manual` profile.

## Environment Variables

Create a root `.env` file before running Docker Compose. Use [.env.example](.env.example) as the template.

```env
JSOC_EMAIL=your_jsoc_email@example.com
DEFAULT_HELIOVIEWER_DATE=

POSTGRES_DB=flare_db
POSTGRES_USER=flare_user
POSTGRES_PASSWORD=flare_password
DATABASE_URL=postgresql+psycopg://flare_user:flare_password@db:5432/flare_db

MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=solar-artifacts
MINIO_SECURE=false
```

Variable notes:

- `JSOC_EMAIL`: Registered JSOC email. The current default pipeline uses Helioviewer JP2 downloads, but JSOC support code still uses this when the FITS flow is enabled.
- `DEFAULT_HELIOVIEWER_DATE`: Optional fallback date for worker jobs that do not include `helioviewer_date`.
- `DATABASE_URL`: Used by FastAPI and the worker inside Docker. The hostname is `db`, the Compose service name.
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: Used by the Postgres container.
- `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`: Used by the MinIO container and bucket initialization.
- `MINIO_ENDPOINT`: Used by FastAPI and the worker inside Docker. The hostname is `minio`, the Compose service name.
- `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `MINIO_SECURE`: Used when uploading artifacts to MinIO.

For local frontend development outside Docker, copy [web/.env.local.example](web/.env.local.example) to `web/.env.local`:

```env
FASTAPI_BASE_URL=http://localhost:8000
NEXT_PUBLIC_ARTIFACT_BASE_URL=http://localhost:9000/solar-artifacts
```

Inside Docker Compose, `FASTAPI_BASE_URL` is set to `http://api:8000` because the Next.js server route talks to FastAPI over the Compose network. `NEXT_PUBLIC_ARTIFACT_BASE_URL` stays `http://localhost:9000/solar-artifacts` because the browser loads images through the host-exposed MinIO port.

## Setup

1. Confirm model weights exist:

```text
prediction/modeling/full_disk/trained_models/
prediction/modeling/active_region/trained_models/
```

2. Create the root `.env`:

```powershell
Copy-Item .env.example .env
```

3. Edit `.env` and set your `JSOC_EMAIL` if needed.

4. Build and start the stack:

```powershell
docker compose up --build
```

5. Open the frontend:

```text
http://localhost:3000
```

Useful service URLs:

- Frontend: `http://localhost:3000`
- FastAPI: `http://localhost:8000`
- FastAPI health: `http://localhost:8000/health`
- MinIO API: `http://localhost:9000`
- MinIO console: `http://localhost:9001`
- Postgres: `localhost:5432`

## Running With Docker Compose

Start everything:

```powershell
docker compose up --build
```

Run detached:

```powershell
docker compose up --build -d
```

View logs:

```powershell
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f web
```

Stop services:

```powershell
docker compose down
```

Stop services and delete database/object-store volumes:

```powershell
docker compose down -v
```

Run the manual one-shot pipeline container:

```powershell
docker compose --profile manual run --rm pipeline --helioviewer-date "2023-04-19 13:00:00"
```

The normal application path does not use the manual pipeline service. It uses the `worker` service.

## Backend API

FastAPI exposes:

- `GET /health`: Database health check.
- `POST /predictions/jobs`: Create or reuse a prediction job.
- `POST /predictions/jobs/range`: Queue one prediction job per hour between `start_time` and `end_time`.
- `GET /predictions/jobs/{job_id}`: Read queued/running/completed/failed job status.
- `GET /history/`: List saved prediction records.

When `POST /predictions/jobs` receives a requested datetime, the backend:

1. Parses `helioviewer_date`.
2. Normalizes it to the prediction hour, for example `2023-04-19 13:12:00` becomes `2023-04-19 13:00:00`.
3. Checks `predictions.prediction_hour`.
4. If a prediction already exists, returns `prediction_exists`.
5. If a queued or running job already exists for that hour, returns `job_exists`.
6. Otherwise inserts a `queued` row into `pipeline_jobs`.

When `POST /predictions/jobs/range` receives `start_time` and `end_time`, the backend normalizes both values to hourly boundaries, walks every hour inclusively, skips hours that already have a saved prediction, skips hours that already have a queued/running job, and inserts queued jobs for the remaining hours. This is the preferred way to backfill large ranges such as 2020 through 2026.

## Database Tables

Fresh databases are created automatically by both the API and worker through SQLAlchemy `create_all`.

Main prediction table: `predictions`

- `id`
- `created_at`
- `date`
- `prediction_hour`, unique and indexed
- `global_flare_probability`
- `predicted_class`
- `localized_probabilities`
- `jp2_object_path`
- `full_disk_image_path`
- `active_regions`
- `heatmaps`

Job table: `pipeline_jobs`

- `id`
- `status`: `queued`, `running`, `completed`, or `failed`
- `created_at`
- `requested_prediction_hour`
- `started_at`
- `finished_at`
- `payload`
- `prediction_id`
- `error_message`

If a worker fails because no Helioviewer magnetogram is found within the allowed time window, the error message is saved in `pipeline_jobs.error_message` and shown in the frontend.

## Worker And Job Flow

The worker runs [prediction/worker/run_worker.py](prediction/worker/run_worker.py).

Loop behavior:

1. Creates database tables if this is the first startup.
2. Polls `pipeline_jobs` every few seconds.
3. Selects the oldest `queued` job.
4. Marks the job `running`.
5. Checks again whether a prediction already exists for the requested hour.
6. Runs the prediction pipeline.
7. Uploads artifacts to MinIO.
8. Saves a row in `predictions`.
9. Marks the job `completed` with `prediction_id`.
10. If any error occurs, marks the job `failed` and saves `error_message`.

The frontend polls `GET /predictions/jobs/{job_id}` through a Next.js proxy while a job is queued or running. It also refreshes history during polling. When the prediction appears in `GET /history/`, the dashboard selects it automatically.

## Prediction Pipeline

The main pipeline entrypoint is [prediction/pipeline/run_pipeline.py](prediction/pipeline/run_pipeline.py).

Pipeline stages:

1. Parse requested Helioviewer datetime.
2. Download an HMI JP2 magnetogram from Helioviewer.
3. Reject the request if the closest available magnetogram is more than 12 minutes before or after the requested time.
4. Convert JP2 to full-disk JPG.
5. Run the 4-fold full-disk classifier and average flare probabilities.
6. Select one full-disk fold for attribution.
7. Generate and save heatmaps:
   - Guided Grad-CAM
   - Integrated Gradients
   - DeepLiftShap
   - Occlusion
8. Propose active-region boxes from attribution maps.
9. Crop active regions from the original full-disk image.
10. Resize crops to 512x512.
11. Run active-region model predictions.
12. Return artifact paths and prediction metadata to the worker.

Heatmaps are saved as images only. The pipeline uses a non-interactive Matplotlib backend and does not open visual windows.

## Artifact Storage

Artifacts are generated locally inside the worker container under:

```text
data/YYYY/MM/DD/jp2/
data/YYYY/MM/DD/full_disk/
data/YYYY/MM/DD/heat_maps/
data/YYYY/MM/DD/active_regions/
```

The worker uploads them to MinIO under:

```text
predictions/{prediction_id}/jp2/{filename}
predictions/{prediction_id}/full_disk/{filename}
predictions/{prediction_id}/heat_maps/{filename}
predictions/{prediction_id}/active_regions/{filename}
```

The database stores MinIO object paths, not local container paths.

The frontend builds browser image URLs from:

```text
NEXT_PUBLIC_ARTIFACT_BASE_URL + "/" + object_path
```

For Docker Compose, that becomes:

```text
http://localhost:9000/solar-artifacts/predictions/{prediction_id}/...
```

## Frontend

The frontend is a Next.js app in `web/`.

Capabilities:

- Submit a point-in-time prediction request.
- Submit a range backfill request that queues every hour between start and end.
- Show waiting state while the worker runs.
- Poll job status until completion or failure.
- Show no-image-within-12-minutes errors from the worker.
- Browse past prediction history.
- Filter history by datetime range.
- Display global probability.
- Display full-disk image.
- Display heatmaps.
- Display active-region crops and localized probabilities.

Run locally outside Docker:

```powershell
cd web
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

## Local Python Development

Install all Python dependencies:

```powershell
pip install -r requirements/requirements.txt
```

Run FastAPI locally:

```powershell
uvicorn app.main:app --reload
```

Run the worker locally:

```powershell
python -m prediction.worker.run_worker
```

Run the pipeline directly:

```powershell
python -m prediction.pipeline.run_pipeline --helioviewer-date "2023-04-19 13:00:00"
```

For local Python runs outside Docker, use hostnames reachable from your machine in `DATABASE_URL` and `MINIO_ENDPOINT`, for example `localhost:5432` and `localhost:9000` instead of Compose service names `db` and `minio`.

## Troubleshooting

Rebuild after code or dependency changes:

```powershell
docker compose build --no-cache api worker web
docker compose up
```

If the worker log still references `/app/worker/run_worker.py`, the old worker image is running. Rebuild the worker:

```powershell
docker compose build --no-cache worker
docker compose up worker
```

If the frontend waits forever, check worker logs:

```powershell
docker compose logs -f worker
```

If images do not display, confirm MinIO is reachable at `http://localhost:9000` and that `NEXT_PUBLIC_ARTIFACT_BASE_URL` points to `http://localhost:9000/solar-artifacts`.

If you need a clean first-start database:

```powershell
docker compose down -v
docker compose up --build
```
