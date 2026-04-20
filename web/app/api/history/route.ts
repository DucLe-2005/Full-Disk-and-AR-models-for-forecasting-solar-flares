import { NextResponse } from "next/server";

import { fetchPredictionHistory } from "@/lib/api";

export async function GET() {
  try {
    const history = await fetchPredictionHistory();
    return NextResponse.json(history);
  } catch (error) {
    return NextResponse.json(
      {
        detail: error instanceof Error ? error.message : "Failed to fetch prediction history"
      },
      {
        status: 502
      }
    );
  }
}
