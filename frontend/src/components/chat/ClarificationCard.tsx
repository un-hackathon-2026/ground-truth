"use client";

import { useState } from "react";
import { CheckCircle } from "lucide-react";
import type { ClarificationQuestion } from "@/types/pipeline";

interface Props {
  data: ClarificationQuestion;
  frozenAnswer?: string;
  onConfirm?: (answer: string) => void;
}

export default function ClarificationCard({ data, frozenAnswer, onConfirm }: Props) {
  const [selected, setSelected] = useState<string | null>(frozenAnswer ?? null);
  const isFrozen = frozenAnswer !== undefined;

  const handleConfirm = () => {
    if (!selected || isFrozen || !onConfirm) return;
    onConfirm(selected);
  };

  return (
    <div className="space-y-3">
      <p className="text-sm text-gray-800 leading-relaxed font-medium">
        {data.question}
      </p>

      <div className="flex flex-col gap-2">
        {data.options.map((opt, i) => {
          const isSelected = selected === opt.label;
          return (
            <button
              key={i}
              disabled={isFrozen}
              onClick={() => !isFrozen && setSelected(opt.label)}
              className={[
                "text-left w-full px-4 py-3 rounded-xl border-2 transition-all",
                isFrozen
                  ? isSelected
                    ? "border-blue-400 bg-blue-50 cursor-default"
                    : "border-gray-100 bg-gray-50 opacity-50 cursor-default"
                  : isSelected
                    ? "border-blue-500 bg-blue-50 shadow-sm"
                    : "border-gray-200 hover:border-blue-300 hover:bg-blue-50/50",
              ].join(" ")}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className={`text-sm font-semibold leading-tight ${isSelected ? "text-blue-800" : "text-gray-800"}`}>
                    {opt.label}
                  </p>
                  <p className={`text-xs mt-0.5 leading-relaxed ${isSelected ? "text-blue-600" : "text-gray-500"}`}>
                    {opt.description}
                  </p>
                </div>
                {isSelected && (
                  <CheckCircle className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" strokeWidth={2.5} />
                )}
              </div>
            </button>
          );
        })}
      </div>

      {!isFrozen && (
        <button
          disabled={!selected}
          onClick={handleConfirm}
          className="mt-1 w-full py-2.5 rounded-xl text-sm font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed bg-blue-600 hover:bg-blue-700 text-white"
        >
          Confirm &amp; Search Datasets
        </button>
      )}
    </div>
  );
}
