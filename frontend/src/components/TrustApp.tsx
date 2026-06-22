"use client";

import { useState } from "react";
import ChatContainer from "./ChatContainer";
import AnalysisConfig from "./AnalysisConfig";
import type { CandidateList, MultiDatasetReport } from "@/types/pipeline";

// ─── Message types ─────────────────────────────────────────────────────────────

export type ChatMessage =
  | { kind: "user"; text: string }
  | { kind: "candidates"; data: CandidateList; frozenCodes?: string[] }
  | { kind: "selection"; text: string }
  | { kind: "report"; data: MultiDatasetReport }
  | { kind: "error"; text: string };

type Stage =
  | "idle"
  | "loading_candidates"
  | "awaiting_selection"
  | "loading_evaluation"
  | "complete"
  | "error";

export type ReadinessStatus = "PENDING" | "EVALUATING" | "READY";

function stageToReadiness(stage: Stage): ReadinessStatus {
  if (stage === "complete") return "READY";
  if (stage === "idle" || stage === "error") return "PENDING";
  return "EVALUATING";
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function TrustApp() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [stage, setStage] = useState<Stage>("idle");
  const [query, setQuery] = useState("");

  // Preserved across phases so evaluate can reuse them without a second LLM call
  const [pendingQuery, setPendingQuery] = useState("");
  const [pendingLabels, setPendingLabels] = useState<Record<string, string>>({});

  const isLoading =
    stage === "loading_candidates" || stage === "loading_evaluation";

  // ── Phase 1: Discover candidates ────────────────────────────────────────────
  const handleAnalyze = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed || isLoading) return;

    setPendingQuery(trimmed);
    setMessages((prev) => [...prev, { kind: "user", text: trimmed }]);
    setStage("loading_candidates");

    try {
      const res = await fetch("/api/candidates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed }),
      });
      const data: CandidateList & { error?: string } = await res.json();

      if (!res.ok || data.error) {
        setMessages((prev) => [
          ...prev,
          { kind: "error", text: data.error ?? "Failed to fetch candidates." },
        ]);
        setStage("error");
        return;
      }

      if (data.parse_error) {
        setMessages((prev) => [
          ...prev,
          { kind: "error", text: data.parse_error! },
        ]);
        setStage("error");
        return;
      }

      const labels: Record<string, string> = {};
      for (const o of data.options) labels[o.indicator_code] = o.indicator_name;
      setPendingLabels(labels);

      setMessages((prev) => [...prev, { kind: "candidates", data }]);
      setStage("awaiting_selection");
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { kind: "error", text: String(err) },
      ]);
      setStage("error");
    }
  };

  // ── Phase 2: Evaluate selected datasets ─────────────────────────────────────
  const handleSelectDatasets = async (
    selectedCodes: string[],
    selectionText: string
  ) => {
    // Freeze the last candidates message
    setMessages((prev) =>
      prev.map((m, i) =>
        i === prev.length - 1 && m.kind === "candidates"
          ? { ...m, frozenCodes: selectedCodes }
          : m
      )
    );

    setMessages((prev) => [
      ...prev,
      { kind: "selection", text: selectionText },
    ]);
    setStage("loading_evaluation");

    try {
      const res = await fetch("/api/evaluate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: pendingQuery,
          selected_codes: selectedCodes,
          labels: pendingLabels,
        }),
      });
      const data: MultiDatasetReport & { error?: string } = await res.json();

      if (!res.ok || data.error) {
        setMessages((prev) => [
          ...prev,
          { kind: "error", text: data.error ?? "Evaluation failed." },
        ]);
        setStage("error");
        return;
      }

      setMessages((prev) => [...prev, { kind: "report", data }]);
      setStage("complete");
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { kind: "error", text: String(err) },
      ]);
      setStage("error");
    }
  };

  // ── Suggestion pills trigger a brand-new analysis ───────────────────────────
  const handleQuerySuggestion = (label: string) => {
    setQuery(label);
    handleAnalyze(label);
  };

  return (
    <div className="flex flex-col gap-4">
      <ChatContainer
        messages={messages}
        isLoading={isLoading}
        onSelectDatasets={handleSelectDatasets}
        onQuerySuggestion={handleQuerySuggestion}
      />
      <AnalysisConfig
        query={query}
        onQueryChange={setQuery}
        onAnalyze={handleAnalyze}
        isAnalyzing={isLoading}
      />
    </div>
  );
}
