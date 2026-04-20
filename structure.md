# Project Structure

This project is split into three main application areas:

- `app/`: FastAPI backend
- `web/`: Next.js frontend
- `prediction/`: Prediction worker and model pipeline

The full Docker Compose stack connects the frontend, backend, worker, PostgreSQL, and MinIO.

---

## Top-Level Layout

```text
Full-Disk-and-AR-models-for-forecasting-solar-flares/
|-- app/                 FastAPI backend
|-- web/                 Next.js frontend
|-- prediction/          Prediction pipeline and worker
|-- requirements/        Shared Python dependency files
|-- scripts/             Utility scripts and database migrations
|-- data/                Local/generated artifacts
|-- docker-compose.yml   Local full-stack runtime
|-- requirements.txt     Root Python dependency entrypoint
|-- README.md            Setup and runtime documentation
`-- structure.md         This file
```

---

## Backend: `app/`

The backend owns the API, database models, database repositories, services, settings, and MinIO upload helpers.

```text
app/
|-- api/
|   |-- repositories/    Database access for jobs and predictions
|   |-- routers/         FastAPI routes
|   |-- schemas/         Pydantic request/response schemas
|   `-- services/        Legacy/API service helpers
|
|-- core/
|   |-- config.py        Environment-driven settings
|   |-- database.py      SQLAlchemy engine, session, and Base
|   |-- dependencies.py  FastAPI dependency providers
|   |-- schema.py        First-start schema creation
|   `-- storage.py       MinIO artifact upload helpers
|
|-- models/
|   |-- pipeline_job.py  `pipeline_jobs` table
|   `-- prediction.py    `predictions` table
|
|-- services/
|   |-- job_service.py        Job creation, reuse, and status logic
|   `-- prediction_service.py Prediction history/query logic
|
|-- Dockerfile           Backend API container
`-- main.py              FastAPI application entrypoint
```

Main backend routes:

- `GET /health`
- `POST /predictions/jobs`
- `GET /predictions/jobs/{job_id}`
- `GET /history/`

---

## Frontend: `web/`

The frontend is a Next.js dashboard. It lets users request predictions, poll jobs, browse history, filter by time range, and display saved artifacts from MinIO.

```text
web/
|-- app/
|   |-- api/
|   |   |-- history/
|   |   |   `-- route.ts        Server proxy to FastAPI history endpoint
|   |   `-- jobs/
|   |       |-- route.ts        Server proxy to create jobs
|   |       `-- [jobId]/
|   |           `-- route.ts    Server proxy to poll job status
|   |
|   |-- globals.css            Dashboard styles
|   |-- layout.tsx             Root layout
|   `-- page.tsx               Main prediction dashboard
|
|-- lib/
|   |-- api.ts                 Frontend API helpers
|   |-- artifacts.ts           MinIO/browser artifact URL helpers
|   `-- types.ts               Shared frontend types
|
|-- public/                    Static frontend assets
|-- Dockerfile                 Frontend container
|-- next.config.mjs
|-- package.json
|-- package-lock.json
`-- tsconfig.json
```

Important frontend behavior:

- Browser requests go to Next.js routes under `web/app/api/...`.
- Next.js server routes call FastAPI through `FASTAPI_BASE_URL`.
- Browser image URLs are built from `NEXT_PUBLIC_ARTIFACT_BASE_URL`.

---

## Prediction System: `prediction/`

The prediction folder contains the long-running worker, the prediction pipeline, model definitions, trained weights, and solar image download helpers.

```text
prediction/
|-- download_mag/        Magnetogram/FITS/JP2 download and transform helpers
|
|-- modeling/
|   |-- active_region/   Active-region model definitions and weights
|   `-- full_disk/       Full-disk model definition and fold weights
|
|-- pipeline/
|   |-- stages/          Download, preprocess, attribution, crop, predict stages
|   |-- utils/
|   |-- jobs/
|   `-- run_pipeline.py  Pipeline orchestration entrypoint
|
|-- worker/
|   `-- run_worker.py    Polls jobs, runs pipeline, saves results
|
|-- Dockerfile           Long-running worker container
|-- Dockerfile.pipeline  Manual one-shot pipeline container
`-- requirements.txt
```

The worker is the normal production path. The manual pipeline container is only for direct one-shot runs.

---

## Requirements

```text
requirements/
|-- api.txt              Backend/API dependencies
|-- base.txt             Shared Python dependencies
|-- pipeline.txt         Pipeline/model dependencies
`-- requirements.txt     Combined include file
```

There is also a root `requirements.txt` entrypoint for installing dependencies from the repository root.

---

## Scripts

```text
scripts/
|-- migrations/
|   `-- 001_hourly_prediction_schema.sql
```

The application currently creates database tables automatically on first startup through SQLAlchemy, but migration scripts are kept for reference/manual database setup.

---

## Runtime Flow

```text
User
  |
  v
Next.js frontend
  |
  v
FastAPI backend
  |
  v
PostgreSQL `pipeline_jobs`
  |
  v
Prediction worker
  |
  v
Prediction pipeline
  |
  |-- uploads images/artifacts --> MinIO
  |
  v
PostgreSQL `predictions`
  |
  v
Frontend polls and displays result
```

Step by step:

1. The user chooses a time in the Next.js dashboard.
2. The frontend sends the request to the Next.js API route.
3. The Next.js API route forwards the request to FastAPI.
4. FastAPI normalizes the requested time to the prediction hour.
5. FastAPI checks whether a prediction already exists in `predictions`.
6. If no prediction exists, FastAPI creates or reuses a queued row in `pipeline_jobs`.
7. The worker polls `pipeline_jobs` for queued jobs.
8. The worker marks the job as `running`.
9. The worker runs `prediction/pipeline/run_pipeline.py`.
10. The pipeline downloads the closest valid magnetogram image.
11. If the image is not within the allowed time window, the job is marked `failed`.
12. If the image is valid, the pipeline runs full-disk prediction, heatmap generation, active-region proposal, active-region crop prediction, and artifact generation.
13. The worker uploads generated artifacts to MinIO.
14. The worker inserts the final prediction row into `predictions`.
15. The worker marks the job as `completed`.
16. The frontend keeps polling until the result is available, then displays the prediction and artifact images.

---

## Artifact Storage

Generated files are created locally inside the worker first:

```text
data/YYYY/MM/DD/jp2/
data/YYYY/MM/DD/full_disk/
data/YYYY/MM/DD/heat_maps/
data/YYYY/MM/DD/active_regions/
```

The worker then uploads them to MinIO:

```text
predictions/{prediction_id}/jp2/
predictions/{prediction_id}/full_disk/
predictions/{prediction_id}/heat_maps/
predictions/{prediction_id}/active_regions/
```

`prediction_id` is the database primary key from the `predictions` table.

The database stores MinIO object paths. The frontend turns those object paths into browser URLs using:

```text
NEXT_PUBLIC_ARTIFACT_BASE_URL
```
