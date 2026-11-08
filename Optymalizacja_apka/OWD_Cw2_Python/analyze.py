"""Opracowanie wyników eksperymentów (tabele zbiorcze, wykresy, regresje).
Uruchomienie: python3 experiments/analyze.py   (po node experiments/run_experiments.js)
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import curve_fit

ROOT = Path(__file__).resolve().parent
RES = ROOT / "results"
FIG = RES / "figures"
FIG.mkdir(parents=True, exist_ok=True)

METHODS = ["M1", "M1S", "M2", "M2S", "M3"]
MLABEL = {
    "M1": "M1 naiwny bez filtracji",
    "M1S": "M1S bez filtracji + sortowanie",
    "M2": "M2 naiwny z filtracją",
    "M2S": "M2S z filtracją + sortowanie",
    "M3": "M3 punkt idealny",
}
COLORS = {"M1": "#2a78d6", "M1S": "#eb6834", "M2": "#1baf7a", "M2S": "#eda100", "M3": "#e87ba4"}
MARKERS = {"M1": "o", "M1S": "s", "M2": "^", "M2S": "D", "M3": "v"}
DLABEL = {"uniform": "rozkład jednostajny U[0,2]", "gauss": "rozkład Gaussa N(1,1)"}

plt.rcParams.update({
    "font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e3e3e0", "grid.linewidth": 0.6,
    "axes.edgecolor": "#8a8984", "axes.labelcolor": "#33322f", "xtick.color": "#52514e", "ytick.color": "#52514e",
    "legend.frameon": False, "figure.dpi": 150, "lines.linewidth": 1.6, "lines.markersize": 4.5,
})

summary = {}

# ---------------------------------------------------------------- część A
a = pd.read_csv(RES / "partA_test_sets.csv")
summary["partA"] = a.fillna("").to_dict(orient="records")

# ---------------------------------------------------------------- część B
b = pd.read_csv(RES / "partB_random_raw.csv")
b["cc_per_pc"] = b.coordCmp / b.pointCmp
agg = (b.groupby(["dist", "n", "k", "method"])
        .agg(K=("rep", "count"), nP=("nP", "mean"), nP_sd=("nP", "std"),
             pc=("pointCmpTotal", "mean"), pc_sd=("pointCmpTotal", "std"),
             pc2=("pointCmp", "mean"), pc2_sd=("pointCmp", "std"),
             cc=("coordCmpTotal", "mean"), cc_sd=("coordCmpTotal", "std"),
             t=("timeMs", "mean"), t_sd=("timeMs", "std"),
             ccpc=("cc_per_pc", "mean"))
        .reset_index())
agg.to_csv(RES / "partB_summary.csv", index=False, float_format="%.6g")
summary["partB"] = agg.to_dict(orient="records")

# wykresy: liczba porównań punktów i czas w funkcji k, osobny panel dla każdego n
for metric, ylab, fname in [("pc", "liczba porównań punktów P (średnia)", "B_point_cmp"),
                            ("cc", "liczba porównań współrzędnych K (średnia)", "B_coord_cmp"),
                            ("t", "czas obliczeń [ms] (średnia)", "B_time")]:
    for dist in ["uniform", "gauss"]:
        fig, axes = plt.subplots(1, 3, figsize=(10, 3.3), constrained_layout=True)
        for ax, n in zip(axes, [100, 1000, 10000]):
            d = agg[(agg.dist == dist) & (agg.n == n)]
            for m in METHODS:
                dm = d[d.method == m].sort_values("k")
                ax.errorbar(dm.k, dm[metric], yerr=dm[metric + "_sd"], color=COLORS[m], marker=MARKERS[m],
                            label=MLABEL[m], capsize=2, elinewidth=0.8)
            ax.set_yscale("log")
            ax.set_xticks([2, 3, 4, 5, 10])
            ax.set_title(f"n = {n}", fontsize=10)
            ax.set_xlabel("liczba kryteriów k")
        axes[0].set_ylabel(ylab)
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="outside lower center", ncol=5, fontsize=8)
        fig.suptitle(f"{ylab.split(' (')[0].capitalize()} – {DLABEL[dist]}", fontsize=10)
        fig.savefig(FIG / f"{fname}_{dist}.png")
        plt.close(fig)

# udział punktów niezdominowanych
fig, axes = plt.subplots(1, 2, figsize=(9, 3.2), constrained_layout=True, sharey=True)
ncol = {100: "#2a78d6", 1000: "#eb6834", 10000: "#1baf7a"}
for ax, dist in zip(axes, ["uniform", "gauss"]):
    d = agg[(agg.dist == dist) & (agg.method == "M1")]
    for n in [100, 1000, 10000]:
        dn = d[d.n == n].sort_values("k")
        ax.errorbar(dn.k, dn.nP / n * 100, yerr=dn.nP_sd / n * 100, marker="o", color=ncol[n], label=f"n = {n}", capsize=2)
    ax.set_title(DLABEL[dist], fontsize=10)
    ax.set_xlabel("liczba kryteriów k")
    ax.set_xticks([2, 3, 4, 5, 10])
axes[0].set_ylabel("|P(X)| / n  [%]")
axes[0].legend()
fig.savefig(FIG / "B_pareto_share.png")
plt.close(fig)

# porównania współrzędnych na jedno porównanie punktów vs teoria 3 - 2^(2-k)
fig, ax = plt.subplots(figsize=(5, 3.1), constrained_layout=True)
ks = np.array([2, 3, 4, 5, 10])
d = b[(b.method == "M1") & (b.n == 1000)].groupby(["dist", "k"]).cc_per_pc.mean().reset_index()
for dist, col in [("uniform", "#2a78d6"), ("gauss", "#eb6834")]:
    dd = d[d.dist == dist]
    ax.plot(dd.k, dd.cc_per_pc, marker="o", color=col, label=f"pomiar M1, n=1000, {dist}")
kk = np.linspace(2, 10, 50)
kk = np.arange(2, 11)
ax.plot(kk, 3 - 2.0 ** (2 - kk), color="#52514e", linestyle="--", marker=".", label="teoria (losowa para): 3 − 2^(2−k)")
ax.set_xlabel("liczba kryteriów k")
ax.set_ylabel("porównania współrzędnych / porównanie punktów")
ax.legend(fontsize=7)
fig.savefig(FIG / "B_coord_per_point.png")
plt.close(fig)
summary["cc_per_pc"] = d.to_dict(orient="records")

# zysk względem M1 (n=10000)
gain = agg[agg.n == 10000].pivot_table(index=["dist", "k"], columns="method", values="pc")
gain = (gain.div(gain["M1"], axis=0) * 100).round(1)
summary["gain_10000"] = gain.reset_index().to_dict(orient="records")

# ---------------------------------------------------------------- część 2
def logistic(x, a, b):
    return 1.0 / (1.0 + np.exp(-(a + b * x)))


reg = {}
r2a = pd.read_csv(RES / "part2A_ratio_vs_k.csv")
r2b = pd.read_csv(RES / "part2B_ratio_vs_diff.csv")
for dist in ["uniform", "gauss"]:
    da = r2a[r2a.dist == dist]
    lr = stats.linregress(da.k, da.ratio)
    popt, _ = curve_fit(logistic, da.k, da.ratio, p0=[-3, 1])
    pred = logistic(da.k, *popt)
    r2_log = 1 - ((da.ratio - pred) ** 2).sum() / ((da.ratio - da.ratio.mean()) ** 2).sum()
    means = da.groupby("k").ratio.agg(["mean", "std", "count"]).reset_index()
    reg[f"2A_{dist}"] = dict(lin_a=lr.intercept, lin_b=lr.slope, lin_r2=lr.rvalue ** 2, lin_p=lr.pvalue, lin_se=lr.stderr,
                             log_a=popt[0], log_b=popt[1], log_r2=r2_log, nobs=len(da), means=means.to_dict(orient="records"))

    db = r2b[r2b.dist == dist]
    lrb = stats.linregress(db["diff"], db.ratio)
    # model wykładniczy ratio = exp(-c * diff)
    popt_e, _ = curve_fit(lambda x, c: np.exp(-c * x), db["diff"], db.ratio, p0=[0.5])
    pred_e = np.exp(-popt_e[0] * db["diff"])
    r2_e = 1 - ((db.ratio - pred_e) ** 2).sum() / ((db.ratio - db.ratio.mean()) ** 2).sum()
    means_b = db.groupby("diff").ratio.agg(["mean", "std", "count"]).reset_index()
    reg[f"2B_{dist}"] = dict(lin_a=lrb.intercept, lin_b=lrb.slope, lin_r2=lrb.rvalue ** 2, lin_p=lrb.pvalue, lin_se=lrb.stderr,
                             exp_c=popt_e[0], exp_r2=r2_e, nobs=len(db), means=means_b.to_dict(orient="records"))

fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.4), constrained_layout=True, sharey=True)
for ax, dist in zip(axes, ["uniform", "gauss"]):
    da = r2a[r2a.dist == dist]
    jitter = np.random.default_rng(0).uniform(-0.12, 0.12, len(da))
    ax.scatter(da.k + jitter, da.ratio, s=4, color="#9a9994", alpha=0.25, label="pojedyncze kombinacje kryteriów")
    m = da.groupby("k").ratio.mean()
    ax.plot(m.index, m.values, "o", color="#2a78d6", markersize=6, label="średnia")
    x = np.linspace(1, 8, 100)
    r = reg[f"2A_{dist}"]
    ax.plot(x, r["lin_a"] + r["lin_b"] * x, color="#eb6834", label=f"regresja liniowa (R²={r['lin_r2']:.3f})")
    ax.plot(x, logistic(x, r["log_a"], r["log_b"]), color="#1baf7a", label=f"regresja logistyczna (R²={r['log_r2']:.3f})")
    ax.set_title(DLABEL[dist], fontsize=10)
    ax.set_xlabel("liczba kryteriów k (podzbiory z k0 = 6)")
    ax.set_ylim(-0.05, 1.05)
axes[0].set_ylabel("|P(X)| / |X|")
axes[0].legend(fontsize=7, loc="upper left")
fig.savefig(FIG / "R2A_ratio_vs_k.png")
plt.close(fig)

fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.4), constrained_layout=True, sharey=True)
for ax, dist in zip(axes, ["uniform", "gauss"]):
    db = r2b[r2b.dist == dist]
    jitter = np.random.default_rng(1).uniform(-0.12, 0.12, len(db))
    ax.scatter(db["diff"] + jitter, db.ratio, s=3, color="#9a9994", alpha=0.2, label="pojedyncze kombinacje kryteriów")
    m = db.groupby("diff").ratio.mean()
    ax.plot(m.index, m.values, "o", color="#2a78d6", markersize=6, label="średnia")
    x = np.linspace(0, 6, 100)
    r = reg[f"2B_{dist}"]
    ax.plot(x, r["lin_a"] + r["lin_b"] * x, color="#eb6834", label=f"regresja liniowa (R²={r['lin_r2']:.3f})")
    ax.plot(x, np.exp(-r["exp_c"] * x), color="#1baf7a", label=f"model wykładniczy (R²={r['exp_r2']:.3f})")
    ax.set_title(DLABEL[dist], fontsize=10)
    ax.set_xlabel("różnica liczby kryteriów k0 − k (k0 = 7)")
axes[0].set_ylabel("|P_k(X)| / |P_k0(X)|")
axes[0].legend(fontsize=7)
fig.savefig(FIG / "R2B_ratio_vs_diff.png")
plt.close(fig)

summary["regression"] = reg
summary["environment"] = json.loads((RES / "environment.json").read_text())
(RES / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=float))
print(json.dumps(reg, indent=1, default=float)[:3000])
