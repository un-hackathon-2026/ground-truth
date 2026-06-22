"use client";

import { Search } from "lucide-react";

interface Props {
  query: string;
  onQueryChange: (q: string) => void;
  onAnalyze: (query: string) => void;
  isAnalyzing: boolean;
}

export default function AnalysisConfig({
  query,
  onQueryChange,
  onAnalyze,
  isAnalyzing,
}: Props) {
  const handleSubmit = () => {
    if (!query.trim() || isAnalyzing) return;
    onAnalyze(query.trim());
  };

  return (
    <div className="flex gap-3">
      <div className="relative flex-1">
        <Search
          className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400"
          strokeWidth={2}
        />
        <input
          type="text"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          placeholder="child mortality rate in kenya 2020-2024"
          disabled={isAnalyzing}
          className="w-full pl-11 pr-4 py-3.5 bg-white border border-gray-300 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm disabled:opacity-60 disabled:cursor-not-allowed"
        />
      </div>
      <button
        onClick={handleSubmit}
        disabled={!query.trim() || isAnalyzing}
        className="px-7 py-3.5 bg-blue-600 text-white font-semibold text-sm rounded-xl hover:bg-blue-700 active:bg-blue-800 transition-colors shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {isAnalyzing ? "Running…" : "Analyze"}
      </button>
    </div>
  );
}
