import { NextRequest, NextResponse } from "next/server";
import { runPython } from "@/lib/python";

export async function POST(req: NextRequest) {
  const { dataset, country } = await req.json();
  if (!dataset?.trim() || !country?.trim()) {
    return NextResponse.json({ error: "dataset and country are required" }, { status: 400 });
  }
  try {
    const raw = await runPython("src.run_series", { dataset, country }, 60_000);
    return NextResponse.json(JSON.parse(raw));
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
