"""Eksperymenty obliczeniowe Ćw. 2 (części A, B i 2).
Uruchomienie:  python run_experiments.py          (pełna seria, z numbą ok. 2-3 min)
               python run_experiments.py --quick  (szybka seria testowa, mniejsze K)
Wyniki zapisywane są do katalogu results/ (pliki CSV)."""
import csv
import itertools
import json
import os
import platform
import sys
import time
from pathlib import Path

import numpy as np

import owd

QUICK = "--quick" in sys.argv
OUT = Path(__file__).resolve().parent / "results"
OUT.mkdir(exist_ok=True)

DISTS = [("uniform", {"a": 0, "b": 2}), ("gauss", {"mu": 1, "sigma": 1})]
SIZES = [(100, 50), (1000, 25), (10000, 20)] if not QUICK else [(100, 10), (1000, 5), (10000, 2)]
KS = [2, 3, 4, 5, 10]


def timed_run(X, alg, presort, reps):
    total = 0.0
    for _ in range(reps):
        r = owd.run(X, alg, presort=presort)
        total += r.timeMs
    r.timeMs = total / reps
    return r


def cpu_name():
    try:
        if platform.system() == "Windows":
            import subprocess
            out = subprocess.run(["wmic", "cpu", "get", "name"], capture_output=True, text=True).stdout
            return out.strip().splitlines()[-1].strip()
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.processor() or "nieznany"


def mem_gb():
    try:
        if platform.system() == "Windows":
            import ctypes

            class MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("a", ctypes.c_ulonglong * 6)]
            m = MS()
            m.dwLength = ctypes.sizeof(MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return round(m.ullTotalPhys / 2 ** 30, 1)
        return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2 ** 30, 1)
    except Exception:
        return "?"


def main():
    print("numba:", "TAK" if owd.HAS_NUMBA else "NIE (obliczenia będą wolne - zainstaluj: pip install numba)")
    owd.warmup()
    env = {"cpu": cpu_name(), "cores": os.cpu_count(), "memGB": mem_gb(), "python": platform.python_version(),
           "numpy": np.__version__, "numba": owd.HAS_NUMBA, "platform": platform.platform(),
           "date": time.strftime("%Y-%m-%d %H:%M")}
    try:
        import numba
        env["numba_version"] = numba.__version__
    except ImportError:
        pass
    (OUT / "environment.json").write_text(json.dumps(env, indent=2, ensure_ascii=False), encoding="utf-8")

    # ------------------------------------------------------------ część A: zbiory testowe
    with open(OUT / "partA_test_sets.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["set", "n", "k", "method", "label", "nP", "pointCmp", "coordCmp", "sortCmp",
                    "pointCmpTotal", "coordCmpTotal", "timeMs", "note"])
        for name, rows in owd.TEST_SETS.items():
            X = np.array(rows, dtype=float)
            bf = owd.brute_force(X)
            for mid, alg, ps, label in owd.METHODS:
                r = timed_run(X, alg, ps, 2000)
                assert np.array_equal(r.inP, bf), (mid, name)
                w.writerow([name, len(X), X.shape[1], mid, label, len(r.P), r.pointCmp, r.coordCmp, r.sortCmp,
                            round(r.pointCmpTotal, 3), r.coordCmpTotal, round(r.timeMs, 6), ""])
            r = owd.run(X, "nofilter", wrong=True)
            fals = [tuple(X[i]) for i in r.P if not bf[i]]
            w.writerow([name, len(X), X.shape[1], "M1-BLAD", "wariant błędny: usunięcie Y bez filtracji", len(r.P),
                        r.pointCmp, r.coordCmp, 0, r.pointCmp, r.coordCmp, 0, f"fałszywe: {fals}"])
    print("Część A zakończona")

    # ------------------------------------------------------------ część B: zbiory losowe
    seed = 1000
    with open(OUT / "partB_random_raw.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["dist", "n", "k", "rep", "seed", "method", "nP", "pointCmp", "coordCmp", "sortCmp",
                    "pointCmpTotal", "coordCmpTotal", "timeMs"])
        for dist, params in DISTS:
            for n, K in SIZES:
                for k in KS:
                    t0 = time.time()
                    for rep in range(K):
                        seed += 1
                        X = owd.generate(n, k, dist, params, seed)
                        ref = None
                        for mid, alg, ps, _ in owd.METHODS:
                            reps = 20 if n == 100 else (3 if n == 1000 else 1)
                            r = timed_run(X, alg, ps, reps)
                            if ref is None:
                                ref = r.inP
                            elif not np.array_equal(ref, r.inP):
                                raise RuntimeError(f"Niezgodne wyniki {mid}")
                            w.writerow([dist, n, k, rep, seed, mid, len(r.P), r.pointCmp, r.coordCmp, r.sortCmp,
                                        round(r.pointCmpTotal, 3), r.coordCmpTotal, round(r.timeMs, 6)])
                        if n <= 1000 and not np.array_equal(ref, owd.brute_force(X)):
                            raise RuntimeError("Wynik niezgodny z przeglądem zupełnym")
                    print(f"B: {dist:7s} n={n:5d} k={k:2d} K={K:2d}  ({time.time() - t0:.1f} s)", flush=True)

    # ------------------------------------------------------------ część 2: zależności regresyjne
    seed = 50000
    reps2 = 50 if not QUICK else 10
    with open(OUT / "part2A_ratio_vs_k.csv", "w", newline="", encoding="utf-8") as fa, \
         open(OUT / "part2B_ratio_vs_diff.csv", "w", newline="", encoding="utf-8") as fb:
        wa, wb = csv.writer(fa), csv.writer(fb)
        wa.writerow(["dist", "rep", "k", "cols", "nP", "ratio"])
        wb.writerow(["dist", "rep", "k", "cols", "nP", "nP_k0", "ratio", "diff"])
        for dist, params in DISTS:
            for rep in range(reps2):  # 2A: k0 = 6, wszystkie kombinacje k kryteriów, k0 >= k > 1
                seed += 1
                X = owd.generate(100, 6, dist, params, seed)
                for k in range(2, 7):
                    for cols in itertools.combinations(range(6), k):
                        r = owd.run(X[:, cols], "ideal")
                        wa.writerow([dist, rep, k, "-".join(str(c + 1) for c in cols), len(r.P), len(r.P) / 100])
            for rep in range(reps2):  # 2B: k0 = 7, iloraz |P_k| / |P_k0| w funkcji k0 - k
                seed += 1
                X = owd.generate(100, 7, dist, params, seed)
                p0 = len(owd.run(X, "ideal").P)
                for k in range(1, 7):
                    for cols in itertools.combinations(range(7), k):
                        r = owd.run(X[:, cols], "ideal")
                        wb.writerow([dist, rep, k, "-".join(str(c + 1) for c in cols), len(r.P), p0, len(r.P) / p0, 7 - k])
    print("Część 2 zakończona. Wyniki w katalogu", OUT)


if __name__ == "__main__":
    main()
