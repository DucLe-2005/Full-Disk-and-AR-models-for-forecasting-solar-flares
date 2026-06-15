import { NextResponse } from "next/server";

import { fetchPredictionHistory } from "@/lib/api";

export async function GET(request: Request) {
  try {
    const history = await fetchPredictionHistory(new URL(request.url).searchParams.toString());
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
