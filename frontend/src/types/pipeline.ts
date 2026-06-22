// Mirrors the Pydantic schemas in src/schemas.py

export interface CandidateOption {
  index: number;
  indicator_name: string;
  indicator_code: string;
}

export interface CandidateList {
  query: string;
  topic: string;
  geography: string;
  time_range: [number, number] | null;
  options: CandidateOption[];
  parse_error?: string | null;
}

export interface MetadataCompletenessScore {
  score: number;
  missing_fields: string[];
  present_fields: string[];
}

export interface DataQualityScore {
  score: number;
  issues: string[];
}

export interface FreshnessScore {
  score: number;
  days_since_update: number | null;
  note: string;
}

export interface CrossSourceScore {
  score: number;
  status: "AGREE" | "CONFLICT" | "SINGLE_SOURCE" | "NO_DATA" | "NO_COMMONS_EQUIVALENT";
  spread_pct: number | null;
  source_count: number;
  authoritative_count: number;
  note: string;
}

export interface DimensionScores {
  metadata_completeness: MetadataCompletenessScore;
  data_quality: DataQualityScore;
  freshness: FreshnessScore;
  cross_source?: CrossSourceScore | null;
}

export interface DatasetInfo {
  indicator_name: string | null;
  indicator_code: string;
  geography: string;
  years_in_data: [number, number] | null;
  row_count: number;
  non_null_count: number;
  source_org: string | null;
  last_updated: string | null;
}

export interface CandidateResult {
  dataset_info: DatasetInfo;
  dimension_scores: DimensionScores;
  verdict: "PASS" | "REVIEW" | "REJECT";
  operational_explanation: string;
}

export interface ChainRecommendation {
  label: string;
  geography: string;
  topic: string;
  reason: string;
}

export interface MultiDatasetReport {
  query: string;
  topic: string;
  geography: string;
  time_range: [number, number] | null;
  overall_status: "VIABLE" | "NOT_VIABLE";
  candidates: CandidateResult[];
  chain: ChainRecommendation[];
  parse_error?: string | null;
}
