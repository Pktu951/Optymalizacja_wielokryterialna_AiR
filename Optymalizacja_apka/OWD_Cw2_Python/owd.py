"""
owd.py - Optymalizacja wielokryterialna dyskretna (OWD), Ćw. 2.
Wyznaczanie zbioru punktów niezdominowanych P(X).

Algorytmy (wg instrukcji do ćwiczenia):
  1) 'nofilter' - naiwny BEZ filtracji punktów zdominowanych (z flagą fl),
  2) 'filter'   - naiwny Z filtracją punktów zdominowanych,
  3) 'ideal'    - oparty o punkt idealny (sortowanie odległości od punktu idealnego + filtracja).
Algorytmy 1 i 2 mogą być poprzedzone sortowaniem wstępnym wg wybranego kryterium.

Wewnętrznie wszystkie kryteria są minimalizowane (kryteria 'max' mnożone przez -1).
Liczone są: porównania punktów (P2), porównania współrzędnych (K2), porównania w fazie
sortowania (K1) oraz przeliczenie K1 na porównania punktów: P1 = K1 * P2 / K2, P = P1 + P2.

Jeżeli zainstalowany jest pakiet numba, pętle algorytmów są kompilowane (JIT) i działają
ok. 100x szybciej. Bez numby kod działa tak samo, tylko wolniej.
"""
import time

import numpy as np

try:
    from numba import njit
    HAS_NUMBA = True
except ImportError:  # pragma: no cover
    HAS_NUMBA = False

    def njit(*args, **kwargs):
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return lambda f: f

# typy zdarzeń zapisywanych do animacji
EV_ACTIVE, EV_CMP, EV_DEL, EV_ADDP, EV_FCMP = 0, 1, 2, 3, 4


# ---------------------------------------------------------------- generowanie danych
def generate(n, k, dist="uniform", params=None, seed=1):
    """Zwraca macierz n x k z wylosowanymi punktami."""
    p = params or {}
    rng = np.random.default_rng(seed)
    if dist == "uniform":
        return rng.uniform(p.get("a", 0.0), p.get("b", 2.0), size=(n, k))
    if dist == "gauss":
        return rng.normal(p.get("mu", 1.0), p.get("sigma", 1.0), size=(n, k))
    if dist == "exp":
        return rng.exponential(1.0 / p.get("lambda", 1.0), size=(n, k))
    if dist == "poisson":
        return rng.poisson(p.get("lambda", 2.0), size=(n, k)).astype(float)
    raise ValueError("Nieznany rozkład: " + dist)


def normalize(X, directions=None):
    """Kryteria 'max' mnożone przez -1 -> wszystkie kryteria minimalizowane."""
    X = np.array(X, dtype=np.float64, copy=True)
    if directions:
        for c, d in enumerate(directions):
            if d == "max":
                X[:, c] = -X[:, c]
    return np.ascontiguousarray(X)


# ---------------------------------------------------------------- jądra obliczeniowe
@njit(cache=True)
def _merge_sort_idx(idx, key):
    """Stabilne sortowanie przez scalanie tablicy indeksów wg key[idx]; zwraca liczbę porównań."""
    n = idx.shape[0]
    cmp = 0
    src = idx.copy()
    dst = np.empty_like(idx)
    width = 1
    while width < n:
        lo = 0
        while lo < n:
            mid = min(lo + width, n)
            hi = min(lo + 2 * width, n)
            i, j, o = lo, mid, lo
            while i < mid and j < hi:
                cmp += 1
                if key[src[j]] < key[src[i]]:
                    dst[o] = src[j]; j += 1
                else:
                    dst[o] = src[i]; i += 1
                o += 1
            while i < mid:
                dst[o] = src[i]; i += 1; o += 1
            while j < hi:
                dst[o] = src[j]; j += 1; o += 1
            lo += 2 * width
        src, dst = dst, src
        width *= 2
    idx[:] = src
    return cmp


@njit(cache=True)
def _compare(X, a, b):
    """Porównanie punktów a i b. Zwraca (wynik, liczba porównań współrzędnych):
    1 -> a dominuje b, -1 -> b dominuje a, 0 -> nieporównywalne lub równe.
    Porównanie kończy się, gdy tylko wiadomo, że punkty są nieporównywalne."""
    k = X.shape[1]
    a_b = False
    b_b = False
    for c in range(k):
        x = X[a, c]
        y = X[b, c]
        if x < y:
            a_b = True
            if b_b:
                return 0, c + 1
        elif x > y:
            b_b = True
            if a_b:
                return 0, c + 1
    if a_b:
        return 1, k
    if b_b:
        return -1, k
    return 0, k


@njit(cache=True)
def _log(ev, nev, record, t, a, b, r):
    if record and nev < ev.shape[0]:
        ev[nev, 0] = t; ev[nev, 1] = a; ev[nev, 2] = b; ev[nev, 3] = r
        return nev + 1
    return nev


