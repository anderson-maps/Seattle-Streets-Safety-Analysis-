"""Phase 2 (interim): negative binomial safety performance functions (SPFs) and Empirical Bayes
(EB) ranking for street segments and intersections, plus a temporal holdout test.

Study window: 2015-2025 (full years, 11 yrs). 2026 is partial and excluded from ranking.
Holdout: fit/rank on 2015-2019, evaluate on 2021-2025 (2020 skipped: pandemic disruption).
No traffic volume exists in the inputs, so SPFs use road class, speed limit, length, width,
transit class, slope (segments) and leg counts/classes (intersections) as volume proxies.
"""
import numpy as np, pandas as pd, statsmodels.api as sm, statsmodels.formula.api as smf
from pyproj import Transformer
from config import COLLISIONS_CSV, STREETS_CSV, DOCS, KSI_CODES

RES = DOCS / "results"; RES.mkdir(parents=True, exist_ok=True)
df = pd.read_csv(COLLISIONS_CSV, low_memory=False)
st = pd.read_csv(STREETS_CSV, low_memory=False)
df["year"] = pd.to_datetime(df.INCDTTM, format="mixed").dt.year
k = df[df.SEVERITYCODE.isin(KSI_CODES)].copy()
k["ped"] = k.PEDCOUNT > 0
k["bike"] = (k.PEDCYLCOUNT > 0) & ~k.ped

tf = Transformer.from_crs(2926, 4326, always_xy=True)  # WA State Plane North (ftUS) -> lon/lat

def nb_fit(formula, d):
    m = smf.negativebinomial(formula, data=d).fit(disp=0, maxiter=200)
    alpha = float(m.params["alpha"])
    return m, alpha

def eb(d, m, alpha, ycol):
    mu = m.predict(d).values
    w = 1.0 / (1.0 + alpha * mu)
    d = d.copy()
    d["spf_expected"] = mu
    d["eb_expected"] = w * mu + (1 - w) * d[ycol].values
    d["excess"] = d.eb_expected - d.spf_expected
    return d

def capture(d, score, ycol_test, frac=0.05):
    n = max(1, int(len(d) * frac))
    top = d.sort_values(score, ascending=False).head(n)
    return top[ycol_test].sum() / d[ycol_test].sum()

# ---------------- segments ----------------
seg = st[(st.STATUS == "INSVC") & (st.SEGLENGTH > 0)].copy()
seg["spd"] = pd.cut(seg.SPEEDLIMIT.replace(0, np.nan), [0, 20, 25, 30, 100], labels=["<=20", "25", "30", "35+"]).astype(str)
seg["art"] = seg.ARTDESCRIPT.fillna("Not Designated")
seg["trn"] = seg.TRANCLASS.clip(upper=4).astype(int).astype(str)
seg["loglen"] = np.log(seg.SEGLENGTH)
seg["width"] = seg.SURFACEWIDTH.fillna(seg.SURFACEWIDTH.median())
seg["slope"] = seg.SLOPE_PCT.abs().fillna(0)
kb = k[k.ADDRTYPE == "B"]
def seg_counts(y0, y1, name):
    c = kb[kb.year.between(y0, y1)].groupby("ADDR_SEGINTKEY").agg(**{name: ("OBJECTID", "size")})
    return c
for (a, b, n) in [(2015, 2025, "ksi_all"), (2015, 2019, "ksi_train"), (2021, 2025, "ksi_test")]:
    seg = seg.merge(seg_counts(a, b, n), left_on="COMPKEY", right_index=True, how="left")
    seg[n] = seg[n].fillna(0)
