"use client";

import { useRef, useState, useEffect } from "react";
import { Download, FileDown, Loader2 } from "lucide-react";
import {
  BarChart, Bar,
  LineChart, Line,
  AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

type ChartType = "Bar Chart" | "Line Chart" | "Area Chart";

const CHART_TYPES: ChartType[] = ["Bar Chart", "Line Chart", "Area Chart"];

interface DataPoint {
  year: string;
  value: number;
}

interface SeriesResponse {
  rows: { year: number; value: number }[];
  unit?: string | null;
  source_org?: string | null;
  time_coverage?: string | null;
  methodology_note?: string | null;
  license_url?: string | null;
  last_updated?: string | null;
  error?: string;
}

// ─── Chart renderer ───────────────────────────────────────────────────────────

function ChartRenderer({
  type,
  data,
  unit,
  citations,
  dataset,
}: {
  type: ChartType;
  data: DataPoint[];
  unit: string;
  citations: boolean;
  dataset: string;
}) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tooltipFormatter = (value: any): [string, string] => [
    `${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}${unit ? ` ${unit}` : ""}`,
    "Value",
  ];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const labelFormatter = (label: any) => `Year: ${label}`;
  const yTickFormatter = (v: number) =>
    v >= 1_000_000
      ? `${(v / 1_000_000).toFixed(1)}M`
      : v >= 1_000
        ? `${(v / 1_000).toFixed(1)}k`
        : String(v);

  const commonAxis = (
    <>
      <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
      <XAxis dataKey="year" tick={{ fontSize: 12, fill: "#6b7280" }} axisLine={{ stroke: "#e5e7eb" }} tickLine={false} />
      <YAxis tick={{ fontSize: 12, fill: "#6b7280" }} axisLine={false} tickLine={false} width={50}
        tickFormatter={yTickFormatter} />
      <Tooltip
        contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb", fontSize: 12 }}
        cursor={{ fill: "rgba(59,130,246,0.05)" }}
        formatter={tooltipFormatter}
        labelFormatter={labelFormatter}
      />
      {citations && (
        <Legend wrapperStyle={{ fontSize: 11, color: "#9ca3af" }}
          formatter={() => `Source: ${dataset}`} />
      )}
    </>
  );

  if (type === "Line Chart") {
    return (
      <LineChart data={data}>
        {commonAxis}
        <Line type="monotone" dataKey="value" stroke="#3b82f6" strokeWidth={2.5}
          dot={{ r: 4, fill: "#3b82f6" }} activeDot={{ r: 6 }} />
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
  return (
    <BarChart data={data}>
      {commonAxis}
      <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
    </BarChart>
  );
}

// ─── Loaded state (has dataset + country) ─────────────────────────────────────

interface LoadedProps {
  title: string;
  dataset: string;
  country: string;
}

function LoadedState({ title, dataset, country }: LoadedProps) {
  const [chartType, setChartType] = useState<ChartType>("Bar Chart");
  const [citations, setCitations] = useState(true);
  const chartRef = useRef<HTMLDivElement>(null);

  const [data, setData] = useState<DataPoint[]>([]);
  const [unit, setUnit] = useState("");
  const [sourceOrg, setSourceOrg] = useState("");
  const [timeCoverage, setTimeCoverage] = useState("");
  const [methodologyNote, setMethodologyNote] = useState("");
  const [licenseUrl, setLicenseUrl] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!dataset || !country) return;
    setLoading(true);
    setError(null);

    fetch("/api/series", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset, country }),
    })
      .then((r) => r.json())
      .then((json: SeriesResponse) => {
        if (json.error) {
          setError(json.error);
          return;
        }
        setData(json.rows.map((r) => ({ year: String(r.year), value: r.value })));
        setUnit(json.unit ?? "");
        setSourceOrg(json.source_org ?? dataset);
        setTimeCoverage(json.time_coverage ?? "");
        setMethodologyNote(json.methodology_note ?? "");
        setLicenseUrl(json.license_url ?? "");
        setLastUpdated(json.last_updated ?? "");
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [dataset, country]);

  // PNG download via canvas
  const downloadChart = () => {
    const container = chartRef.current;
    if (!container) return;
    const svg = container.querySelector("svg");
    if (!svg) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 400;

    const clone = svg.cloneNode(true) as SVGSVGElement;
    clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    clone.setAttribute("width", String(width));
    clone.setAttribute("height", String(height));
    const bg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    bg.setAttribute("width", "100%");
    bg.setAttribute("height", "100%");
    bg.setAttribute("fill", "white");
    clone.insertBefore(bg, clone.firstChild);

    const svgStr = new XMLSerializer().serializeToString(clone);
    const svgBlob = new Blob([svgStr], { type: "image/svg+xml;charset=utf-8" });
    const svgUrl = URL.createObjectURL(svgBlob);

    const img = new Image();
    img.onload = () => {
      const scale = window.devicePixelRatio || 2;
      const canvas = document.createElement("canvas");
      canvas.width = width * scale;
      canvas.height = height * scale;
      const ctx = canvas.getContext("2d")!;
      ctx.scale(scale, scale);
      ctx.fillStyle = "white";
      ctx.fillRect(0, 0, width, height);
      ctx.drawImage(img, 0, 0, width, height);
      URL.revokeObjectURL(svgUrl);
      canvas.toBlob((blob) => {
        if (!blob) return;
        const pngUrl = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = pngUrl;
        a.download = `${title.replace(/[^a-z0-9]/gi, "_")}.png`;
        a.click();
        URL.revokeObjectURL(pngUrl);
      }, "image/png");
    };
    img.onerror = () => {
      const a = document.createElement("a");
      a.href = svgUrl;
      a.download = `${title.replace(/[^a-z0-9]/gi, "_")}.svg`;
      a.click();
      URL.revokeObjectURL(svgUrl);
    };
    img.src = svgUrl;
  };

  const downloadCSV = () => {
    const header = unit ? `Year,Value (${unit})` : "Year,Value";
    const rows = data.map((d) => `${d.year},${d.value}`);
    const blob = new Blob([[header, ...rows].join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.replace(/[^a-z0-9]/gi, "_")}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-6 flex-wrap">
        <div>
          <h2 className="text-base font-bold text-gray-900">{title}</h2>
          <p className="text-xs text-gray-400 font-mono mt-0.5">
            {dataset} · {country}
            {unit && <span className="text-gray-500 font-sans"> · {unit}</span>}
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={citations}
              onChange={(e) => setCitations(e.target.checked)}
              className="w-4 h-4 rounded accent-blue-600 cursor-pointer"
            />
            <span className="text-sm text-gray-700 font-medium">Include Citations</span>
          </label>

          <select
            value={chartType}
            onChange={(e) => setChartType(e.target.value as ChartType)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
          >
            {CHART_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>

          <button
            onClick={downloadChart}
            disabled={loading || !!error || data.length === 0}
            title="Download chart as PNG"
            className="flex items-center gap-1.5 text-sm text-gray-600 border border-gray-200 rounded-lg px-3 py-1.5 hover:bg-gray-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Download className="w-4 h-4" strokeWidth={2} />
            PNG
          </button>

          <button
            onClick={downloadCSV}
            disabled={loading || !!error || data.length === 0}
            title="Download data as CSV"
            className="flex items-center gap-1.5 text-sm text-gray-600 border border-gray-200 rounded-lg px-3 py-1.5 hover:bg-gray-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <FileDown className="w-4 h-4" strokeWidth={2} />
            CSV
          </button>
        </div>
      </div>

      {/* Chart area */}
      {loading ? (
        <div className="h-72 flex items-center justify-center gap-3 text-sm text-gray-400">
          <Loader2 className="w-5 h-5 animate-spin text-blue-400" strokeWidth={2} />
          Fetching data from the UN Data Commons…
        </div>
      ) : error || data.length === 0 ? (
        <div className="h-72 flex flex-col items-center justify-center gap-3">
          <div className="w-12 h-12 rounded-full bg-gray-50 flex items-center justify-center">
            <svg className="w-6 h-6 text-gray-300" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 3v18h18M9 17V9m4 8v-5m4 5V5" />
            </svg>
          </div>
          <div className="text-center">
            <p className="text-sm text-gray-500 font-medium">No observations available</p>
            <p className="text-xs text-gray-400 mt-1">
              {dataset} · {country}
            </p>
          </div>
        </div>
      ) : (
        <div ref={chartRef} className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <ChartRenderer
              type={chartType}
              data={data}
              unit={unit}
              citations={citations}
              dataset={sourceOrg || dataset}
            />
          </ResponsiveContainer>
        </div>
      )}

      {!loading && !error && data.length > 0 && citations && (
        <p className="text-xs text-gray-400 mt-3 text-right">
          Source: UN Data Commons · {sourceOrg || dataset} · {data.length} observations
        </p>
      )}

      {/* Data Provenance */}
      {!loading && !error && data.length > 0 && (
        <div className="mt-4 border-t border-gray-100 pt-4">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Data Provenance</p>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
            <div>
              <dt className="text-gray-400">Source organisation</dt>
              <dd className="text-gray-700 font-medium mt-0.5">
                {licenseUrl ? (
                  <a href={licenseUrl} target="_blank" rel="noopener noreferrer"
                    className="text-blue-600 hover:underline">
                    {sourceOrg || dataset}
                  </a>
                ) : (sourceOrg || dataset)}
              </dd>
            </div>
            <div>
              <dt className="text-gray-400">Indicator code</dt>
              <dd className="text-gray-700 font-mono mt-0.5 truncate">{dataset}</dd>
            </div>
            <div>
              <dt className="text-gray-400">Time coverage</dt>
              <dd className="text-gray-700 font-medium mt-0.5">{timeCoverage || "—"}</dd>
            </div>
            <div>
              <dt className="text-gray-400">Last updated</dt>
              <dd className="text-gray-700 font-medium mt-0.5">{lastUpdated || "—"}</dd>
            </div>
            {unit && (
              <div>
                <dt className="text-gray-400">Unit of measurement</dt>
                <dd className="text-gray-700 font-medium mt-0.5">{unit}</dd>
              </div>
            )}
            {methodologyNote && (
              <div className="col-span-2">
                <dt className="text-gray-400">Measurement method</dt>
                <dd className="text-gray-600 mt-0.5 leading-relaxed">{methodologyNote}</dd>
              </div>
            )}
          </dl>
        </div>
      )}
    </div>
  );
}

// ─── Empty state ──────────────────────────────────────────────────────────────

function EmptyState({ onLoad }: { onLoad: (dataset: string, country: string) => void }) {
  const [datasetInput, setDatasetInput] = useState("");
  const [countryInput, setCountryInput] = useState("");

  const canSubmit = datasetInput.trim().length > 0 && countryInput.trim().length > 0;

  const handleLoad = () => {
    if (!canSubmit) return;
    onLoad(datasetInput.trim(), countryInput.trim().toUpperCase());
  };

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
          Enter a UN Data Commons dataset ID and country code, or arrive here from the Trust Filter.
        </p>

        <div className="w-full max-w-md space-y-3">
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider text-left mb-1">
              Dataset ID
            </label>
            <input
              type="text"
              value={datasetInput}
              onChange={(e) => setDatasetInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLoad()}
              placeholder="e.g., sdg/SH_DYN_MORT"
              className="w-full px-4 py-3 border border-gray-300 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider text-left mb-1">
              Country (ISO3 code)
            </label>
            <input
              type="text"
              value={countryInput}
              onChange={(e) => setCountryInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleLoad()}
              placeholder="e.g., KEN"
              maxLength={3}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm"
            />
          </div>
          <button
            onClick={handleLoad}
            disabled={!canSubmit}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
          >
            Load Data
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Main export ──────────────────────────────────────────────────────────────

interface Props {
  dataset?: string;
  country?: string;
  name?: string;
  onManualLoad?: (dataset: string, country: string) => void;
}

export default function VisualizationCard({ dataset, country, name, onManualLoad }: Props) {
  if (!dataset || !country) {
    return <EmptyState onLoad={onManualLoad ?? (() => {})} />;
  }

  const displayName = name ? `${name} (${country})` : dataset;

  return (
    <LoadedState title={displayName} dataset={dataset} country={country} />
  );
}
