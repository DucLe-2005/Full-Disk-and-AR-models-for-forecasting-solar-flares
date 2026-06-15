import { NextResponse } from "next/server";

const DEFAULT_MINIO_BASE_URL = "http://localhost:9000/solar-artifacts";

export async function GET(request: Request) {
  const key = new URL(request.url).searchParams.get("key")?.replace(/^\/+/, "");

  if (!key || !key.startsWith("predictions/") || key.includes("..")) {
    return NextResponse.json({ detail: "Invalid artifact key" }, { status: 400 });
  }

  const baseUrl = process.env.MINIO_ARTIFACT_BASE_URL || DEFAULT_MINIO_BASE_URL;
  const objectUrl = `${baseUrl.replace(/\/$/, "")}/${key
    .split("/")
    .map(encodeURIComponent)
    .join("/")}`;

  try {
    const response = await fetch(objectUrl, { cache: "no-store" });
    if (!response.ok || !response.body) {
      return NextResponse.json(
        { detail: response.status === 404 ? "Artifact not found" : "Artifact storage request failed" },
        { status: response.status }
      );
    }

    return new Response(response.body, {
      status: 200,
      headers: {
        "Content-Type": response.headers.get("content-type") || "application/octet-stream",
        "Cache-Control": "public, max-age=3600"
      }
    });
  } catch {
    return NextResponse.json({ detail: "Artifact storage is unavailable" }, { status: 502 });
  }
}
