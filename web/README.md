# Solar Flare Web

Next.js frontend for the FastAPI solar flare prediction service.

## Setup

```powershell
cd web
npm install
```

Create `web/.env.local` if the API is not running on `http://localhost:8000`:

```env
FASTAPI_BASE_URL=http://localhost:8000
NEXT_PUBLIC_ARTIFACT_BASE_URL=http://localhost:9000/solar-artifacts
```

## Run

```powershell
npm run dev
```

Open `http://localhost:3000`.
