import type { PredictionHistoryPage } from "@/lib/types";

const backendBaseUrl = process.env.FASTAPI_BASE_URL ?? "http://localhost:8000";

export async function fetchPredictionHistory(query: string): Promise<PredictionHistoryPage> {
  const suffix = query ? `?${query}` : "";
  const response = await fetch(`${backendBaseUrl}/history/${suffix}`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`History request failed with ${response.status}`);
  }

  return response.json();
}
