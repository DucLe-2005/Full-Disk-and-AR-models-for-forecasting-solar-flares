import type { JobRangeResponse, JobResponse, JobStatusResponse, Prediction } from "@/lib/types";

const backendBaseUrl = process.env.FASTAPI_BASE_URL ?? "http://localhost:8000";

export async function fetchPredictionHistory(): Promise<Prediction[]> {
  const response = await fetch(`${backendBaseUrl}/history/`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`History request failed with ${response.status}`);
  }

  return response.json();
}

export async function createPredictionJob(helioviewerDate: string): Promise<JobResponse> {
  const response = await fetch(`${backendBaseUrl}/predictions/jobs`, {
    method: "POST",
    headers: {
      "content-type": "application/json"
    },
    body: JSON.stringify({
      helioviewer_date: helioviewerDate
    })
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Job request failed with ${response.status}`);
  }

  return response.json();
}

export async function createPredictionJobRange(startTime: string, endTime: string): Promise<JobRangeResponse> {
  const response = await fetch(`${backendBaseUrl}/predictions/jobs/range`, {
    method: "POST",
    headers: {
      "content-type": "application/json"
    },
    body: JSON.stringify({
      start_time: startTime,
      end_time: endTime
    })
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Range job request failed with ${response.status}`);
  }

  return response.json();
}

export async function fetchPredictionJob(jobId: string): Promise<JobStatusResponse> {
  const response = await fetch(`${backendBaseUrl}/predictions/jobs/${jobId}`, {
    cache: "no-store"
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Job status request failed with ${response.status}`);
  }

  return response.json();
}
