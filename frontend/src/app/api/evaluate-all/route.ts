import { NextRequest, NextResponse } from "next/server";
import { runPython } from "@/lib/python";

export async function POST(req: NextRequest) {
  const { query, context } = await req.json();
  if (!query?.trim()) {
    return NextResponse.json({ error: "query is required" }, { status: 400 });
  }
  try {
    const raw = await runPython("src.run_evaluate_all", { query, context: context ?? "" }, 180_000);
    return NextResponse.json(JSON.parse(raw));
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
