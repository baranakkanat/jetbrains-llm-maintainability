"""Clustered within-developer estimates via Frisch-Waugh-Lovell, plus leave-one-author-out."""
import sys, warnings
import numpy as np, pandas as pd, statsmodels.api as sm
from statsmodels.stats.multitest import multipletests
warnings.filterwarnings("ignore")
sys.argv = ["x"]
from analyze_pooled import load, eligible_authors, OUTCOMES

d = load(["m_ideavim.csv", "m_intellij-scala.csv", "m_kotlin.csv"])
authors = eligible_authors(d)
w = d[d.group.isin(["human", "pair"]) & d.author.isin(authors)].copy()
w["pair"] = (w.group == "pair").astype(float)

def fwl(dd, col):
    fe = pd.get_dummies(dd[["author", "repo_month"]].astype(str), drop_first=True).astype(float)
    X = fe if col == "log_size" else pd.concat([fe, dd[["log_size"]]], axis=1)
    X = sm.add_constant(X)
    ry = np.asarray(sm.OLS(dd[col].values, X).fit().resid)
    rp = np.asarray(sm.OLS(dd["pair"].values, X).fit().resid)
    res = sm.OLS(ry, rp).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(dd["author"])[0]})
    return float(np.asarray(res.params)[0]), float(np.asarray(res.bse)[0]), float(np.asarray(res.pvalues)[0])

rows = []
for col, (kind, label) in OUTCOMES.items():
    dd = w.dropna(subset=[col])
    b, se, p = fwl(dd, col)
    loo = []
    for a in authors:
        sub = dd[dd.author != a]
        if sub.pair.sum() >= 10:
            loo.append(fwl(sub, col)[0])
    rows.append({"kind": kind, "outcome": label, "n": len(dd), "n_pair": int(dd.pair.sum()),
                 "effect": b, "ci_low": b - 1.96 * se, "ci_high": b + 1.96 * se, "p": p,
                 "loo_min": min(loo), "loo_max": max(loo),
                 "loo_same_sign": f"{sum(np.sign(x) == np.sign(b) for x in loo)}/{len(loo)}"})
out = pd.DataFrame(rows)
out["p_BH"] = multipletests(out["p"], method="fdr_bh")[1]
pd.set_option("display.width", 250); pd.set_option("display.float_format", lambda v: f"{v:.3f}")
print(f"authors={len(authors)}, commits={len(w)}, AI-paired={int(w.pair.sum())}")
print(out.to_string(index=False))
out.to_csv("within_developer_clustered.csv", index=False)
