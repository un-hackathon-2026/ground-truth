"use client";

import { useState } from "react";
import { FileText, Download, Loader2 } from "lucide-react";
import { useTokens } from "@/lib/tokenContext";

interface Props {
  dataset?: string;
  country?: string;
  name?: string;
}

export default function SynthesisEngine({ dataset, country, name }: Props) {
  const { addUsage } = useTokens();
  const [instructions, setInstructions] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [memo, setMemo] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const hasDataset = !!(dataset && country);

  const handleGenerate = async () => {
    if (!instructions.trim() || !hasDataset) return;
    setStatus("loading");
    setMemo("");
    setErrorMsg("");

    try {
      const res = await fetch("/api/synthesize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset, country, name, instructions }),
      });
      const data: { memo?: string; error?: string; usage?: Record<string, number> } = await res.json();

      if (!res.ok || data.error) {
        setErrorMsg(data.error ?? "Failed to generate document.");
        setStatus("error");
        return;
      }

      if (data.usage) addUsage(data.usage);
      setMemo(data.memo ?? "");
      setStatus("done");
    } catch (err) {
      setErrorMsg(String(err));
      setStatus("error");
    }
  };

  const handleDownload = () => {
    const blob = new Blob([memo], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const safeName = (name ?? dataset ?? "policy_memo").replace(/[^a-z0-9]/gi, "_");
    a.download = `${safeName}_memo.txt`;
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
          <h2 className="text-base font-bold text-gray-900">Automated Synthesis &amp; Interpretation</h2>
          {hasDataset && (
            <p className="text-xs text-gray-400 font-mono mt-0.5">
              {name ?? dataset} · {country}
            </p>
          )}
        </div>
      </div>

      {!hasDataset ? (
        <p className="text-sm text-gray-400 italic">
          Load a dataset above to enable document generation.
        </p>
      ) : (
        <>
          {/* Instructions input */}
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Instructions for Synthesis Agent
            </label>
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="e.g., Write a 1-page policy brief for the Minister of Health highlighting the trend in mortality rates…"
              rows={5}
              className="w-full px-4 py-3 border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Generate button */}
          <div className="flex justify-end">
            <button
              onClick={handleGenerate}
              disabled={!instructions.trim() || status === "loading"}
              className="flex items-center gap-2 px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
            >
              {status === "loading" && <Loader2 className="w-4 h-4 animate-spin" strokeWidth={2} />}
              {status === "loading" ? "Generating…" : "Generate Document"}
            </button>
          </div>

          {/* Error */}
          {status === "error" && (
            <p className="text-xs text-red-600 font-mono">{errorMsg}</p>
          )}

          {/* Generated memo */}
          {status === "done" && memo && (
            <div className="border border-gray-200 rounded-xl overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2.5 bg-gray-50 border-b border-gray-200">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Generated Policy Document
                </span>
                <button
                  onClick={handleDownload}
                  className="flex items-center gap-1.5 text-xs font-medium text-blue-600 hover:text-blue-800 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" strokeWidth={2} />
                  Download
                </button>
              </div>
              <pre className="p-5 text-xs text-gray-700 font-mono leading-relaxed whitespace-pre-wrap bg-white overflow-auto max-h-96">
                {memo}
              </pre>
            </div>
          )}
        </>
      )}
    </div>
  );
}
