# Seattle Streets Safety Analysis

Public, interactive analysis of serious-injury and fatal (KSI) collisions on Seattle streets. Goals: raise awareness of dangerous locations and show decision-makers where countermeasures are needed most. A site's ranking reflects crash history and modeled risk, not blame on any person. No victim names or identifying details are used.

**Status:** Phase 1 audit done ([docs/data_audit.md](docs/data_audit.md)); interim safety models in [docs/models_interim.md](docs/models_interim.md).

## Reproduce

```bash
pip install -r requirements.txt
# place raw files in data/raw/ (see data/README.md)
cd src && python 01_audit.py && python 02_safety_models.py
```

## Data sources (so far)

| File | Source | Notes |
|---|---|---|
| `SDOT_Collisions_All_Years.csv` | Seattle Open Data (SDOT/SPD collisions) | Downloaded Nov 2026; records through Oct 26, 2026 |
| `Seattle_Streets.csv` | Seattle GIS open data (street segments) | Attributes and midpoints only, no line geometry |

Planned: FARS, WSDOT crash data, Vision Zero High Injury Network, Race and Social Equity Index, ACS commute data. Licenses will be listed here as each source is added.

## Definitions

KSI = collisions with SDOT `SEVERITYCODE` 3 (serious injury) or 4 (fatal). Severity levels are kept separate from all collisions.

## Known limitations

See the audit. Key points: no exposure data yet, fatality counts unreliable in some years, reported collision volume drops after 2020.
