"""Testy poprawności: porównanie wyników wszystkich algorytmów z przeglądem zupełnym.
Uruchomienie: python test_owd.py"""
import numpy as np
import owd

owd.warmup()
bad = tot = 0
for dist in ["uniform", "gauss", "exp", "poisson"]:
    for n in [1, 2, 3, 5, 20, 100, 300]:
        for k in [1, 2, 3, 5]:
            for s in range(1, 11):
                X = owd.generate(n, k, dist, seed=s * 7 + n)
                bf = owd.brute_force(X)
                for alg in owd.ALGORITHMS:
                    for ps in (None, 0, k - 1):
                        r = owd.run(X, alg, presort=ps)
                        tot += 1
                        if not np.array_equal(r.inP, bf):
                            bad += 1
                            print("BŁĄD", dist, n, k, s, alg, ps)
print(f"testy: {tot}, błędne: {bad}")
X = np.array(owd.TEST_SETS["Zestaw 1 (przykład z instrukcji, 12 pkt, k=2)"], dtype=float)
for alg in owd.ALGORITHMS:
    r = owd.run(X, alg)
    print(r.name, [tuple(int(v) for v in X[i]) for i in r.P], "P2 =", r.pointCmp, "K2 =", r.coordCmp, "K1 =", r.sortCmp)
r = owd.run(X, "nofilter", wrong=True)
print("Wariant błędny (usunięcie Y bez filtracji):", [tuple(int(v) for v in X[i]) for i in r.P])
