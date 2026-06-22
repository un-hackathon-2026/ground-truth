import { NextRequest, NextResponse } from "next/server";
import { runPython } from "@/lib/python";

export async function POST(req: NextRequest) {
  const { dataset, country, name, instructions } = await req.json();
  if (!dataset?.trim() || !country?.trim() || !instructions?.trim()) {
    return NextResponse.json(
      { error: "dataset, country, and instructions are required" },
      { status: 400 }
    );
  }
  try {
    const raw = await runPython(
      "src.run_synthesize",
      { dataset, country, name: name ?? dataset, instructions },
      120_000
    );
    return NextResponse.json(JSON.parse(raw));
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}
