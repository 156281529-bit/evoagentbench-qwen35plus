import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

async function forward(request: NextRequest, path: string, init?: RequestInit) {
  try {
    const port = request.nextUrl.searchParams.get("native") === "1" ? 39915 : 39913;
    const result = await fetch(`http://127.0.0.1:${port}/${path}`, { ...init, cache: "no-store" });
    return new Response(await result.text(), {
      status: result.status, headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  } catch {
    return Response.json({ error: "请启动本机十题执行器" }, { status: 503 });
  }
}

export function GET(request: NextRequest) {
  return forward(request, request.nextUrl.searchParams.has("latest") ? "latest" : "workflow");
}

export async function POST(request: NextRequest) {
  const origin = request.headers.get("origin");
  if (origin && new URL(origin).host !== request.headers.get("host"))
    return Response.json({ error: "来源无效" }, { status: 403 });
  const payload = await request.text();
  if (payload.length > 16384) return new Response(null, { status: 413 });
  return forward(request, "run", { method: "POST", body: payload, headers: { "Content-Type": "application/json" } });
}
