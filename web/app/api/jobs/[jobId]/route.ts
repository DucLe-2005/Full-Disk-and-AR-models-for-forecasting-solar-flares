import { NextResponse } from "next/server";

import { fetchPredictionJob } from "@/lib/api";

type RouteContext = {
  params: Promise<{
    jobId: string;
  }>;
};

export async function GET(_request: Request, context: RouteContext) {
  try {
    const { jobId } = await context.params;
    const job = await fetchPredictionJob(jobId);
    return NextResponse.json(job);
  } catch (error) {
    return NextResponse.json(
      {
        detail: error instanceof Error ? error.message : "Failed to fetch job status"
      },
      {
        status: 502
      }
    );
  }
}
