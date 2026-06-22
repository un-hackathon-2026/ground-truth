import Link from "next/link";
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  GitMerge,
  ArrowRight,
  ExternalLink,
  BarChart2,
  ShieldAlert,
  ShieldCheck,
  Info,
} from "lucide-react";
import type { MultiDatasetReport, CandidateResult, CrossSourceScore } from "@/types/pipeline";

// ─── Helpers ──────────────────────────────────────────────────────────────────

function scoreColors(score: number) {
  if (score >= 0.7)
    return { bg: "bg-green-50", border: "border-green-200", text: "text-green-700", icon: "text-green-500" };
  if (score >= 0.4)
    return { bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-700", icon: "text-amber-500" };
  return { bg: "bg-red-50", border: "border-red-200", text: "text-red-700", icon: "text-red-500" };
}

function verdictStyles(verdict: "PASS" | "REVIEW" | "REJECT") {
  if (verdict === "PASS")  return { bg: "bg-green-100", text: "text-green-700", label: "PASS" };
  if (verdict === "REVIEW") return { bg: "bg-amber-100", text: "text-amber-700", label: "REVIEW" };
  return { bg: "bg-red-100", text: "text-red-700", label: "REJECT" };
}

function browserUrl(indicatorCode: string) {
  return `https://datacommons.org/browser/${indicatorCode}`;
}

function dashboardHref(indicatorCode: string, geography: string, name: string, verdict: string) {
  const p = new URLSearchParams({ dataset: indicatorCode, country: geography, name, verdict });
  return `/policy-dashboard?${p.toString()}`;
}

// ─── Responsible Use Assessment ───────────────────────────────────────────────

interface UseAssessment {
  suitableFor: string[];
  notSuitableFor: string[];
  keyRisks: string[];
}

function buildUseAssessment(data: MultiDatasetReport): UseAssessment {
  const suitableFor: string[] = [];
  const notSuitableFor: string[] = [];
  const keyRisks: string[] = [];

  const cs = data.candidates;
  if (!cs.length) return { suitableFor, notSuitableFor, keyRisks };

  const passing = cs.filter(c => c.verdict === "PASS");
  const reviewing = cs.filter(c => c.verdict === "REVIEW");

  // Freshness analysis
  const lastYears = cs
    .map(c => Number(c.dataset_info.last_updated))
    .filter(y => !isNaN(y) && y > 1990);
  const maxLastYear = lastYears.length ? Math.max(...lastYears) : null;
  const freshScores = cs.map(c => c.dimension_scores.freshness.score);
  const avgFreshness = freshScores.reduce((a, b) => a + b, 0) / freshScores.length;

  // Row count / trend ability
  const rowCounts = cs.map(c => c.dataset_info.row_count ?? 0);
  const maxRows = Math.max(...rowCounts);
  const thinCount = cs.filter(c => (c.dataset_info.row_count ?? 0) <= 3).length;

  // Cross-source
  const hasConflict = cs.some(c => c.dimension_scores.cross_source?.status === "CONFLICT");
  const allSingleSource = cs.every(
    c => c.dimension_scores.cross_source?.status === "SINGLE_SOURCE" ||
         c.dimension_scores.cross_source?.status === "NO_DATA"
  );

  // Coverage
  const yearsRanges = cs
    .filter(c => c.dataset_info.years_in_data)
    .map(c => c.dataset_info.years_in_data!);
  const allStart = yearsRanges.length ? Math.min(...yearsRanges.map(r => r[0])) : null;
  const allEnd = yearsRanges.length ? Math.max(...yearsRanges.map(r => r[1])) : null;

  // Build suitable-for
  if (passing.length > 0) {
    if (allStart && allEnd) {
      suitableFor.push(`Historical trend analysis within the ${allStart}–${allEnd} coverage period`);
    }
    suitableFor.push("SDG progress monitoring and policy baseline reporting");
    if (avgFreshness >= 0.6) {
      suitableFor.push("Inclusion in ministerial briefings with full source attribution");
    }
  }
  if (reviewing.length > 0) {
    suitableFor.push("Exploratory analysis when findings are presented with caveats");
  }

  // Build not-suitable-for
  if (avgFreshness < 0.45) {
    notSuitableFor.push(
      `Real-time or current-year decisions — most recent observation: ${maxLastYear ?? "before 2022"}`
    );
  }
  if (thinCount > 0 && thinCount === cs.length) {
    notSuitableFor.push(
      `Statistical trend modeling or regression — insufficient observations (max ${maxRows})`
    );
  }
  if (hasConflict) {
    notSuitableFor.push(
      "Definitive cross-source conclusions without expert reconciliation of source conflicts"
    );
  }
  if (data.overall_status === "NOT_VIABLE") {
    notSuitableFor.push("Any policy decision without first sourcing higher-quality alternative data");
  }

  // Key risks
  if (hasConflict) {
    const conflicted = cs.filter(c => c.dimension_scores.cross_source?.status === "CONFLICT");
    for (const c of conflicted) {
      const spread = c.dimension_scores.cross_source?.spread_pct;
      keyRisks.push(
        `${c.dataset_info.indicator_name ?? c.dataset_info.indicator_code}: authoritative sources disagree` +
        (spread != null ? ` (${spread.toFixed(0)}% value spread)` : "")
      );
    }
  }
  if (allSingleSource && passing.length > 0) {
    keyRisks.push("All viable datasets come from a single source — independent cross-validation was not possible");
  }
  if (avgFreshness < 0.3) {
    keyRisks.push(
      `Significant temporal gap — data may not reflect conditions after ${maxLastYear ?? "the last update"}`
    );
  }

  return { suitableFor, notSuitableFor, keyRisks };
}

function ResponsibleUseCard({ data }: { data: MultiDatasetReport }) {
  const { suitableFor, notSuitableFor, keyRisks } = buildUseAssessment(data);
  const isViable = data.overall_status === "VIABLE";

  return (
    <div className={`rounded-xl border p-4 space-y-3 ${
      isViable ? "bg-green-50 border-green-200" : "bg-amber-50 border-amber-200"
    }`}>
      <div className="flex items-center gap-2">
        {isViable
          ? <ShieldCheck className="w-4 h-4 text-green-600 flex-shrink-0" strokeWidth={2} />
          : <ShieldAlert className="w-4 h-4 text-amber-600 flex-shrink-0" strokeWidth={2} />
        }
        <span className={`text-xs font-bold uppercase tracking-wide ${
          isViable ? "text-green-700" : "text-amber-700"
        }`}>
          {isViable ? "Responsible Use Assessment — Query is answerable" : "Responsible Use Assessment — Limited viability"}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {suitableFor.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-600 mb-1.5 flex items-center gap-1">
              <CheckCircle className="w-3 h-3 text-green-500" strokeWidth={2.5} />
              Suitable for
            </p>
            <ul className="space-y-1">
              {suitableFor.map((item, i) => (
                <li key={i} className="text-xs text-gray-700 flex gap-1.5">
                  <span className="text-green-500 mt-0.5 flex-shrink-0">·</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {notSuitableFor.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-600 mb-1.5 flex items-center gap-1">
              <XCircle className="w-3 h-3 text-red-400" strokeWidth={2.5} />
              Not suitable for
            </p>
            <ul className="space-y-1">
              {notSuitableFor.map((item, i) => (
                <li key={i} className="text-xs text-gray-700 flex gap-1.5">
                  <span className="text-red-400 mt-0.5 flex-shrink-0">·</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {keyRisks.length > 0 && (
        <div className="border-t border-amber-200 pt-2.5">
          <p className="text-xs font-semibold text-amber-700 mb-1.5 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" strokeWidth={2.5} />
            Key risks
          </p>
          <ul className="space-y-1">
            {keyRisks.map((risk, i) => (
              <li key={i} className="text-xs text-amber-800 flex gap-1.5">
                <span className="flex-shrink-0 mt-0.5">·</span>
                {risk}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ─── Dataset Comparison Table ──────────────────────────────────────────────────

function ComparisonTable({ candidates }: { candidates: CandidateResult[] }) {
  if (candidates.length < 2) return null;

  return (
    <div className="rounded-xl border border-gray-200 overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2.5 bg-gray-50 border-b border-gray-200">
        <Info className="w-3.5 h-3.5 text-gray-400" strokeWidth={2} />
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          Dataset Comparison
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="text-left px-3 py-2 font-semibold text-gray-500">Indicator</th>
              <th className="text-center px-3 py-2 font-semibold text-gray-500">Coverage</th>
              <th className="text-center px-3 py-2 font-semibold text-gray-500">Obs.</th>
              <th className="text-center px-3 py-2 font-semibold text-gray-500">Metadata</th>
              <th className="text-center px-3 py-2 font-semibold text-gray-500">Quality</th>
              <th className="text-center px-3 py-2 font-semibold text-gray-500">Freshness</th>
              <th className="text-center px-3 py-2 font-semibold text-gray-500">Verdict</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((c, i) => {
              const s = c.dimension_scores;
              const v = verdictStyles(c.verdict);
              return (
                <tr key={i} className={`border-b border-gray-50 ${i % 2 === 0 ? "bg-white" : "bg-gray-50/50"}`}>
                  <td className="px-3 py-2 max-w-[180px]">
                    <p className="font-medium text-gray-800 truncate" title={c.dataset_info.indicator_name ?? c.dataset_info.indicator_code}>
                      {c.dataset_info.indicator_name ?? c.dataset_info.indicator_code}
                    </p>
                    <p className="text-gray-400 font-mono text-[10px] truncate">{c.dataset_info.source_org}</p>
                  </td>
                  <td className="px-3 py-2 text-center text-gray-600">
                    {c.dataset_info.years_in_data
                      ? `${c.dataset_info.years_in_data[0]}–${c.dataset_info.years_in_data[1]}`
                      : "—"}
                  </td>
                  <td className="px-3 py-2 text-center text-gray-600">
                    {c.dataset_info.row_count ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={`font-semibold ${scoreColors(s.metadata_completeness.score).text}`}>
                      {Math.round(s.metadata_completeness.score * 100)}%
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={`font-semibold ${scoreColors(s.data_quality.score).text}`}>
                      {Math.round(s.data_quality.score * 100)}%
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={`font-semibold ${scoreColors(s.freshness.score).text}`}>
                      {Math.round(s.freshness.score * 100)}%
                    </span>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${v.bg} ${v.text}`}>
                      {v.label}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function MetricChip({ label, score }: { label: string; score: number }) {
  const pct = Math.round(score * 100);
  const c = scoreColors(score);
  const Icon = score >= 0.7 ? CheckCircle : AlertTriangle;
  return (
    <div className={`flex flex-col items-center gap-1 p-3 rounded-xl border ${c.bg} ${c.border}`}>
      <Icon className={`w-4 h-4 ${c.icon}`} strokeWidth={2} />
      <span className={`text-base font-bold leading-none ${c.text}`}>{pct}%</span>
      <span className="text-xs text-gray-500 font-medium">{label}</span>
    </div>
  );
}

function CrossSourceBadge({ cs }: { cs: CrossSourceScore }) {
  const styles = {
    AGREE:                { bg: "bg-green-50", border: "border-green-200", text: "text-green-700" },
    CONFLICT:             { bg: "bg-red-50",   border: "border-red-200",   text: "text-red-700"   },
    SINGLE_SOURCE:        { bg: "bg-gray-50",  border: "border-gray-200",  text: "text-gray-600"  },
    NO_DATA:              { bg: "bg-gray-50",  border: "border-gray-200",  text: "text-gray-500"  },
    NO_COMMONS_EQUIVALENT:{ bg: "bg-gray-50",  border: "border-gray-200",  text: "text-gray-500"  },
  }[cs.status];

  const label = cs.status.replace(/_/g, " ");
  const detail = cs.source_count > 0
    ? ` · ${cs.source_count} source${cs.source_count !== 1 ? "s" : ""}${
        cs.spread_pct != null ? ` · ${cs.spread_pct.toFixed(0)}% spread` : ""
      }`
    : "";

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium ${styles.bg} ${styles.border} ${styles.text}`}>
      <GitMerge className="w-3.5 h-3.5" strokeWidth={2} />
      <span>Cross-source: {label}{detail}</span>
    </div>
  );
}

function CandidateCard({ c }: { c: CandidateResult }) {
  const v = verdictStyles(c.verdict);
  const s = c.dimension_scores;
  const url = browserUrl(c.dataset_info.indicator_code);
  const vizHref = dashboardHref(
    c.dataset_info.indicator_code,
    c.dataset_info.geography,
    c.dataset_info.indicator_name ?? c.dataset_info.indicator_code,
    c.verdict,
  );

  return (
    <div className="border border-gray-200 rounded-xl p-4 space-y-3">
      {/* Header */}
      <div className="min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${v.bg} ${v.text}`}>
            {v.label}
          </span>
          <h4 className="text-sm font-semibold text-gray-900">
            {c.dataset_info.indicator_name ?? c.dataset_info.indicator_code}
          </h4>
        </div>
        <p className="text-xs font-mono text-gray-400 mt-1 truncate">
          {c.dataset_info.indicator_code}
        </p>

        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 mt-0.5 text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline"
        >
          {c.dataset_info.source_org ?? "View on UN Data Commons"}
          <ExternalLink className="w-3 h-3" strokeWidth={2} />
        </a>

        {c.dataset_info.years_in_data && (
          <p className="text-xs text-gray-400 mt-0.5">
            Data: {c.dataset_info.years_in_data[0]}–{c.dataset_info.years_in_data[1]}
            {" · "}{c.dataset_info.row_count} observations
          </p>
        )}
      </div>

      {/* Metric chips */}
      <div className="grid grid-cols-3 gap-2">
        <MetricChip label="Metadata" score={s.metadata_completeness.score} />
        <MetricChip label="Quality"  score={s.data_quality.score} />
        <MetricChip label="Freshness" score={s.freshness.score} />
      </div>

      {/* Cross-source */}
      {s.cross_source && (
        <div>
          <CrossSourceBadge cs={s.cross_source} />
          {s.cross_source.status === "CONFLICT" && s.cross_source.note && (
            <p className="text-xs text-red-600 mt-1.5 leading-relaxed">{s.cross_source.note}</p>
          )}
        </div>
      )}

      {/* Issues */}
      {s.metadata_completeness.missing_fields.length > 0 && (
        <p className="text-xs text-gray-500">
          Missing metadata:{" "}
          <span className="font-mono">{s.metadata_completeness.missing_fields.join(", ")}</span>
        </p>
      )}
      {s.data_quality.issues.length > 0 && (
        <ul className="text-xs text-amber-700 space-y-0.5">
          {s.data_quality.issues.map((issue, i) => (
            <li key={i} className="flex gap-1.5">
              <AlertTriangle className="w-3 h-3 flex-shrink-0 mt-0.5" strokeWidth={2} />
              {issue}
            </li>
          ))}
        </ul>
      )}

      {/* Explanation */}
      {c.operational_explanation && (
        <p className="text-xs text-gray-600 leading-relaxed border-t border-gray-100 pt-2">
          {c.operational_explanation}
        </p>
      )}

      {/* Source link + visualize button */}
      <div className="border-t border-gray-100 pt-3 space-y-2">
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-1.5 w-full py-2 rounded-lg border border-gray-200 text-xs font-medium text-gray-600 hover:text-blue-700 hover:border-blue-200 hover:bg-blue-50 transition-colors"
        >
          <ExternalLink className="w-3.5 h-3.5" strokeWidth={2} />
          View dataset source
        </a>
        <Link
          href={vizHref}
          className="flex items-center justify-center gap-1.5 w-full py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold transition-colors"
        >
          <BarChart2 className="w-3.5 h-3.5" strokeWidth={2} />
          Visualize this dataset
        </Link>
      </div>
    </div>
  );
}

// ─── Main export ──────────────────────────────────────────────────────────────

interface Props {
  data: MultiDatasetReport;
  onQuerySuggestion: (query: string) => void;
}

export default function TrustReport({ data, onQuerySuggestion }: Props) {
  const isViable = data.overall_status === "VIABLE";

  return (
    <div className="space-y-4">
      {/* Overall verdict */}
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-gray-600">Overall verdict:</span>
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-bold ${
            isViable ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
          }`}
        >
          {isViable
            ? <CheckCircle className="w-3.5 h-3.5" strokeWidth={2.5} />
            : <XCircle className="w-3.5 h-3.5" strokeWidth={2.5} />
          }
          {data.overall_status.replace("_", " ")}
        </span>
      </div>

      {/* Responsible Use Assessment */}
      {data.candidates.length > 0 && <ResponsibleUseCard data={data} />}

      {/* Comparison table — only when 2+ candidates */}
      {data.candidates.length >= 2 && (
        <ComparisonTable candidates={data.candidates} />
      )}

      {/* Per-candidate detail cards */}
      {data.candidates.length > 0 ? (
        <div className="space-y-3">
          {data.candidates.map((c, i) => <CandidateCard key={i} c={c} />)}
        </div>
      ) : (
        <p className="text-sm text-gray-500 italic">No candidate results returned.</p>
      )}

      {/* Related queries */}
      {data.chain.length > 0 && (
        <div className="pt-1">
          <p className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">
            Related queries
          </p>
          <div className="flex flex-wrap gap-2">
            {data.chain.map((ch, i) => (
              <button
                key={i}
                onClick={() => onQuerySuggestion(ch.label)}
                className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 bg-gray-100 hover:bg-blue-50 text-gray-600 hover:text-blue-700 rounded-full transition-colors font-medium"
              >
                <ArrowRight className="w-3 h-3" strokeWidth={2} />
                {ch.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
