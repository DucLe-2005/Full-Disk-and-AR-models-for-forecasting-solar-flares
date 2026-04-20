import { NextResponse } from "next/server";

import { createPredictionJob } from "@/lib/api";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const helioviewerDate = String(body.helioviewer_date ?? "");

    if (!helioviewerDate) {
      return NextResponse.json(
        {
          detail: "helioviewer_date is required"
        },
        {
          status: 422
        }
      );
    }

    const job = await createPredictionJob(helioviewerDate);
    return NextResponse.json(job);
  } catch (error) {
    return NextResponse.json(
      {
        detail: error instanceof Error ? error.message : "Failed to create prediction job"
      },
      {
        status: 502
      }
    );
  }
}
