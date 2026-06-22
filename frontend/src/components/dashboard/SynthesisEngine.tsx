"use client";

import { useState } from "react";
import { FileText, Download, Loader2, ChevronDown, ChevronUp } from "lucide-react";
import { useTokens } from "@/lib/tokenContext";

interface Props {
  dataset?: string;
  country?: string;
  name?: string;
  onStatusChange?: (status: "pending" | "loading" | "done") => void;
}

export default function SynthesisEngine({ dataset, country, name, onStatusChange }: Props) {
  const { addUsage } = useTokens();
  const [instructions, setInstructions] = useState("");
  const [showCustom, setShowCustom] = useState(false);
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [memo, setMemo] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const hasDataset = !!(dataset && country);

  const setAndBubble = (s: "idle" | "loading" | "done" | "error") => {
    setStatus(s);
    if (s === "loading") onStatusChange?.("loading");
    else if (s === "done") onStatusChange?.("done");
  };

  const handleGenerate = async () => {
    if (!hasDataset) return;
    setAndBubble("loading");
    setMemo("");
    setErrorMsg("");

    try {
      const res = await fetch("/api/synthesize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset, country, name, instructions: instructions.trim() }),
      });
      const data: { memo?: string; error?: string; usage?: Record<string, number> } = await res.json();

      if (!res.ok || data.error) {
        setErrorMsg(data.error ?? "Failed to generate document.");
        setAndBubble("error");
        return;
      }

      if (data.usage) addUsage(data.usage);
      setMemo(data.memo ?? "");
      setAndBubble("done");
    } catch (err) {
      setErrorMsg(String(err));
      setAndBubble("error");
    }
  };

  const handleDownload = () => {
    const blob = new Blob([memo], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const safeName = (name ?? dataset ?? "policy_brief").replace(/[^a-z0-9]/gi, "_");
    a.download = `${safeName}_evidence_brief.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
          <FileText className="w-4 h-4 text-blue-600" strokeWidth={2} />
        </div>
        <div>
          <h2 className="text-base font-bold text-gray-900">Evidence Brief Generator</h2>
          {hasDataset && (
            <p className="text-xs text-gray-400 font-mono mt-0.5">{name ?? dataset} · {country}</p>
          )}
        </div>
      </div>

      {!hasDataset ? (
        <p className="text-sm text-gray-400 italic">
          Load a dataset above to enable brief generation.
        </p>
      ) : (
        <>
          {/* What will be generated */}
          <div className="bg-blue-50 border border-blue-100 rounded-xl px-4 py-3 text-xs text-blue-800 space-y-1">
            <p className="font-semibold">Auto-generated brief will include:</p>
            <ul className="list-disc list-inside space-y-0.5 text-blue-700">
              <li>Executive summary grounded in observed data points</li>
              <li>Key findings with specific years and values cited</li>
              <li>Trend analysis and policy implications</li>
              <li>Data caveats, freshness, and source provenance appendix</li>
            </ul>
          </div>

          {/* Optional custom focus */}
          <div>
            <button
              type="button"
              onClick={() => setShowCustom((v) => !v)}
              className="flex items-center gap-1.5 text-xs font-semibold text-gray-500 hover:text-gray-800 transition-colors"
            >
              {showCustom
                ? <ChevronUp className="w-3.5 h-3.5" strokeWidth={2.5} />
                : <ChevronDown className="w-3.5 h-3.5" strokeWidth={2.5} />}
              Add custom focus instructions (optional)
            </button>
            {showCustom && (
              <textarea
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="e.g., Focus on the last 5 years and frame findings for the Minister of Health…"
                rows={4}
                className="mt-2 w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            )}
          </div>

          {/* Generate button */}
          <button
            onClick={handleGenerate}
            disabled={status === "loading"}
            className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
          >
            {status === "loading" && <Loader2 className="w-4 h-4 animate-spin" strokeWidth={2} />}
            {status === "loading" ? "Generating evidence brief…" : "Generate Evidence Brief"}
          </button>

          {status === "error" && (
            <p className="text-xs text-red-600 font-mono">{errorMsg}</p>
          )}

          {status === "done" && memo && (
            <div className="border border-gray-200 rounded-xl overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-200">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Evidence Brief · UN Data Commons
                </span>
                <button
                  onClick={handleDownload}
                  className="flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-800 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" strokeWidth={2} />
                  Download .txt
                </button>
              </div>
              <pre className="p-5 text-xs text-gray-700 font-mono leading-relaxed whitespace-pre-wrap bg-white overflow-auto max-h-[480px]">
                {memo}
              </pre>
            </div>
          )}
        </>
      )}
    </div>
  );
}
