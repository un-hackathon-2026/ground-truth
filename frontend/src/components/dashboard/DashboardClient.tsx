"use client";

import { useState } from "react";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import VisualizationCard from "./VisualizationCard";
import SynthesisEngine from "./SynthesisEngine";

interface Props {
  dataset?: string;
  country?: string;
  name?: string;
  verdict?: string;
}

type BriefStatus = "pending" | "loading" | "done";

// ─── Evidence chain ───────────────────────────────────────────────────────────

function verdictColor(v: string) {
  if (v === "PASS") return "text-green-600 bg-green-50 border-green-200";
  if (v === "REVIEW") return "text-amber-600 bg-amber-50 border-amber-200";
  return "text-red-600 bg-red-50 border-red-200";
}

function EvidenceChain({
  verdict,
  dataLoaded,
  briefStatus,
  hasDataset,
}: {
  verdict?: string;
  dataLoaded: boolean;
  briefStatus: BriefStatus;
  hasDataset: boolean;
}) {
  if (!hasDataset) return null;

  const fromFilter = !!verdict;

  type Step = { label: string; sub?: string; done: boolean; active: boolean };

  const steps: Step[] = [
    ...(fromFilter
      ? [
          { label: "Query & Clarification", sub: undefined, done: true, active: false },
          {
            label: "Trust Verified",
            sub: verdict,
            done: true,
            active: false,
          },
        ]
      : []),
    {
      label: "Data Fetched",
      sub: dataLoaded ? "from UN Data Commons" : undefined,
      done: dataLoaded,
      active: !dataLoaded,
    },
    {
      label: "Visualization",
      sub: dataLoaded ? "active" : undefined,
      done: dataLoaded,
      active: dataLoaded && briefStatus === "pending",
    },
    {
      label: "Evidence Brief",
      sub: briefStatus === "done" ? "generated" : briefStatus === "loading" ? "generating…" : undefined,
      done: briefStatus === "done",
      active: briefStatus === "loading",
    },
  ];

  return (
    <div className="bg-white border border-gray-200 rounded-2xl px-5 py-4">
      <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Evidence Chain
      </p>
      <div className="flex items-start gap-0 flex-wrap">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center gap-0">
            <div className="flex flex-col items-center min-w-[100px] max-w-[140px]">
              <div className="flex items-center gap-1.5">
                {step.done ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" strokeWidth={2} />
                ) : step.active ? (
                  <Loader2 className="w-4 h-4 text-blue-500 animate-spin flex-shrink-0" strokeWidth={2} />
                ) : (
                  <Circle className="w-4 h-4 text-gray-300 flex-shrink-0" strokeWidth={2} />
                )}
                <span className={`text-xs font-semibold ${step.done ? "text-gray-800" : step.active ? "text-blue-700" : "text-gray-400"}`}>
                  {step.label}
                </span>
              </div>
              {step.label === "Trust Verified" && verdict ? (
                <span className={`mt-1 text-[10px] font-bold px-1.5 py-0.5 rounded border ${verdictColor(verdict)}`}>
                  {verdict}
                </span>
              ) : step.sub ? (
                <span className="mt-1 text-[10px] text-gray-400">{step.sub}</span>
              ) : null}
            </div>
            {i < steps.length - 1 && (
              <div className={`h-px w-6 mx-1 mt-[-10px] flex-shrink-0 ${step.done ? "bg-green-300" : "bg-gray-200"}`} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main export ──────────────────────────────────────────────────────────────

export default function DashboardClient({ dataset, country, name, verdict }: Props) {
  const [activeDataset, setActiveDataset] = useState(dataset);
  const [activeCountry, setActiveCountry] = useState(country);
  const [activeName, setActiveName] = useState(name);
  const [dataLoaded, setDataLoaded] = useState(false);
  const [briefStatus, setBriefStatus] = useState<BriefStatus>("pending");

  const hasDataset = !!(activeDataset && activeCountry);

  return (
    <>
      <EvidenceChain
        verdict={verdict}
        dataLoaded={dataLoaded}
        briefStatus={briefStatus}
        hasDataset={hasDataset}
      />
      <VisualizationCard
        dataset={activeDataset}
        country={activeCountry}
        name={activeName}
        verdict={verdict}
        onManualLoad={(ds, ct) => {
          setActiveDataset(ds);
          setActiveCountry(ct);
          setActiveName(undefined);
          setDataLoaded(false);
          setBriefStatus("pending");
        }}
        onDataLoaded={() => setDataLoaded(true)}
      />
      <SynthesisEngine
        dataset={activeDataset}
        country={activeCountry}
        name={activeName}
        onStatusChange={setBriefStatus}
      />
    </>
  );
}