@njit(cache=True)
def _nofilter(X, order, wrong, record, ev):
    n = X.shape[0]
    alive = np.ones(n, dtype=np.uint8)
    inP = np.zeros(n, dtype=np.uint8)
    pc = 0; cc = 0; nev = 0
    for i in range(n):
        if alive[i] == 0:
            continue
        y = i
        fl = 0
        nev = _log(ev, nev, record, EV_ACTIVE, order[y], -1, 0)
        for j in range(i + 1, n):
            if alive[j] == 0:
                continue
            r, c = _compare(X, order[y], order[j])
            pc += 1; cc += c
            nev = _log(ev, nev, record, EV_CMP, order[y], order[j], r)
            if r == 1:
                alive[j] = 0
                nev = _log(ev, nev, record, EV_DEL, order[j], -1, 0)
            elif r == -1:
                alive[y] = 0
                nev = _log(ev, nev, record, EV_DEL, order[y], -1, 0)
                y = j
                fl = 1
                nev = _log(ev, nev, record, EV_ACTIVE, order[y], -1, 0)
        if inP[order[y]] == 0:
            inP[order[y]] = 1
            nev = _log(ev, nev, record, EV_ADDP, order[y], -1, 0)
        # wariant błędny (wrong): Y zawsze usuwany, bez filtracji - demonstracja błędu
        if fl == 0 or wrong:
            alive[y] = 0
    return inP, pc, cc, nev


@njit(cache=True)
def _filter(X, order, record, ev):
    n = X.shape[0]
    alive = np.ones(n, dtype=np.uint8)
    inP = np.zeros(n, dtype=np.uint8)
    pc = 0; cc = 0; nev = 0
    left = n
    for i in range(n):
        if alive[i] == 0:
            continue
        y = i
        nev = _log(ev, nev, record, EV_ACTIVE, order[y], -1, 0)
        for j in range(i + 1, n):
            if alive[j] == 0:
                continue
            r, c = _compare(X, order[y], order[j])
            pc += 1; cc += c
            nev = _log(ev, nev, record, EV_CMP, order[y], order[j], r)
            if r == 1:
                alive[j] = 0; left -= 1
                nev = _log(ev, nev, record, EV_DEL, order[j], -1, 0)
            elif r == -1:
                alive[y] = 0; left -= 1
                nev = _log(ev, nev, record, EV_DEL, order[y], -1, 0)
                y = j
                nev = _log(ev, nev, record, EV_ACTIVE, order[y], -1, 0)
        inP[order[y]] = 1
        nev = _log(ev, nev, record, EV_ADDP, order[y], -1, 0)
        alive[y] = 0; left -= 1
        # filtracja: usuń z X wszystkie X(m) takie, że Y <= X(m).
        # Gdy został jeden element, porównany już z Y w pętli wewnętrznej
        # (leży za Y na liście), filtracja nie jest wykonywana (iteracja 2F w instrukcji).
        skip = False
        if left == 1:
            for m in range(y + 1, n):
                if alive[m]:
                    skip = True
                    break
        if left > 0 and not skip:
            for m in range(i + 1, n):
                if alive[m] == 0:
                    continue
                r, c = _compare(X, order[y], order[m])
                pc += 1; cc += c
                nev = _log(ev, nev, record, EV_FCMP, order[y], order[m], r)
                if r == 1:
                    alive[m] = 0; left -= 1
                    nev = _log(ev, nev, record, EV_DEL, order[m], -1, 0)
        if left == 1:  # w X został tylko jeden element - jest niezdominowany
            for m in range(i + 1, n):
                if alive[m]:
                    inP[order[m]] = 1; alive[m] = 0; left = 0
                    nev = _log(ev, nev, record, EV_ADDP, order[m], -1, 0)
                    break
        if left == 0:
            break
    return inP, pc, cc, nev


@njit(cache=True)
def _ideal(X, J, record, ev):
    """J - indeksy punktów posortowane rosnąco wg odległości od punktu idealnego."""
    n = X.shape[0]
    alive = np.ones(n, dtype=np.uint8)
    inP = np.zeros(n, dtype=np.uint8)
    pc = 0; cc = 0; nev = 0
    for m in range(n):
        if alive[m] == 0:
            continue
        y = J[m]
        # najbliższy punktowi idealnemu spośród pozostałych jest niezdominowany
        inP[y] = 1
        alive[m] = 0
        nev = _log(ev, nev, record, EV_ACTIVE, y, -1, 0)
        nev = _log(ev, nev, record, EV_ADDP, y, -1, 0)
        for q in range(m + 1, n):
            if alive[q] == 0:
                continue
            r, c = _compare(X, y, J[q])
            pc += 1; cc += c
            nev = _log(ev, nev, record, EV_FCMP, y, J[q], r)
            if r == 1:
                alive[q] = 0
                nev = _log(ev, nev, record, EV_DEL, J[q], -1, 0)
    return inP, pc, cc, nev


# ---------------------------------------------------------------- interfejs
ALGORITHMS = {
    "nofilter": "Naiwny bez filtracji",
    "filter": "Naiwny z filtracją",
    "ideal": "Punkt idealny",
}


