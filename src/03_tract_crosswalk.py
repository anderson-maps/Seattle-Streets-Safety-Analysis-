"""Provisional list of Seattle census tracts, inferred from where Seattle street segments fall.
The street file contains only SDOT-owned streets inside the city plus a few outside it, so tracts
with almost no segments are not Seattle. Replace this with a spatial join to the official
Seattle city-limit polygon when that file is available.

Rule: tract has >= 20 Seattle street-segment midpoints AND >= 5 miles of segment per sq mile of land.
Edge tracts that straddle city limits are included whole, which slightly overstates Seattle population.
"""
import geopandas as gpd, pandas as pd
from config import *

t = gpd.read_file(TRACTS_SHP)
k = t[t.COUNTYFP == KING_FIPS].copy()
st = pd.read_csv(STREETS_CSV, usecols=["COMPKEY", "GIS_MID_X", "GIS_MID_Y", "SEGLENGTH"])
pts = gpd.GeoDataFrame(st, geometry=gpd.points_from_xy(st.GIS_MID_X, st.GIS_MID_Y), crs=2926).to_crs(k.crs)
j = gpd.sjoin(pts, k[["GEOID", "geometry"]], how="left", predicate="within")
c = j.groupby("GEOID").agg(segments=("COMPKEY", "size"), seg_feet=("SEGLENGTH", "sum"))
k = k.merge(c, left_on="GEOID", right_index=True, how="left").fillna({"segments": 0, "seg_feet": 0})
k["street_mi_per_sqmi"] = (k.seg_feet / 5280) / (k.ALAND / 2.58999e6)
k["seattle_provisional"] = (k.segments >= 20) & (k.street_mi_per_sqmi >= 5)

pop = pd.read_csv(ACS_POP_CSV, skiprows=[1]); pop["GEOID"] = pop.GEO_ID.str[-11:]
wk = pd.read_csv(ACS_COMMUTE_CSV, skiprows=[1]); wk["GEOID"] = wk.GEO_ID.str[-11:]
x = k[["GEOID", "NAMELSAD", "segments", "street_mi_per_sqmi", "seattle_provisional"]].merge(
    pop[["GEOID", "B01003_001E", "B01003_001M"]].rename(columns={"B01003_001E": "pop", "B01003_001M": "pop_moe"}), on="GEOID").merge(
    wk[["GEOID", "B08301_001E", "B08301_018E", "B08301_018M", "B08301_019E", "B08301_019M", "B08301_021E"]].rename(columns={
        "B08301_001E": "workers", "B08301_018E": "bike", "B08301_018M": "bike_moe", "B08301_019E": "walk", "B08301_019M": "walk_moe", "B08301_021E": "wfh"}), on="GEOID")
x.round(3).to_csv(DOCS / "results" / "tract_crosswalk_provisional.csv", index=False)
s = x[x.seattle_provisional]
print(f"King tracts: {len(x)}; provisional Seattle tracts: {len(s)}; population {s['pop'].sum():,}; workers {s.workers.sum():,}")
print(f"workers walking {s.walk.sum():,} ({s.walk.sum()/s.workers.sum():.2%}); biking {s.bike.sum():,} ({s.bike.sum()/s.workers.sum():.2%}); WFH {s.wfh.sum()/s.workers.sum():.1%}")
import numpy as np
print("MOE of summed walk:", round(float(np.sqrt((s.walk_moe**2).sum())),0), " bike:", round(float(np.sqrt((s.bike_moe**2).sum())),0), " pop:", round(float(np.sqrt((s.pop_moe**2).sum())),0))
