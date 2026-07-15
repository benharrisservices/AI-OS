import { NextRequest, NextResponse } from "next/server";

/**
 * Server-side proxy for authenticated knowledge uploads.
 * AI_OS_API_KEY stays on the server — never exposed to the browser.
 */
export async function POST(req: NextRequest) {
  const apiBase = (
    process.env.NEXT_PUBLIC_AI_OS_API_URL ||
    (process.env.NODE_ENV === "production"
      ? "https://api.sedr.ca"
      : "http://127.0.0.1:8741")
  ).replace(/\/$/, "");

  const apiKey = process.env.AI_OS_API_KEY?.trim();
  const form = await req.formData();

  const headers: HeadersInit = {};
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${apiBase}/api/v1/imports/upload`, {
      method: "POST",
      headers,
      body: form,
      cache: "no-store",
    });
  } catch (err) {
    return NextResponse.json(
      {
        error: "Backend unavailable",
        detail: err instanceof Error ? err.message : String(err),
      },
      { status: 502 },
    );
  }

  const text = await upstream.text();
  let body: unknown = text;
  try {
    body = JSON.parse(text);
  } catch {
    /* keep raw text */
  }

  return NextResponse.json(body, { status: upstream.status });
}
