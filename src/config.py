"""Paths and shared definitions for the Seattle KSI pipeline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
DOCS = ROOT / "docs"

COLLISIONS_CSV = RAW / "SDOT_Collisions_All_Years.csv"
STREETS_CSV = RAW / "Seattle_Streets.csv"

# KSI = fatal + serious injury, defined from SDOT's SEVERITYCODE (3 = serious injury, 4 = fatal).
# Other severity fields disagree with it in a few hundred records; see docs/data_audit.md.
KSI_CODES = (3, 4)

TRACTS_SHP = RAW / "tl_2026_53_tract.shp"          # Census TIGER/Line 2026 tracts, Washington
ACS_POP_CSV = RAW / "ACSDT5Y2024_B01003-Data.csv"   # ACS 2020-2024 5-yr, total population
ACS_COMMUTE_CSV = RAW / "ACSDT5Y2024_B08301-Data.csv"  # ACS 2020-2024 5-yr, means of transportation to work
KING_FIPS = "033"