class Result:
    """Wynik działania algorytmu."""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    def __repr__(self):
        return (f"Result({self.name}: |P|={len(self.P)}, P2={self.pointCmp}, K2={self.coordCmp}, "
                f"K1={self.sortCmp}, P={self.pointCmpTotal:.1f}, czas={self.timeMs:.3f} ms)")


def run(X, alg, presort=None, trace=False, wrong=False):
    """Uruchamia algorytm na danych X (już znormalizowanych do minimalizacji).
    alg: 'nofilter' | 'filter' | 'ideal'; presort: numer kryterium (0..k-1) lub None;
    trace: zapis przebiegu do animacji (lista zdarzeń); wrong: wariant błędny algorytmu 1."""
    X = np.ascontiguousarray(X, dtype=np.float64)
    n = X.shape[0]
    if alg not in ALGORITHMS:
        raise ValueError("Nieznany algorytm: " + alg)
    if alg == "ideal":
        presort = None
    cap = (4 * n * n + 10 * n + 10) if trace else 1
    ev = np.zeros((cap, 4), dtype=np.int64)
    ideal_pt = None
    t0 = time.perf_counter()
    sort_cmp = 0
    if alg == "ideal":
        ideal_pt = X.min(axis=0)
        d = ((X - ideal_pt) ** 2).sum(axis=1)
        J = np.arange(n, dtype=np.int64)
        sort_cmp = _merge_sort_idx(J, d)
        inP, pc, cc, nev = _ideal(X, J, trace, ev)
    else:
        order = np.arange(n, dtype=np.int64)
        if presort is not None:
            sort_cmp = _merge_sort_idx(order, np.ascontiguousarray(X[:, presort]))
        if alg == "nofilter":
            inP, pc, cc, nev = _nofilter(X, order, wrong, trace, ev)
        else:
            inP, pc, cc, nev = _filter(X, order, trace, ev)
    t1 = time.perf_counter()
    pc, cc = int(pc), int(cc)
    p1 = sort_cmp * pc / cc if cc > 0 else 0.0
    name = ALGORITHMS[alg] + (f" + sortowanie (kryt. {presort + 1})" if presort is not None else "")
    return Result(alg=alg, name=name, P=np.flatnonzero(inP), inP=inP.astype(bool),
                  pointCmp=pc, coordCmp=cc, sortCmp=int(sort_cmp),
                  pointCmpTotal=pc + p1, coordCmpTotal=cc + int(sort_cmp),
                  timeMs=(t1 - t0) * 1000.0,
                  trace=ev[:nev].tolist() if trace else None, ideal=ideal_pt)


def brute_force(X):
    """Przegląd zupełny (do weryfikacji): maska punktów niezdominowanych."""
    X = np.asarray(X)
    n = X.shape[0]
    res = np.ones(n, dtype=bool)
    for i in range(n):
        le = np.all(X <= X[i], axis=1)
        lt = np.any(X < X[i], axis=1)
        if np.any(le & lt):
            res[i] = False
    return res


def warmup():
    """Kompilacja JIT (numba) przed pomiarami czasu."""
    X = generate(50, 3, "uniform", seed=0)
    for a in ALGORITHMS:
        run(X, a)
        run(X, a, presort=0)
        run(X, a, trace=True)
    run(X, "nofilter", wrong=True)


TEST_SETS = {
    "Zestaw 1 (przykład z instrukcji, 12 pkt, k=2)": [
        [5, 5], [3, 6], [4, 4], [5, 3], [3, 3], [1, 8], [3, 4], [4, 5], [3, 10], [6, 6], [4, 1], [3, 5]],
    "Zestaw 2 (25 pkt, k=2)": [
        [-9.9711, -12.9227], [-3.4457, -9.848], [-7.9457, -3.3428], [-11.4903, 0.35851], [-2.893, 2.112],
        [-6.5593, -0.43486], [-10.5946, -3.7958], [0.61711, -8.2411], [-4.5631, 3.1734], [-8.9225, -10.5519],
        [-0.33194, -5.1174], [-10.5034, -9.4686], [-3.2687, -3.7756], [-6.7579, -3.8547], [-2.1778, -8.6548],
        [-6.5988, -8.6283], [1.6994, -11.3935], [3.0705, -7.8488], [-5.0102, -0.2123], [-1.3111, -6.707],
        [-0.55711, -10.8986], [1.9074, 0.80222], [-4.9074, -2.9805], [-0.10246, -6.6387], [-2.273, -1.564]],
}

METHODS = [  # konfiguracje używane w eksperymentach
    ("M1", "nofilter", None, "Naiwny bez filtracji"),
    ("M1S", "nofilter", 0, "Naiwny bez filtracji + sortowanie"),
    ("M2", "filter", None, "Naiwny z filtracją"),
    ("M2S", "filter", 0, "Naiwny z filtracją + sortowanie"),
    ("M3", "ideal", None, "Punkt idealny"),
]
