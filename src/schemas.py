"""
Data contracts for the Query Trust & Viability Assessor pipeline.

MODIFIED (Chichi): added 4th dimension (cross_source_agreement), a REVIEW
verdict state, the per-candidate CrossSourceResult, and chain recommendations.
All additions are backward-compatible (Optional / defaults) so existing code
keeps working.
"""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Fixed catalogs  (unchanged)
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

# Neighbour groups for chain recommendations ("want neighbouring countries?").
# Small curated map — extend as needed. Keyed by ISO3.
NEIGHBOURS: dict[str, list[str]] = {
    "KEN": ["TZA", "UGA", "ETH", "SOM", "SSD"],
    "NGA": ["BEN", "NER", "TCD", "CMR"],
    "ZAF": ["NAM", "BWA", "ZWE", "MOZ", "LSO", "SWZ"],
    "IND": ["PAK", "BGD", "NPL", "LKA", "BTN", "MMR"],
    "BRA": ["ARG", "BOL", "PER", "COL", "PRY", "URY"],
    "EGY": ["LBY", "SDN", "ISR"],
    "ETH": ["KEN", "SOM", "SSD", "ERI", "DJI"],
    "GHA": ["CIV", "BFA", "TGO"],
    "UGA": ["KEN", "TZA", "RWA", "SSD", "COD"],
    "TZA": ["KEN", "UGA", "RWA", "BDI", "MOZ", "ZMB", "MWI"],
}

# ISO3 -> human-readable country name (for display; codes shown in parentheses).
COUNTRY_NAMES: dict[str, str] = {
    "KEN": "Kenya", "TZA": "Tanzania", "UGA": "Uganda", "ETH": "Ethiopia",
    "SOM": "Somalia", "SSD": "South Sudan", "NGA": "Nigeria", "BEN": "Benin",
    "NER": "Niger", "TCD": "Chad", "CMR": "Cameroon", "ZAF": "South Africa",
    "NAM": "Namibia", "BWA": "Botswana", "ZWE": "Zimbabwe", "MOZ": "Mozambique",
    "LSO": "Lesotho", "SWZ": "Eswatini", "IND": "India", "PAK": "Pakistan",
    "BGD": "Bangladesh", "NPL": "Nepal", "LKA": "Sri Lanka", "BTN": "Bhutan",
    "MMR": "Myanmar", "BRA": "Brazil", "ARG": "Argentina", "BOL": "Bolivia",
    "PER": "Peru", "COL": "Colombia", "PRY": "Paraguay", "URY": "Uruguay",
    "EGY": "Egypt", "LBY": "Libya", "SDN": "Sudan", "ISR": "Israel",
    "ERI": "Eritrea", "DJI": "Djibouti", "GHA": "Ghana", "CIV": "Côte d'Ivoire",
    "BFA": "Burkina Faso", "TGO": "Togo", "RWA": "Rwanda", "COD": "DR Congo",
    "BDI": "Burundi", "ZMB": "Zambia", "MWI": "Malawi",
}


def country_name(iso3: str) -> str:
    """Human name for an ISO3 code, falling back to the code itself."""
    return COUNTRY_NAMES.get(iso3.upper(), iso3.upper())

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
# Step 1 output: StructuredQuery  (unchanged)
# ---------------------------------------------------------------------------

class StructuredQuery(BaseModel):
    topic: str
    geography: str
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
# Step 2 outputs  (unchanged)
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
# Step 3 output: DimensionScores  (+ NEW 4th dimension)
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


# NEW — 4th dimension
class CrossSourceScore(BaseModel):
    """How well independent sources agree on the same value."""
    score: float                       # 1.0 = identical, lower = wider spread
    status: Literal[
        "AGREE", "CONFLICT", "SINGLE_SOURCE", "NO_DATA", "NO_COMMONS_EQUIVALENT"
    ]
    spread_pct: Optional[float] = None
    source_count: int = 0
    authoritative_count: int = 0       # how many are official (not Wikipedia etc.)
    note: str = ""


class DimensionScores(BaseModel):
    metadata_completeness: MetadataCompletenessScore
    data_quality: DataQualityScore
    freshness: FreshnessScore
    # NEW — Optional so existing fixtures/tests that build 3 dims still validate
    cross_source: Optional[CrossSourceScore] = None


# ---------------------------------------------------------------------------
# Step 4 output  (+ REVIEW verdict, + chain recommendations)
# ---------------------------------------------------------------------------

class CandidateResult(BaseModel):
    dataset_info: DatasetInfo
    dimension_scores: DimensionScores
    # was Literal["PASS","REJECT"] — REVIEW added for cross-source conflicts
    verdict: Literal["PASS", "REVIEW", "REJECT"]
    operational_explanation: str


class ChainRecommendation(BaseModel):
    """A suggested follow-up query (the 'want neighbouring countries?' chain)."""
    label: str            # human text, e.g. "Compare with Tanzania"
    geography: str        # ISO3 to query next
    topic: str            # same topic, different place
    reason: str           # why it's suggested


class MultiDatasetReport(BaseModel):
    query: str
    topic: str
    geography: str
    time_range: Optional[tuple[int, int]]
    candidates: list[CandidateResult]
    overall_status: Literal["VIABLE", "NOT_VIABLE"]
    pivots: list[str] = []
    parse_error: Optional[str] = None
    # NEW — chain recommendations (follow-up queries)
    chain: list[ChainRecommendation] = []


# ---------------------------------------------------------------------------
# Clarification question (pre-fetch, LLM-only)
# ---------------------------------------------------------------------------

class ClarificationOption(BaseModel):
    label: str
    description: str


class ClarificationQuestion(BaseModel):
    question: str
    options: list[ClarificationOption]


# ---------------------------------------------------------------------------
# Phase 1 outputs: the candidate list the user chooses from (NEW)
# ---------------------------------------------------------------------------

class CandidateOption(BaseModel):
    """One dataset the user can pick — shown BEFORE any deep evaluation."""
    index: int                 # 1-based, for the user to select
    indicator_name: str
    indicator_code: str


class CandidateList(BaseModel):
    """Phase 1 result: what we'd evaluate, shown to the user to choose from.
    No fetching or scoring has happened yet — this is cheap."""
    query: str
    topic: str
    geography: str
    time_range: Optional[tuple[int, int]]
    options: list[CandidateOption] = []
    parse_error: Optional[str] = None
