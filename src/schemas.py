"""
Data contracts for the Query Trust & Viability Assessor pipeline.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Fixed catalogs
# ---------------------------------------------------------------------------

VALID_ISO3_CODES: frozenset[str] = frozenset({
    "AFG", "ALB", "DZA", "AND", "AGO", "ARG", "ARM", "AUS", "AUT", "AZE",
    "BHS", "BHR", "BGD", "BRB", "BLR", "BEL", "BLZ", "BEN", "BTN", "BOL",
    "BIH", "BWA", "BRA", "BRN", "BGR", "BFA", "BDI", "CPV", "KHM", "CMR",
    "CAN", "CAF", "TCD", "CHL", "CHN", "COL", "COM", "COD", "COG", "CRI",
    "CIV", "HRV", "CUB", "CYP", "CZE", "DNK", "DJI", "DOM", "ECU", "EGY",
    "SLV", "GNQ", "ERI", "EST", "SWZ", "ETH", "FJI", "FIN", "FRA", "GAB",
    "GMB", "GEO", "DEU", "GHA", "GRC", "GTM", "GIN", "GNB", "GUY", "HTI",
    "HND", "HUN", "ISL", "IND", "IDN", "IRN", "IRQ", "IRL", "ISR", "ITA",
    "JAM", "JPN", "JOR", "KAZ", "KEN", "KOR", "PRK", "KWT", "KGZ", "LAO",
    "LVA", "LBN", "LSO", "LBR", "LBY", "LIE", "LTU", "LUX", "MDG", "MWI",
    "MYS", "MDV", "MLI", "MLT", "MRT", "MUS", "MEX", "MDA", "MNG", "MNE",
    "MAR", "MOZ", "MMR", "NAM", "NPL", "NLD", "NZL", "NIC", "NER", "NGA",
    "MKD", "NOR", "OMN", "PAK", "PAN", "PNG", "PRY", "PER", "PHL", "POL",
    "PRT", "QAT", "ROU", "RUS", "RWA", "SAU", "SEN", "SRB", "SLE", "SGP",
    "SVK", "SVN", "SOM", "ZAF", "SSD", "ESP", "LKA", "SDN", "SUR", "SWE",
    "CHE", "SYR", "TJK", "TZA", "THA", "TLS", "TGO", "TTO", "TUN", "TUR",
    "TKM", "UGA", "UKR", "ARE", "GBR", "USA", "URY", "UZB", "VEN", "VNM",
    "YEM", "ZMB", "ZWE",
})

# Topic groups: each topic maps to 3-4 World Bank indicators that together
# cover the concept from different angles.  The pipeline evaluates EVERY
# indicator in the matched group so the analyst sees the full candidate set.
# Format: (human_label, WB_indicator_code)
TOPIC_GROUPS: dict[str, list[tuple[str, str]]] = {
    "poverty and inequality": [
        ("National Poverty Headcount Ratio", "SI.POV.NAHC"),
        ("Extreme Poverty Headcount ($2.15/day)", "SI.POV.DDAY"),
        ("Gini Index (income inequality)", "SI.POV.GINI"),
    ],
    "economic growth": [
        ("GDP per Capita (current USD)", "NY.GDP.PCAP.CD"),
        ("GDP Annual Growth Rate (%)", "NY.GDP.MKTP.KD.ZG"),
        ("Inflation, Consumer Prices (annual %)", "FP.CPI.TOTL.ZG"),
    ],
    "health outcomes": [
        ("Life Expectancy at Birth (years)", "SP.DYN.LE00.IN"),
        ("Under-5 Mortality Rate (per 1,000)", "SH.DYN.MORT"),
        ("Maternal Mortality Ratio (per 100,000)", "SH.STA.MMRT"),
        ("Health Expenditure (% of GDP)", "SH.XPD.CHEX.GD.ZS"),
    ],
    "education": [
        ("Primary School Net Enrollment Rate (%)", "SE.PRM.NENR"),
        ("Adult Literacy Rate (%)", "SE.ADT.LITR.ZS"),
        ("Government Education Expenditure (% of GDP)", "SE.XPD.TOTL.GD.ZS"),
    ],
    "population and urbanisation": [
        ("Total Population", "SP.POP.TOTL"),
        ("Urban Population (% of total)", "SP.URB.TOTL.IN.ZS"),
        ("Rural Population (% of total)", "SP.RUR.TOTL.ZS"),
    ],
    "environment and climate": [
        ("CO2 Emissions per Capita (metric tons)", "EN.ATM.CO2E.PC"),
        ("Forest Area (% of land area)", "AG.LND.FRST.ZS"),
        ("Renewable Energy Share of Total Consumption (%)", "EG.FEC.RNEW.ZS"),
        ("Access to Electricity (% of population)", "EG.ELC.ACCS.ZS"),
    ],
    "trade and finance": [
        ("Foreign Direct Investment, Net Inflows (% of GDP)", "BX.KLT.DINV.WD.GD.ZS"),
        ("Exports of Goods & Services (% of GDP)", "NE.EXP.GNFS.ZS"),
        ("Imports of Goods & Services (% of GDP)", "NE.IMP.GNFS.ZS"),
        ("Government Expenditure (% of GDP)", "GC.XPN.TOTL.GD.ZS"),
    ],
    "infrastructure and technology": [
        ("Access to Electricity (% of population)", "EG.ELC.ACCS.ZS"),
        ("Internet Users (% of population)", "IT.NET.USER.ZS"),
        ("Renewable Energy Share of Total Consumption (%)", "EG.FEC.RNEW.ZS"),
    ],
    "employment and labour": [
        ("Unemployment Rate (% of labour force)", "SL.UEM.TOTL.ZS"),
        ("GDP per Capita (current USD)", "NY.GDP.PCAP.CD"),
        ("GDP Annual Growth Rate (%)", "NY.GDP.MKTP.KD.ZG"),
    ],
}


# ---------------------------------------------------------------------------
# Step 1 output: StructuredQuery  (topic-based, not single-indicator)
# ---------------------------------------------------------------------------

class StructuredQuery(BaseModel):
    """Parsed, validated query. `topic` maps to a TOPIC_GROUPS key;
    the pipeline resolves all candidate indicators from that group."""

    topic: str                              # must be a key in TOPIC_GROUPS
    geography: str                          # ISO 3166-1 alpha-3, uppercased
    time_range: Optional[tuple[int, int]] = None
    comparison_requested: bool = False

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        if v not in TOPIC_GROUPS:
            raise ValueError(
                f"'{v}' is not a recognised topic. "
                f"Valid topics: {sorted(TOPIC_GROUPS.keys())}"
            )
        return v

    @field_validator("geography")
    @classmethod
    def validate_geography(cls, v: str) -> str:
        code = v.upper().strip()
        if code not in VALID_ISO3_CODES:
            raise ValueError(
                f"'{v}' is not a recognised ISO-3166-1 alpha-3 country code."
            )
        return code

    @field_validator("time_range", mode="before")
    @classmethod
    def validate_time_range(cls, v):
        if v is None:
            return None
        try:
            start, end = int(v[0]), int(v[1])
        except (TypeError, IndexError, ValueError):
            raise ValueError("time_range must be [start_year, end_year] or null.")
        if not (1950 <= start <= 2030):
            raise ValueError(f"Start year {start} outside valid range 1950–2030.")
        if not (1950 <= end <= 2030):
            raise ValueError(f"End year {end} outside valid range 1950–2030.")
        if start > end:
            raise ValueError(f"Start year {start} must be ≤ end year {end}.")
        return (start, end)

    @property
    def candidates(self) -> list[tuple[str, str]]:
        return TOPIC_GROUPS.get(self.topic, [])


# ---------------------------------------------------------------------------
# Step 2 outputs: RawDataset, RawMetadata, FetchError
# ---------------------------------------------------------------------------

class DataRow(BaseModel):
    year: int
    value: Optional[float]


class RawDataset(BaseModel):
    indicator_code: str
    geography: str
    rows: list[DataRow]


class RawMetadata(BaseModel):
    indicator_code: str
    indicator_name: Optional[str] = None
    unit: Optional[str] = None
    source_org: Optional[str] = None
    methodology_note: Optional[str] = None
    time_coverage: Optional[str] = None
    geography_coverage: Optional[str] = None
    license: Optional[str] = None
    last_updated: Optional[str] = None


class FetchError(BaseModel):
    reason: str
    http_status: Optional[int] = None


class DatasetInfo(BaseModel):
    """Provenance record shown to the user for each evaluated dataset."""
    indicator_name: Optional[str] = None
    indicator_code: str
    geography: str
    years_in_data: Optional[tuple[int, int]] = None
    row_count: int = 0
    non_null_count: int = 0
    source_org: Optional[str] = None
    api_url: str = ""
    last_updated: Optional[str] = None


# ---------------------------------------------------------------------------
# Step 3 output: DimensionScores
# ---------------------------------------------------------------------------

class MetadataCompletenessScore(BaseModel):
    score: float
    missing_fields: list[str]
    present_fields: list[str]


class DataQualityScore(BaseModel):
    score: float
    issues: list[str]


class FreshnessScore(BaseModel):
    score: float
    days_since_update: Optional[int]
    note: str


class DimensionScores(BaseModel):
    metadata_completeness: MetadataCompletenessScore
    data_quality: DataQualityScore
    freshness: FreshnessScore


# ---------------------------------------------------------------------------
# Step 4 output: CandidateResult + MultiDatasetReport
# ---------------------------------------------------------------------------

class CandidateResult(BaseModel):
    """Trust evaluation for a single candidate dataset."""
    dataset_info: DatasetInfo
    dimension_scores: DimensionScores
    verdict: Literal["PASS", "REJECT"]
    # Operational consequences in plain language, NOT raw score percentages.
    operational_explanation: str


class MultiDatasetReport(BaseModel):
    """Top-level output: all candidates evaluated, overall status, pivots."""
    query: str
    topic: str
    geography: str
    time_range: Optional[tuple[int, int]]
    candidates: list[CandidateResult]
    overall_status: Literal["VIABLE", "NOT_VIABLE"]
    # Populated only when overall_status == "NOT_VIABLE"
    pivots: list[str] = []
    # Populated on parse/fetch failures before any candidate could be evaluated
    parse_error: Optional[str] = None
