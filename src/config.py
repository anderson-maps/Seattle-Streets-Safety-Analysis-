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
