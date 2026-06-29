import { NextResponse } from "next/server";

import { createPredictionJob } from "@/lib/api";

function pad(value: number) {
  return String(value).padStart(2, "0");
}

function formatUtcHour(date: Date) {
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())} ${pad(
    date.getUTCHours()
  )}:00:00`;
}

export async function POST() {
  const now = new Date();
  now.setUTCMinutes(0, 0, 0);
  const helioviewerDate = formatUtcHour(now);

  try {
    const result = await createPredictionJob(helioviewerDate);
    return NextResponse.json({
      ...result,
      helioviewer_date: helioviewerDate
    });
  } catch (error) {
    return NextResponse.json(
      {
        detail: error instanceof Error ? error.message : "Failed to create current-hour prediction job",
        helioviewer_date: helioviewerDate
      },
      {
        status: 502
      }
    );
  }
}
