"use client";

import { useState, useEffect } from "react";
import ChatContainer from "./ChatContainer";
import AnalysisConfig from "./AnalysisConfig";
import type { ClarificationQuestion, MultiDatasetReport } from "@/types/pipeline";

// ─── Message types ─────────────────────────────────────────────────────────────

export type ChatMessage =
  | { kind: "user"; text: string }
  | { kind: "clarification"; data: ClarificationQuestion; frozenAnswer?: string }
  | { kind: "clarification_response"; text: string }
  | { kind: "report"; data: MultiDatasetReport }
  | { kind: "error"; text: string };

export type Stage =
  | "idle"
  | "loading_clarification"
  | "awaiting_clarification"
  | "loading_evaluation"
  | "complete"
  | "error";

const STORAGE_KEY = "ground-truth:state";

function readStorage<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return fallback;
    const parsed = JSON.parse(raw);
    return (parsed[key] as T) ?? fallback;
  } catch {
    return fallback;
  }
}

function restoreStage(msgs: ChatMessage[]): Stage {
  if (!msgs.length) return "idle";
  const last = msgs[msgs.length - 1];
  if (last.kind === "report") return "complete";
  if (last.kind === "error") return "error";
  if (last.kind === "clarification" && !last.frozenAnswer) return "awaiting_clarification";
  // user / clarification_response at end = pipeline was interrupted mid-flight
  return "idle";
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function TrustApp() {
  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    readStorage<ChatMessage[]>("messages", [])
  );
  const [query, setQuery] = useState<string>(() =>
    readStorage<string>("query", "")
  );
  const [pendingQuery, setPendingQuery] = useState<string>(() =>
    readStorage<string>("pendingQuery", "")
  );

  const [stage, setStage] = useState<Stage>(() =>
    restoreStage(readStorage<ChatMessage[]>("messages", []))
  );

  const isAnalyzing =
    stage === "loading_clarification" || stage === "loading_evaluation";

  useEffect(() => {
    try {
      sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({ messages, query, pendingQuery })
      );
    } catch {
      // ignore quota errors
    }
  }, [messages, query, pendingQuery]);

  // ── Phase 0: Ask a clarifying question ─────────────────────────────────────
  const handleAnalyze = async (q: string) => {
    const trimmed = q.trim();
    if (!trimmed || isAnalyzing) return;

    setPendingQuery(trimmed);
    setMessages((prev) => [...prev, { kind: "user", text: trimmed }]);
    setStage("loading_clarification");

    try {
      const res = await fetch("/api/clarify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed }),
      });
      const data: ClarificationQuestion & { error?: string } = await res.json();

      if (!res.ok || data.error) {
        setMessages((prev) => [
          ...prev,
          { kind: "error", text: data.error ?? "Failed to generate clarification." },
        ]);
        setStage("error");
        return;
      }

      setMessages((prev) => [...prev, { kind: "clarification", data }]);
      setStage("awaiting_clarification");
    } catch (err) {
      setMessages((prev) => [...prev, { kind: "error", text: String(err) }]);
      setStage("error");
    }
  };

  // ── Phase 1+2: Evaluate all datasets for the refined query ─────────────────
  const handleClarificationConfirm = async (answer: string) => {
    // Freeze the clarification card
    setMessages((prev) =>
      prev.map((m, i) =>
        i === prev.length - 1 && m.kind === "clarification"
          ? { ...m, frozenAnswer: answer }
          : m
      )
    );
    setMessages((prev) => [
      ...prev,
      { kind: "clarification_response", text: answer },
    ]);
    setStage("loading_evaluation");

    try {
      const res = await fetch("/api/evaluate-all", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: pendingQuery, context: answer }),
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

      if (data.parse_error) {
        setMessages((prev) => [
          ...prev,
          { kind: "error", text: data.parse_error! },
        ]);
        setStage("error");
        return;
      }

      setMessages((prev) => [...prev, { kind: "report", data }]);
      setStage("complete");
    } catch (err) {
      setMessages((prev) => [...prev, { kind: "error", text: String(err) }]);
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
        stage={stage}
        onClarificationConfirm={handleClarificationConfirm}
        onQuerySuggestion={handleQuerySuggestion}
      />
      <AnalysisConfig
        query={query}
        onQueryChange={setQuery}
        onAnalyze={handleAnalyze}
        isAnalyzing={isAnalyzing}
      />
    </div>
  );
}
