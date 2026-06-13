import type { Prediction } from "@/lib/types";

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
