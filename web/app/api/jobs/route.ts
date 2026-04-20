import { NextResponse } from "next/server";

import { createPredictionJob, createPredictionJobRange } from "@/lib/api";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const startTime = String(body.start_time ?? "");
    const endTime = String(body.end_time ?? "");

    if (startTime || endTime) {
      if (!startTime || !endTime) {
        return NextResponse.json(
          {
            detail: "start_time and end_time are required for range requests"
          },
          {
            status: 422
          }
        );
      }

      const result = await createPredictionJobRange(startTime, endTime);
      return NextResponse.json(result);
    }

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
