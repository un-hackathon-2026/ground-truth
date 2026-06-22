"use client";

import { useState } from "react";
import type { CandidateOption } from "@/types/pipeline";

interface Props {
  topic: string;
  geography: string;
  options: CandidateOption[];
  /** Set once the user has confirmed — freezes the UI */
  frozenSelection?: string[];
  onSelect?: (codes: string[], selectionText: string) => void;
}

export default function DatasetSelector({
  topic,
  geography,
  options,
  frozenSelection,
  onSelect,
}: Props) {
  const frozen = frozenSelection !== undefined;
  // Pre-select if there's exactly one candidate
  const [selected, setSelected] = useState<string[]>(
    options.length === 1 ? [options[0].indicator_code] : []
  );

  const toggle = (code: string) => {
    if (frozen) return;
    setSelected((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    );
  };

  const confirm = () => {
    if (selected.length === 0 || !onSelect) return;
    const names = options
      .filter((o) => selected.includes(o.indicator_code))
      .map((o) => o.indicator_name)
      .join(", ");
    onSelect(selected, names);
  };

  const active = frozen ? frozenSelection! : selected;

  if (options.length === 0) {
    return (
      <p className="text-sm text-gray-500 italic">
        No matching datasets found in the UN Commons for this query.
      </p>
    );
  }

  return (
    <div>
      <p className="text-sm text-gray-600 mb-3">
        Found{" "}
        <span className="font-semibold">{options.length}</span>{" "}
        dataset{options.length !== 1 ? "s" : ""} for{" "}
        <span className="font-semibold">{topic}</span> in{" "}
        <span className="font-semibold">{geography}</span>.{" "}
        {frozen ? "You selected:" : "Select one or more to evaluate:"}
      </p>

      <div className="space-y-2">
        {options.map((opt) => {
          const isSelected = active.includes(opt.indicator_code);
          return (
            <button
              key={opt.indicator_code}
              onClick={() => toggle(opt.indicator_code)}
              disabled={frozen}
              className={[
                "w-full text-left p-3.5 rounded-xl border-2 transition-all",
                isSelected
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200 bg-white hover:border-blue-300",
                frozen ? "cursor-default" : "cursor-pointer",
              ].join(" ")}
            >
              <div className="flex items-start gap-3">
                {/* Custom radio/checkbox indicator */}
                <div
                  className={[
                    "mt-0.5 w-4 h-4 rounded-full border-2 flex-shrink-0 flex items-center justify-center",
                    isSelected ? "border-blue-600 bg-blue-600" : "border-gray-400",
                  ].join(" ")}
                >
                  {isSelected && (
                    <div className="w-1.5 h-1.5 rounded-full bg-white" />
                  )}
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-gray-900">
                    {opt.indicator_name}
                  </p>
                  <p className="text-xs font-mono text-gray-400 mt-0.5 truncate">
                    {opt.indicator_code}
                  </p>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {!frozen && (
        <button
          onClick={confirm}
          disabled={selected.length === 0}
          className={[
            "mt-3 w-full py-2.5 rounded-xl text-sm font-semibold transition-colors",
            selected.length > 0
              ? "bg-blue-600 text-white hover:bg-blue-700"
              : "bg-gray-100 text-gray-400 cursor-not-allowed",
          ].join(" ")}
        >
          {selected.length === 0
            ? "Select a dataset to continue"
            : `Evaluate ${selected.length} dataset${selected.length > 1 ? "s" : ""}`}
        </button>
      )}
    </div>
  );
}