ped = kb[kb.year.between(2015, 2025)].groupby("ADDR_SEGINTKEY").agg(ped_ksi=("ped", "sum"), bike_ksi=("bike", "sum"), fatal=("SEVERITYCODE", lambda s: (s == 4).sum()))
seg = seg.merge(ped, left_on="COMPKEY", right_index=True, how="left").fillna({"ped_ksi": 0, "bike_ksi": 0, "fatal": 0})
F_SEG = "{y} ~ C(art) + C(spd) + C(trn) + loglen + width + slope"
m_all, a_all = nb_fit(F_SEG.format(y="ksi_all"), seg)
seg = eb(seg, m_all, a_all, "ksi_all")
m_tr, a_tr = nb_fit(F_SEG.format(y="ksi_train"), seg)
seg_tr = eb(seg, m_tr, a_tr, "ksi_train")
lon, lat = tf.transform(seg.GIS_MID_X.values, seg.GIS_MID_Y.values)
seg["lon"], seg["lat"] = lon, lat
cols = ["COMPKEY", "UNITDESC", "ARTDESCRIPT", "SPEEDLIMIT", "SEGLENGTH", "ksi_all", "ped_ksi", "bike_ksi", "fatal", "spf_expected", "eb_expected", "excess", "lat", "lon"]
seg_rank = seg.sort_values("excess", ascending=False)[cols]
seg_rank.round(3).to_csv(RES / "segment_ranking_all.csv", index=False)
seg_rank.head(50).round(3).to_csv(RES / "segment_top50.csv", index=False)

# ---------------- intersections ----------------
lo = st[["INTKEYLO", "INTRLO", "ARTDESCRIPT", "SPEEDLIMIT", "SURFACEWIDTH", "TRANCLASS", "STATUS"]].set_axis(["key", "name", "art", "spd", "w", "trn", "status"], axis=1)
hi = st[["INTKEYHI", "INTRHI", "ARTDESCRIPT", "SPEEDLIMIT", "SURFACEWIDTH", "TRANCLASS", "STATUS"]].set_axis(["key", "name", "art", "spd", "w", "trn", "status"], axis=1)
legs = pd.concat([lo, hi])
legs = legs[legs.status == "INSVC"]
g = legs.groupby("key")
ix = pd.DataFrame({
    "name": g.name.first(),
    "legs": g.size(),
    "n_principal": g.art.apply(lambda s: (s == "Principal Arterial").sum()),
    "n_minor": g.art.apply(lambda s: (s == "Minor Arterial").sum()),
    "n_collector": g.art.apply(lambda s: (s == "Collector Arterial").sum()),
    "n_freeway": g.art.apply(lambda s: s.isin(["State Route/Freeway", "Interstate/Freeway"]).sum()),
    "max_spd": g.spd.max(),
    "sum_width": g.w.sum(),
    "n_transit": g.trn.apply(lambda s: ((s >= 1) & (s <= 3)).sum()),
}).reset_index()
ix["legs_c"] = ix.legs.clip(upper=5).astype(str)
ix["max_spd_c"] = ix.max_spd.clip(upper=40)
ix["logw"] = np.log1p(ix.sum_width.fillna(0))
ki = k[k.ADDRTYPE == "I"]
def int_counts(y0, y1, name):
    return ki[ki.year.between(y0, y1)].groupby("ADDR_SEGINTKEY").agg(**{name: ("OBJECTID", "size")})
for (a, b, n) in [(2015, 2025, "ksi_all"), (2015, 2019, "ksi_train"), (2021, 2025, "ksi_test")]:
    ix = ix.merge(int_counts(a, b, n), left_on="key", right_index=True, how="left"); ix[n] = ix[n].fillna(0)
