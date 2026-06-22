"use client";

import { useEffect, useRef } from "react";
import { ShieldCheck } from "lucide-react";
import DatasetSelector from "./chat/DatasetSelector";
import TrustReport from "./chat/TrustReport";
import type { ChatMessage } from "./TrustApp";

interface Props {
  messages: ChatMessage[];
  isLoading: boolean;
  onSelectDatasets: (codes: string[], selectionText: string) => void;
  onQuerySuggestion: (query: string) => void;
}

// ─── Shared wrappers ──────────────────────────────────────────────────────────

function UserBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <div className="bg-blue-600 text-white rounded-2xl rounded-br-sm px-5 py-3 max-w-sm shadow-sm">
        <p className="text-sm leading-relaxed">{text}</p>
      </div>
    </div>
  );
}

function AgentBubble({ children }: { children: React.ReactNode }) {
  return (
    <div className="max-w-full">
      <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-5 py-4 shadow-sm">
        {children}
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function ChatContainer({
  messages,
  isLoading,
  onSelectDatasets,
  onQuerySuggestion,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm">

      {/* Agent header */}
      <div className="flex items-center gap-4 px-6 py-5">
        <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
          <ShieldCheck className="w-6 h-6 text-blue-600" strokeWidth={1.75} />
        </div>
        <div>
          <h2 className="text-base font-semibold text-gray-900 leading-tight">
            Data Gatekeeper Agent
          </h2>
          <p className="text-sm text-gray-500 leading-tight mt-0.5">
            Evaluating APIs against UN Schema
          </p>
        </div>
      </div>

      <div className="h-px bg-gray-100" />

      {/* Message thread */}
      <div className="px-6 py-6 space-y-4 min-h-52">

        {/* Greeting — always shown */}
        <AgentBubble>
          <p className="text-sm text-gray-800 leading-relaxed">
            Hello. I am the Trust &amp; Viability Co-pilot. What metric or topic
            are you looking to analyze?
          </p>
        </AgentBubble>

        {messages.map((msg, i) => {
          const isLastCandidates =
            msg.kind === "candidates" &&
            messages.findLastIndex((m) => m.kind === "candidates") === i;

          switch (msg.kind) {
            case "user":
              return <UserBubble key={i} text={msg.text} />;

            case "candidates":
              return (
                <AgentBubble key={i}>
                  <DatasetSelector
                    topic={msg.data.topic}
                    geography={msg.data.geography}
                    options={msg.data.options}
                    frozenSelection={
                      // Freeze if this is not the last candidates msg, or
                      // if the user has already confirmed a selection
                      msg.frozenCodes
                    }
                    onSelect={
                      isLastCandidates && !msg.frozenCodes
                        ? onSelectDatasets
                        : undefined
                    }
                  />
                </AgentBubble>
              );

            case "selection":
              return <UserBubble key={i} text={msg.text} />;

            case "report":
              return (
                <AgentBubble key={i}>
                  <TrustReport
                    data={msg.data}
                    onQuerySuggestion={onQuerySuggestion}
                  />
                </AgentBubble>
              );

            case "error":
              return (
                <AgentBubble key={i}>
                  <div className="flex gap-2 items-start">
                    <div className="w-2 h-2 mt-1.5 rounded-full bg-red-500 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-semibold text-red-700 mb-0.5">
                        Pipeline error
                      </p>
                      <p className="text-xs text-red-600 font-mono">{msg.text}</p>
                    </div>
                  </div>
                </AgentBubble>
              );

            default:
              return null;
          }
        })}

        {/* Loading indicator */}
        {isLoading && (
          <AgentBubble>
            <div className="flex items-center gap-3">
              <span className="flex gap-1">
                {[0, 150, 300].map((delay) => (
                  <span
                    key={delay}
                    className="block w-2 h-2 rounded-full bg-blue-400 animate-bounce"
                    style={{ animationDelay: `${delay}ms` }}
                  />
                ))}
              </span>
              <span className="text-xs text-blue-600 font-medium">
                Running evaluation pipeline…
              </span>
            </div>
          </AgentBubble>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
