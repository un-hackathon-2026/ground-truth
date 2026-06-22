"use client";

import { useRef, useState } from "react";
import { Download } from "lucide-react";
import {
  BarChart, Bar,
  LineChart, Line,
  AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

type ChartType = "Bar Chart" | "Line Chart" | "Area Chart";

const CHART_TYPES: ChartType[] = ["Bar Chart", "Line Chart", "Area Chart"];

// Placeholder time-series data — replaced by real fetch in a future iteration
const PLACEHOLDER_DATA = [
  { year: "2020", value: 42.1 },
  { year: "2021", value: 39.4 },
  { year: "2022", value: 36.8 },
  { year: "2023", value: 34.5 },
  { year: "2024", value: 32.0 },
];

interface LoadedProps {
  title: string;
  dataset: string;
  country: string;
}

function ChartRenderer({
  type,
  data,
  citations,
  dataset,
}: {
  type: ChartType;
  data: typeof PLACEHOLDER_DATA;
  citations: boolean;
  dataset: string;
}) {
  const commonAxis = (
    <>
      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
      <XAxis dataKey="year" tick={{ fontSize: 12, fill: "#6b7280" }} axisLine={{ stroke: "#e5e7eb" }} tickLine={false} />
      <YAxis tick={{ fontSize: 12, fill: "#6b7280" }} axisLine={false} tickLine={false} width={40} />
      <Tooltip
        contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 12 }}
        cursor={{ fill: "rgba(59,130,246,0.05)" }}
      />
      {citations && <Legend wrapperStyle={{ fontSize: 11, color: "#9ca3af" }} formatter={() => `Source: ${dataset}`} />}
    </>
  );

  if (type === "Line Chart") {
    return (
      <LineChart data={data}>
        {commonAxis}
        <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2.5} dot={{ r: 4, fill: "#3b82f6" }} activeDot={{ r: 6 }} />
      </LineChart>
    );
  }
  if (type === "Area Chart") {
    return (
      <AreaChart data={data}>
        {commonAxis}
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.15} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2.5} fill="url(#areaGrad)" />
      </AreaChart>
    );
  }
  // Bar Chart (default)
  return (
    <BarChart data={data}>
      {commonAxis}
      <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
    </BarChart>
  );
}

function LoadedState({ title, dataset, country }: LoadedProps) {
  const [chartType, setChartType] = useState<ChartType>("Bar Chart");
  const [citations, setCitations] = useState(true);
  const chartRef = useRef<HTMLDivElement>(null);

  const downloadChart = () => {
    const svgEl = chartRef.current?.querySelector("svg");
    if (!svgEl) return;
    const serialized = new XMLSerializer().serializeToString(svgEl);
    const blob = new Blob([serialized], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.replace(/\s+/g, "_")}.svg`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
      {/* Header row */}
      <div className="flex items-start justify-between gap-4 mb-6 flex-wrap">
        <div>
          <h2 className="text-base font-bold text-gray-900">{title}</h2>
          <p className="text-xs text-gray-400 font-mono mt-0.5">{dataset} · {country}</p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {/* Citations checkbox */}
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={citations}
              onChange={(e) => setCitations(e.target.checked)}
              className="w-4 h-4 rounded accent-blue-600 cursor-pointer"
            />
            <span className="text-sm text-gray-700 font-medium">Include Citations</span>
          </label>

          {/* Chart type dropdown */}
          <select
            value={chartType}
            onChange={(e) => setChartType(e.target.value as ChartType)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
          >
            {CHART_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>

          {/* Download button */}
          <button
            onClick={downloadChart}
            title="Download chart as SVG"
            className="flex items-center gap-1.5 text-sm text-gray-600 border border-gray-200 rounded-lg px-3 py-1.5 hover:bg-gray-50 transition-colors"
          >
            <Download className="w-4 h-4" strokeWidth={2} />
            Download
          </button>
        </div>
      </div>

      {/* Chart */}
      <div ref={chartRef} className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <ChartRenderer
            type={chartType}
            data={PLACEHOLDER_DATA}
            citations={citations}
            dataset={dataset}
          />
        </ResponsiveContainer>
      </div>

      {/* Citation watermark */}
      {citations && (
        <p className="text-xs text-gray-400 mt-3 text-right">
          Source: UN Data Commons · {dataset} · Placeholder data
        </p>
      )}
    </div>
  );
}

// ─── Empty state ─────────────────────────────────────────────────────────────

interface EmptyProps {
  onLoad: (datasetId: string) => void;
}

function EmptyState({ onLoad }: EmptyProps) {
  const [input, setInput] = useState("");

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm">
      <div className="flex flex-col items-center justify-center py-20 px-8 text-center">
        <div className="w-14 h-14 rounded-full bg-blue-50 flex items-center justify-center mb-5">
          <svg className="w-7 h-7 text-blue-500" fill="none" stroke="currentColor" strokeWidth={1.75} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 3v18h18M9 17V9m4 8v-5m4 5V5" />
          </svg>
        </div>
        <h2 className="text-lg font-bold text-gray-900 mb-1">Policy Dashboard</h2>
        <p className="text-sm text-gray-500 mb-8 max-w-sm">
          Enter a UN Data Commons dataset ID or arrive here from the Trust Filter to begin.
        </p>

        <div className="w-full max-w-md space-y-3">
          <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider text-left">
            Dataset ID or API Endpoint
          </label>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && input.trim() && onLoad(input.trim())}
            placeholder="e.g., sdg/SH_H2O_SAFE"
            className="w-full px-4 py-3 border border-gray-300 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm"
          />
          <button
            onClick={() => input.trim() && onLoad(input.trim())}
            disabled={!input.trim()}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
          >
            Load Data
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main export ─────────────────────────────────────────────────────────────

interface Props {
  dataset?: string;
  country?: string;
  name?: string;
}

export default function VisualizationCard({ dataset, country, name }: Props) {
  const [manualDataset, setManualDataset] = useState<string | null>(null);

  const effectiveDataset = dataset ?? manualDataset;

  if (!effectiveDataset) {
    return <EmptyState onLoad={setManualDataset} />;
  }

  const displayName = name
    ? `${name} (${country ?? effectiveDataset})`
    : effectiveDataset;

  return (
    <LoadedState
      title={displayName}
      dataset={effectiveDataset}
      country={country ?? ""}
    />
  );
}