pi = ki[ki.year.between(2015, 2025)].groupby("ADDR_SEGINTKEY").agg(ped_ksi=("ped", "sum"), bike_ksi=("bike", "sum"), fatal=("SEVERITYCODE", lambda s: (s == 4).sum()))
ix = ix.merge(pi, left_on="key", right_index=True, how="left").fillna({"ped_ksi": 0, "bike_ksi": 0, "fatal": 0})
F_INT = "{y} ~ C(legs_c) + n_principal + n_minor + n_collector + n_freeway + max_spd_c + logw + n_transit"
mi_all, ai_all = nb_fit(F_INT.format(y="ksi_all"), ix)
ix = eb(ix, mi_all, ai_all, "ksi_all")
mi_tr, ai_tr = nb_fit(F_INT.format(y="ksi_train"), ix)
ix_tr = eb(ix, mi_tr, ai_tr, "ksi_train")
ix_rank = ix.sort_values("excess", ascending=False)[["key", "name", "legs", "ksi_all", "ped_ksi", "bike_ksi", "fatal", "spf_expected", "eb_expected", "excess"]]
ix_rank.round(3).to_csv(RES / "intersection_ranking_all.csv", index=False)
ix_rank.head(50).round(3).to_csv(RES / "intersection_top50.csv", index=False)

# ---------------- holdout ----------------
def holdout(d_tr, ytrain, ytest):
    d_tr = d_tr.copy()
    # raw count with ties broken by the SPF prediction (otherwise zero-crash ties are ordered arbitrarily)
    d_tr["raw_tb"] = d_tr[ytrain] + d_tr.spf_expected * 1e-6
    out = {}
    for frac in (0.01, 0.05):
        out[f"top{int(frac*100)}%"] = {
            "raw count (2015-19), ties by SPF": capture(d_tr, "raw_tb", ytest, frac),
            "EB expected frequency (2015-19)": capture(d_tr, "eb_expected", ytest, frac),
            "EB excess (2015-19)": capture(d_tr, "excess", ytest, frac),
            "SPF only (no crash history)": capture(d_tr, "spf_expected", ytest, frac),
        }
    return out
H = {"segments": holdout(seg_tr, "ksi_train", "ksi_test"), "intersections": holdout(ix_tr, "ksi_train", "ksi_test")}

# ---------------- report ----------------
L = ["# Interim safety models", "", "Generated by `src/02_safety_models.py`.", "",
     "Window 2015-2025; holdout trains on 2015-2019 and tests on 2021-2025. No traffic volumes are available, so these models use road class, speed limit, length, width, transit class and slope (segments) or leg counts and classes (intersections) as proxies. 'Excess' is the EB expected KSI count minus what the model predicts for a site of that type, so it is not adjusted for unmeasured traffic volume.", ""]
for nm, m, a, d in [("Segments", m_all, a_all, seg), ("Intersections", mi_all, ai_all, ix)]:
    L += [f"## {nm}", f"- Sites: {len(d):,}; KSI assigned (2015-2025): {int(d.ksi_all.sum()):,}; sites with at least one KSI: {int((d.ksi_all>0).sum()):,}",
          f"- NB2 overdispersion alpha: {a:.3f}", ""]
L += ["## Holdout: share of 2021-2025 KSI falling in the top-ranked sites", "", "EB expected frequency is the right score for predicting future KSI. EB excess deliberately subtracts what road type already explains, so it flags sites that stand out from their peers rather than sites that will have the most crashes.", ""]
for nm, h in H.items():
    L += [f"### {nm}", "", "| Top share of sites | Ranking by | Share of test-period KSI captured |", "|---|---|---|"]
    for tk, v in h.items():
        for rk, val in v.items():
            L.append(f"| {tk} | {rk} | {val:.1%} |")
    L.append("")
L += ["## Top 10 segments by excess KSI", "", seg_rank.head(10)[["UNITDESC", "ARTDESCRIPT", "SPEEDLIMIT", "ksi_all", "fatal", "ped_ksi", "bike_ksi", "spf_expected", "eb_expected", "excess"]].round(2).to_markdown(index=False), "",
      "## Top 10 intersections by excess KSI", "", ix_rank.head(10)[["name", "legs", "ksi_all", "fatal", "ped_ksi", "bike_ksi", "spf_expected", "eb_expected", "excess"]].round(2).to_markdown(index=False), ""]
(DOCS / "models_interim.md").write_text("\n".join(L))
print("\n".join(L))
