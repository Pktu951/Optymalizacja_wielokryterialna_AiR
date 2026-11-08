"""
OWD Pareto Lab - aplikacja do eksperymentów obliczeniowych (Ćw. 2, OWD).
Uruchomienie:  python app.py

Moduły:
  * Kryteria - dodawanie/usuwanie/zmiana nazw, kierunek min/max dla każdego kryterium,
  * Dane - generowanie (rozkład jednostajny, Gaussa, wykładniczy, Poissona), zbiory testowe,
    wczytywanie z pliku CSV/TXT/XLSX, sortowanie wg wybranego kryterium, podgląd tabeli,
  * Algorytm - 3 metody wyznaczania punktów niezdominowanych + opcja sortowania wstępnego,
  * Wykres 2D / 3D / 4D (4. kryterium jako kolor),
  * Wyniki i benchmark - porównanie wszystkich metod na tych samych danych, zapis do CSV/XLSX,
  * Animacja przebiegu algorytmu (odtwarzanie krok po kroku, zapis do GIF),
  * Seria eksperymentów - losowe zbiory (n, k, K), średnie ± odchylenia, zapis do CSV.
"""
import csv
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import matplotlib
matplotlib.use("TkAgg")
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

import owd

C_PARETO, C_DOM, C_ACTIVE, C_CMP, C_REST = "#d1495b", "#9aa7a2", "#e8a33d", "#3b6fb6", "#33403c"
DIST_LABELS = {"jednostajny U[a,b]": "uniform", "Gaussa N(μ,σ)": "gauss", "wykładniczy Exp(λ)": "exp", "Poissona(λ)": "poisson"}
DIST_PARAMS = {"uniform": [("a", 0.0), ("b", 2.0)], "gauss": [("μ", 1.0), ("σ", 1.0)], "exp": [("λ", 1.0)], "poisson": [("λ", 2.0)]}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OWD Pareto Lab - Ćw. 2: wyznaczanie punktów niezdominowanych")
        self.geometry("1350x860")
        self.minsize(1100, 700)
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Accent.TButton", foreground="white", background="#1f6f5c")
        style.map("Accent.TButton", background=[("active", "#2b8a73")])

        self.crit = [{"name": "Kryterium 1", "dir": "min"}, {"name": "Kryterium 2", "dir": "min"}]
        self.X = None          # dane (oryginalne wartości)
        self.result = None     # ostatni wynik
        self.bench = None      # wyniki benchmarku
        self.frames = None     # klatki animacji
        self.frame_i = 0
        self.playing = False
        self.series_rows = []
        self.q = queue.Queue()
        self.stop_flag = threading.Event()

        owd.warmup()
        self._build_ui()
        self.load_data()
        self.solve()

    # ================================================================ UI
    def _build_ui(self):
        left = ttk.Frame(self, padding=8)
        left.pack(side="left", fill="y")
        right = ttk.Frame(self, padding=(0, 8, 8, 8))
        right.pack(side="left", fill="both", expand=True)

        # ---- kryteria
        fc = ttk.LabelFrame(left, text="Kryteria", padding=6)
        fc.pack(fill="x", pady=(0, 8))
        self.crit_frame = ttk.Frame(fc)
        self.crit_frame.pack(fill="x")
        ttk.Button(fc, text="Dodaj kryterium", command=self.add_crit).pack(anchor="w", pady=(6, 0))

        # ---- dane
        fd = ttk.LabelFrame(left, text="Dane wejściowe", padding=6)
        fd.pack(fill="x", pady=(0, 8))
        self.src = tk.StringVar(value="Zbiór losowy")
        ttk.Label(fd, text="Źródło").grid(row=0, column=0, sticky="w")
        cb = ttk.Combobox(fd, textvariable=self.src, state="readonly", width=26,
                          values=["Zbiór losowy", "Zbiór testowy z instrukcji", "Plik (CSV/TXT/XLSX)"])
        cb.grid(row=0, column=1, columnspan=3, sticky="ew", pady=2)
        cb.bind("<<ComboboxSelected>>", lambda e: self._src_changed())

        self.gen_frame = ttk.Frame(fd)
        self.gen_frame.grid(row=1, column=0, columnspan=4, sticky="ew")
        self.dist = tk.StringVar(value="jednostajny U[a,b]")
        ttk.Label(self.gen_frame, text="Rozkład").grid(row=0, column=0, sticky="w")
        dcb = ttk.Combobox(self.gen_frame, textvariable=self.dist, state="readonly", width=20, values=list(DIST_LABELS))
        dcb.grid(row=0, column=1, columnspan=3, sticky="ew", pady=2)
        dcb.bind("<<ComboboxSelected>>", lambda e: self._dist_changed())
        self.p1n, self.p2n = tk.StringVar(), tk.StringVar()
        self.p1, self.p2 = tk.StringVar(), tk.StringVar()
        ttk.Label(self.gen_frame, textvariable=self.p1n).grid(row=1, column=0, sticky="w")
        ttk.Entry(self.gen_frame, textvariable=self.p1, width=8).grid(row=1, column=1, sticky="w", pady=2)
        self.p2l = ttk.Label(self.gen_frame, textvariable=self.p2n)
        self.p2l.grid(row=1, column=2, sticky="w", padx=(6, 0))
        self.p2e = ttk.Entry(self.gen_frame, textvariable=self.p2, width=8)
        self.p2e.grid(row=1, column=3, sticky="w")
        self.n = tk.StringVar(value="60")
        self.seed = tk.StringVar(value="1")
        ttk.Label(self.gen_frame, text="Liczba punktów n").grid(row=2, column=0, sticky="w")
        ttk.Entry(self.gen_frame, textvariable=self.n, width=8).grid(row=2, column=1, sticky="w", pady=2)
        ttk.Label(self.gen_frame, text="Ziarno").grid(row=2, column=2, sticky="w", padx=(6, 0))
        ttk.Entry(self.gen_frame, textvariable=self.seed, width=8).grid(row=2, column=3, sticky="w")
        self._dist_changed()

        self.test_frame = ttk.Frame(fd)
        self.testset = tk.StringVar(value=list(owd.TEST_SETS)[0])
        ttk.Combobox(self.test_frame, textvariable=self.testset, state="readonly", width=34,
                     values=list(owd.TEST_SETS)).pack(fill="x")
        self.file_frame = ttk.Frame(fd)
        self.file_path = tk.StringVar(value="")
        ttk.Button(self.file_frame, text="Wybierz plik…", command=self.pick_file).pack(side="left")
        ttk.Label(self.file_frame, textvariable=self.file_path, width=24).pack(side="left", padx=4)

        ttk.Button(fd, text="Wczytaj / generuj", style="Accent.TButton", command=self.load_data).grid(
            row=3, column=0, columnspan=4, sticky="w", pady=(6, 2))
        ttk.Label(fd, text="Sortuj wg kryterium").grid(row=4, column=0, sticky="w")
        self.sort_crit = tk.StringVar()
        self.sort_cb = ttk.Combobox(fd, textvariable=self.sort_crit, state="readonly", width=14)
        self.sort_cb.grid(row=4, column=1, columnspan=2, sticky="w")
        ttk.Button(fd, text="Sortuj", command=self.sort_data).grid(row=4, column=3, sticky="e")

        # ---- algorytm
        fa = ttk.LabelFrame(left, text="Algorytm", padding=6)
        fa.pack(fill="x", pady=(0, 8))
        self.alg = tk.StringVar(value="1. Naiwny bez filtracji")
        ttk.Combobox(fa, textvariable=self.alg, state="readonly", width=30,
                     values=["1. Naiwny bez filtracji", "2. Naiwny z filtracją", "3. Punkt idealny"]).grid(
            row=0, column=0, columnspan=3, sticky="ew")
        self.presort = tk.BooleanVar(value=False)
        ttk.Checkbutton(fa, text="sortowanie wstępne wg kryt.", variable=self.presort).grid(row=1, column=0, sticky="w", pady=4)
        self.presort_crit = tk.StringVar()
        self.presort_cb = ttk.Combobox(fa, textvariable=self.presort_crit, state="readonly", width=12)
        self.presort_cb.grid(row=1, column=1, sticky="w")
        ttk.Button(fa, text="Rozwiąż", style="Accent.TButton", command=self.solve).grid(row=2, column=0, sticky="w")
        ttk.Button(fa, text="Benchmark (wszystkie)", command=self.run_bench).grid(row=2, column=1, sticky="w")

        self.status = tk.StringVar(value="")
        ttk.Label(left, textvariable=self.status, wraplength=300, foreground="#5d6a66").pack(fill="x")

        # ---- zakładki
        self.nb = ttk.Notebook(right)
        self.nb.pack(fill="both", expand=True)
        self._tab_plot()
        self._tab_data()
        self._tab_results()
        self._tab_anim()
        self._tab_series()
        self.render_crit()

    def _tab_plot(self):
        t = ttk.Frame(self.nb, padding=6)
        self.nb.add(t, text="Wykres")
        top = ttk.Frame(t)
        top.pack(fill="x")
        self.stats = tk.StringVar(value="")
        ttk.Label(top, textvariable=self.stats, font=("TkDefaultFont", 10, "bold")).pack(side="left")
        axf = ttk.Frame(t)
        axf.pack(fill="x", pady=4)
        self.ax_vars, self.ax_cbs = [], []
        for i, lab in enumerate(["Oś X", "Oś Y", "Oś Z", "Kolor (4D)"]):
            ttk.Label(axf, text=lab).pack(side="left", padx=(8 if i else 0, 2))
            v = tk.StringVar()
            c = ttk.Combobox(axf, textvariable=v, state="readonly", width=16)
            c.pack(side="left")
            c.bind("<<ComboboxSelected>>", lambda e: (self.draw_plot(), self.draw_frame()))
            self.ax_vars.append(v)
            self.ax_cbs.append(c)
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=t)
        NavigationToolbar2Tk(self.canvas, t).pack(side="bottom", fill="x")
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _tab_data(self):
        t = ttk.Frame(self.nb, padding=6)
        self.nb.add(t, text="Dane")
        self.data_info = tk.StringVar()
        ttk.Label(t, textvariable=self.data_info).pack(anchor="w")
        self.data_tree = self._tree(t)

    def _tab_results(self):
        t = ttk.Frame(self.nb, padding=6)
        self.nb.add(t, text="Wyniki i benchmark")
        self.res_info = tk.StringVar()
        ttk.Label(t, textvariable=self.res_info, justify="left", font=("Courier New", 10)).pack(anchor="w")
        bf = ttk.Frame(t)
        bf.pack(fill="x", pady=4)
        ttk.Button(bf, text="Zapisz P(X) do CSV/XLSX", command=self.export_p).pack(side="left")
        ttk.Button(bf, text="Zapisz benchmark do CSV/XLSX", command=self.export_bench).pack(side="left", padx=6)
        ttk.Label(t, text="Benchmark na bieżącym zbiorze").pack(anchor="w", pady=(6, 0))
        self.bench_tree = self._tree(t, height=6, expand=False)
        ttk.Label(t, text="Punkty niezdominowane P(X)").pack(anchor="w", pady=(6, 0))
        self.p_tree = self._tree(t)

    def _tab_anim(self):
        t = ttk.Frame(self.nb, padding=6)
        self.nb.add(t, text="Animacja")
        cf = ttk.Frame(t)
        cf.pack(fill="x")
        ttk.Button(cf, text="Przygotuj animację", style="Accent.TButton", command=self.build_anim).pack(side="left")
        self.play_btn = ttk.Button(cf, text="▶ Odtwórz", command=self.toggle_play)
        self.play_btn.pack(side="left", padx=4)
        ttk.Button(cf, text="Krok", command=self.step).pack(side="left")
        ttk.Button(cf, text="Od początku", command=self.rewind).pack(side="left", padx=4)
        ttk.Button(cf, text="Zapisz do GIF", command=self.save_gif).pack(side="left")
        ttk.Label(cf, text="  Prędkość [kroki/s]").pack(side="left")
        self.speed = tk.IntVar(value=8)
        ttk.Scale(cf, from_=1, to=60, variable=self.speed, orient="horizontal", length=140).pack(side="left")
        self.pos = tk.IntVar(value=0)
        self.pos_scale = ttk.Scale(t, from_=0, to=0, variable=self.pos, orient="horizontal",
                                   command=lambda v: self._seek(int(float(v))))
        self.pos_scale.pack(fill="x", pady=4)
        self.anim_info = tk.StringVar(value="Animacja przebiegu wybranego algorytmu (zbiory do 300 punktów).")
        ttk.Label(t, textvariable=self.anim_info).pack(anchor="w")
        self.afig = Figure(figsize=(8, 6), dpi=100)
        self.acanvas = FigureCanvasTkAgg(self.afig, master=t)
        self.acanvas.get_tk_widget().pack(fill="both", expand=True)

    def _tab_series(self):
        t = ttk.Frame(self.nb, padding=6)
        self.nb.add(t, text="Seria eksperymentów")
        ttk.Label(t, text="Dla każdej pary (n, k) generowanych jest K zbiorów; na każdym uruchamiane są wszystkie metody "
                          "(M1, M1S, M2, M2S, M3). Wyniki: średnia ± odchylenie standardowe.", wraplength=900).pack(anchor="w")
        f = ttk.Frame(t)
        f.pack(fill="x", pady=6)
        self.s_n, self.s_k, self.s_K = tk.StringVar(value="100, 1000"), tk.StringVar(value="2, 3, 4, 5, 10"), tk.StringVar(value="50, 25")
        self.s_dist, self.s_seed = tk.StringVar(value="jednostajny U[0,2]"), tk.StringVar(value="1000")
        for i, (lab, var, w) in enumerate([("Wartości n", self.s_n, 16), ("Wartości k", self.s_k, 16), ("K (liczba zbiorów)", self.s_K, 10)]):
            ttk.Label(f, text=lab).grid(row=0, column=2 * i, sticky="w", padx=(0 if i == 0 else 10, 2))
            ttk.Entry(f, textvariable=var, width=w).grid(row=0, column=2 * i + 1)
        ttk.Label(f, text="Rozkład").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Combobox(f, textvariable=self.s_dist, state="readonly", width=18,
                     values=["jednostajny U[0,2]", "Gaussa N(1,1)", "wykładniczy Exp(1)", "Poissona(2)"]).grid(row=1, column=1)
        ttk.Label(f, text="Ziarno").grid(row=1, column=2, sticky="w", padx=(10, 2))
        ttk.Entry(f, textvariable=self.s_seed, width=10).grid(row=1, column=3, sticky="w")
        bf = ttk.Frame(t)
        bf.pack(fill="x")
        self.s_run = ttk.Button(bf, text="Uruchom serię", style="Accent.TButton", command=self.run_series)
        self.s_run.pack(side="left")
        ttk.Button(bf, text="Zatrzymaj", command=self.stop_flag.set).pack(side="left", padx=4)
        ttk.Button(bf, text="Zapisz wyniki do CSV", command=self.export_series).pack(side="left")
        self.s_prog = ttk.Progressbar(bf, length=200, mode="determinate")
        self.s_prog.pack(side="left", padx=10)
        self.s_log = tk.Text(t, height=6, font=("TkFixedFont", 9))
        self.s_log.pack(fill="x", pady=4)
        self.s_tree = self._tree(t)

    def _tree(self, parent, height=12, expand=True):
        fr = ttk.Frame(parent)
        fr.pack(fill="both", expand=expand)
        tree = ttk.Treeview(fr, show="headings", height=height)
        sy = ttk.Scrollbar(fr, orient="vertical", command=tree.yview)
        sx = ttk.Scrollbar(fr, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        tree.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        fr.rowconfigure(0, weight=1)
        fr.columnconfigure(0, weight=1)
        return tree

    @staticmethod
    def fill_tree(tree, cols, rows, widths=None):
        tree.delete(*tree.get_children())
        tree["columns"] = [f"c{i}" for i in range(len(cols))]
        for i, c in enumerate(cols):
            tree.heading(f"c{i}", text=c)
            tree.column(f"c{i}", width=(widths[i] if widths else 110), anchor="e" if i else "w", stretch=True)
        for r in rows:
            tree.insert("", "end", values=r)

    # ================================================================ kryteria
    def render_crit(self):
        for w in self.crit_frame.winfo_children():
            w.destroy()
        ttk.Label(self.crit_frame, text="#").grid(row=0, column=0)
        ttk.Label(self.crit_frame, text="Nazwa").grid(row=0, column=1, sticky="w")
        ttk.Label(self.crit_frame, text="Kierunek").grid(row=0, column=2, sticky="w")
        for i, c in enumerate(self.crit):
            ttk.Label(self.crit_frame, text=str(i + 1)).grid(row=i + 1, column=0, padx=2)
            nv = tk.StringVar(value=c["name"])
            e = ttk.Entry(self.crit_frame, textvariable=nv, width=16)
            e.grid(row=i + 1, column=1, pady=1)
            nv.trace_add("write", lambda *a, i=i, v=nv: self._rename(i, v.get()))
            dv = tk.StringVar(value=c["dir"])
            d = ttk.Combobox(self.crit_frame, textvariable=dv, values=["min", "max"], state="readonly", width=5)
            d.grid(row=i + 1, column=2, padx=2)
            d.bind("<<ComboboxSelected>>", lambda e, i=i, v=dv: self._set_dir(i, v.get()))
            b = ttk.Button(self.crit_frame, text="✕", width=3, command=lambda i=i: self.del_crit(i))
            b.grid(row=i + 1, column=3)
            if len(self.crit) <= 1:
                b.state(["disabled"])
        self.refresh_selectors()

    def _rename(self, i, name):
        self.crit[i]["name"] = name
        self.refresh_selectors(keep=True)

    def _set_dir(self, i, d):
        self.crit[i]["dir"] = d
        self.result = None
        self.draw_plot()
        self.update_results()

    def add_crit(self):
        self.crit.append({"name": f"Kryterium {len(self.crit) + 1}", "dir": "min"})
        self.render_crit()
        if self.src.get() == "Zbiór losowy":
            self.load_data()
        else:
            self.X = None
            self.after_data_change()

    def del_crit(self, i):
        self.crit.pop(i)
        if self.X is not None:
            self.X = np.delete(self.X, i, axis=1)
        self.render_crit()
        self.after_data_change()

    def crit_labels(self):
        return [f"{i + 1}. {c['name']}" for i, c in enumerate(self.crit)]

    def refresh_selectors(self, keep=False):
        labs = self.crit_labels()
        k = len(labs)
        for cb, var in [(self.sort_cb, self.sort_crit), (self.presort_cb, self.presort_crit)]:
            idx = cb.current() if keep and cb.current() >= 0 else 0
            cb["values"] = labs
            var.set(labs[min(idx, k - 1)])
        for a, (cb, var) in enumerate(zip(self.ax_cbs, self.ax_vars)):
            vals = (["—"] if a >= 2 else []) + labs
            old = cb.current() if keep else -1
            cb["values"] = vals
            if old >= 0 and old < len(vals):
                var.set(vals[old])
            else:
                var.set(labs[a] if a < k else "—")

    # ================================================================ dane
    def _src_changed(self):
        for f in (self.gen_frame, self.test_frame, self.file_frame):
            f.grid_forget()
        f = {"Zbiór losowy": self.gen_frame, "Zbiór testowy z instrukcji": self.test_frame}.get(self.src.get(), self.file_frame)
        f.grid(row=1, column=0, columnspan=4, sticky="ew")

    def _dist_changed(self):
        p = DIST_PARAMS[DIST_LABELS[self.dist.get()]]
        self.p1n.set(p[0][0])
        self.p1.set(str(p[0][1]))
        if len(p) > 1:
            self.p2n.set(p[1][0])
            self.p2.set(str(p[1][1]))
            self.p2l.grid()
            self.p2e.grid()
        else:
            self.p2l.grid_remove()
            self.p2e.grid_remove()

    def pick_file(self):
        path = filedialog.askopenfilename(filetypes=[("Dane", "*.csv *.txt *.dat *.xlsx"), ("Wszystkie", "*.*")])
        if path:
            self.file_path.set(path)

    def _set_crit_count(self, k):
        while len(self.crit) < k:
            self.crit.append({"name": f"Kryterium {len(self.crit) + 1}", "dir": "min"})
        del self.crit[k:]
        self.render_crit()

    def load_data(self):
        src = self.src.get()
        try:
            if src == "Zbiór losowy":
                d = DIST_LABELS[self.dist.get()]
                a, b = float(self.p1.get()), float(self.p2.get() or 0)
                params = {"uniform": {"a": a, "b": b}, "gauss": {"mu": a, "sigma": b}}.get(d, {"lambda": a})
                n = max(1, min(200000, int(self.n.get())))
                self.X = owd.generate(n, len(self.crit), d, params, int(self.seed.get()))
            elif src == "Zbiór testowy z instrukcji":
                self.X = np.array(owd.TEST_SETS[self.testset.get()], dtype=float)
                self._set_crit_count(self.X.shape[1])
            else:
                path = self.file_path.get()
                if not path:
                    messagebox.showinfo("Dane", "Wybierz plik z danymi.")
                    return
                self.X = read_file(path)
                self._set_crit_count(self.X.shape[1])
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Błąd danych", str(e))
            return
        self.after_data_change()

    def sort_data(self):
        if self.X is None:
            return
        c = self.sort_cb.current()
        key = self.X[:, c] * (-1 if self.crit[c]["dir"] == "max" else 1)
        self.X = self.X[np.argsort(key, kind="stable")]
        self.after_data_change()

    def after_data_change(self):
        self.status.set("")
        self.result = None
        self.bench = None
        self.frames = None
        self.render_data()
        self.draw_plot()
        self.update_results()
        self.render_bench()

    def render_data(self):
        if self.X is None:
            return
        n, k = self.X.shape
        lim = min(n, 3000)
        self.data_info.set(f"n = {n} punktów, k = {k} kryteriów" + (f" (pokazano pierwsze {lim})" if n > lim else ""))
        cols = ["nr"] + [f"{c['name']} ({c['dir']})" for c in self.crit]
        self.fill_tree(self.data_tree, cols, [[i + 1] + [f"{v:.4f}" for v in self.X[i]] for i in range(lim)], [60] + [140] * k)

    # ================================================================ obliczenia
    def norm(self):
        return owd.normalize(self.X, [c["dir"] for c in self.crit])

    def alg_id(self):
        return ["nofilter", "filter", "ideal"][int(self.alg.get()[0]) - 1]

    def presort_val(self):
        return self.presort_cb.current() if self.presort.get() else None

    def solve(self):
        if self.X is None:
            self.load_data()
        self.result = owd.run(self.norm(), self.alg_id(), presort=self.presort_val())
        self.status.set(f"{self.result.name}: |P(X)| = {len(self.result.P)}")
        self.draw_plot()
        self.update_results()

    def run_bench(self):
        if self.X is None:
            self.load_data()
        X = self.norm()
        reps = 20 if X.shape[0] <= 1000 else 1
        ps = self.presort_cb.current() if self.presort_cb.current() >= 0 else 0
        out = []
        for mid, alg, presort, label in owd.METHODS:
            tot = 0.0
            for _ in range(reps):
                r = owd.run(X, alg, presort=None if presort is None else ps)
                tot += r.timeMs
            r.timeMs = tot / reps
            r.label = label + (f" (kryt. {ps + 1})" if presort is not None else "")
            out.append(r)
        self.bench = out
        if self.result is None:
            self.result = out[0]
        self.render_bench()
        self.update_results()
        self.draw_plot()
        self.nb.select(2)

    def update_results(self):
        r = self.result
        if r is None:
            self.stats.set("" if self.X is None else f"n = {self.X.shape[0]}, k = {self.X.shape[1]} - kliknij „Rozwiąż”")
            self.res_info.set("")
            self.fill_tree(self.p_tree, ["-"], [])
            return
        self.stats.set(f"{r.name}   |P(X)| = {len(r.P)}   porównania punktów P = {r.pointCmpTotal:.1f}   "
                       f"porównania współrzędnych K = {r.coordCmpTotal}   czas = {r.timeMs:.3f} ms")
        self.res_info.set(
            f"{r.name}\n"
            f"|P(X)|                               = {len(r.P)}\n"
            f"P2 - porównania punktów             = {r.pointCmp}\n"
            f"K2 - porównania współrzędnych       = {r.coordCmp}\n"
            f"K1 - porównania przy sortowaniu     = {r.sortCmp}\n"
            f"P = P2 + K1*P2/K2 (łącznie)         = {r.pointCmpTotal:.1f}\n"
            f"K = K1 + K2 (łącznie)               = {r.coordCmpTotal}\n"
            f"czas obliczeń                       = {r.timeMs:.4f} ms   (numba: {'tak' if owd.HAS_NUMBA else 'nie'})")
        cols = ["nr punktu"] + [c["name"] for c in self.crit]
        self.fill_tree(self.p_tree, cols, [[i + 1] + [f"{v:.4f}" for v in self.X[i]] for i in r.P[:5000]], [80] + [140] * len(self.crit))

    def render_bench(self):
        if not self.bench:
            self.fill_tree(self.bench_tree, ["Kliknij „Benchmark”, aby porównać wszystkie metody na tych samych danych"], [], [600])
            return
        cols = ["Metoda", "|P|", "P2", "K2", "K1 (sort.)", "P łącznie", "K łącznie", "czas [ms]"]
        rows = [[r.label, len(r.P), r.pointCmp, r.coordCmp, r.sortCmp, f"{r.pointCmpTotal:.1f}", r.coordCmpTotal, f"{r.timeMs:.4f}"] for r in self.bench]
        self.fill_tree(self.bench_tree, cols, rows, [270, 50, 80, 80, 80, 90, 90, 80])

    # ================================================================ wykresy
    def axes_idx(self):
        k = self.X.shape[1]
        if k == 1:
            return [0, -1, -1, -1]
        if k == 2:
            return [0, 1, -1, -1]
        res = []
        for a, cb in enumerate(self.ax_cbs):
            i = cb.current()
            res.append(i if a < 2 else i - 1)
        return res

    def _scatter(self, ax, idx, axi, is3, **kw):
        if len(idx) == 0:
            return None
        x = self.X[idx, axi[0]]
        y = self.X[idx, axi[1]] if axi[1] >= 0 else np.zeros(len(idx))
        if is3:
            return ax.scatter(x, y, self.X[idx, axi[2]], **kw)
        return ax.scatter(x, y, **kw)

    def _setup_axes(self, fig, axi, title):
        fig.clear()
        is3 = axi[2] >= 0
        ax = fig.add_subplot(111, projection="3d" if is3 else None)
        lab = lambda i: f"{self.crit[i]['name']} ({self.crit[i]['dir']})"  # noqa: E731
        ax.set_xlabel(lab(axi[0]))
        if axi[1] >= 0:
            ax.set_ylabel(lab(axi[1]))
        if is3:
            ax.set_zlabel(lab(axi[2]))
        else:
            ax.grid(True, color="#e3e3e0")
        ax.set_title(title, fontsize=10)
        return ax, is3

    def draw_plot(self):
        if self.X is None:
            return
        axi = self.axes_idx()
        r = self.result
        ax, is3 = self._setup_axes(self.fig, axi, r.name if r else "Zbiór danych")
        n = self.X.shape[0]
        dom = np.flatnonzero(~r.inP) if r else np.arange(n)
        s = 12 if is3 else 22
        if axi[3] >= 0:
            sc = self._scatter(ax, dom, axi, is3, c=self.X[dom, axi[3]], cmap="viridis", s=s, alpha=0.8,
                               label="zdominowane" if r else "zbiór X")
            if sc is not None:
                self.fig.colorbar(sc, ax=ax, shrink=0.6, label=self.crit[axi[3]]["name"])
        else:
            self._scatter(ax, dom, axi, is3, color=C_DOM, s=s, alpha=0.8, label="zdominowane" if r else "zbiór X")
        if r is not None:
            self._scatter(ax, r.P, axi, is3, color=C_PARETO, marker="D", s=s * 2.2, edgecolors="black",
                          linewidths=0.6, label="niezdominowane P(X)")
        ax.legend(loc="best", fontsize=8)
        self.fig.tight_layout()
        self.canvas.draw_idle()

    # ================================================================ animacja
    def build_anim(self):
        if self.X is None:
            self.load_data()
        n = self.X.shape[0]
        if n > 300:
            self.anim_info.set("Animacja jest dostępna dla zbiorów do 300 punktów. Zmniejsz n.")
            return
        r = owd.run(self.norm(), self.alg_id(), presort=self.presort_val(), trace=True)
        frames = []
        dele, inP = np.zeros(n, bool), np.zeros(n, bool)
        active, cmp_, msg, nc = -1, -1, "Start", 0

        def snap():
            frames.append((active, cmp_, dele.copy(), inP.copy(), msg, nc))

        snap()
        if r.ideal is not None:
            msg = "Punkt idealny (min. każdej współrzędnej): (" + ", ".join(f"{v:.3f}" for v in r.ideal) + ")"
            snap()
        for t, a, b, res in r.trace:
            if t == owd.EV_ACTIVE:
                active, cmp_, msg = a, -1, f"Element aktywny Y = nr {a + 1}"
            elif t in (owd.EV_CMP, owd.EV_FCMP):
                nc += 1
                cmp_ = b
                rel = {1: "Y dominuje", -1: "Y jest zdominowany", 0: "nieporównywalne"}[res]
                msg = f"{'Filtracja: ' if t == owd.EV_FCMP else ''}porównanie Y = nr {a + 1} z nr {b + 1}: {rel}"
            elif t == owd.EV_DEL:
                dele[a] = True
                msg += f" → usunięto nr {a + 1}"
            elif t == owd.EV_ADDP:
                inP[a] = True
                msg = f"Dodano nr {a + 1} do P(X)"
            snap()
        active, cmp_, msg = -1, -1, f"Koniec: |P(X)| = {len(r.P)}, porównań punktów: {r.pointCmp}"
        snap()
        self.frames, self.frame_i, self.anim_name = frames, 0, r.name
        self.pos_scale.configure(to=len(frames) - 1)
        self.draw_frame()

    def draw_frame(self, fig=None):
        if not self.frames:
            return
        fig = fig or self.afig
        active, cmp_, dele, inP, msg, nc = self.frames[self.frame_i]
        axi = self.axes_idx()
        ax, is3 = self._setup_axes(fig, axi, self.anim_name)
        n = self.X.shape[0]
        s = 25 if is3 else 40
        allm = np.ones(n, bool)
        if active >= 0:
            allm[active] = False
        if cmp_ >= 0:
            allm[cmp_] = False
        rest = np.flatnonzero(allm & ~dele & ~inP)
        dl = np.flatnonzero(allm & dele & ~inP)
        pp = np.flatnonzero(allm & inP)
        self._scatter(ax, rest, axi, is3, color=C_REST, s=s, alpha=0.6, label="do sprawdzenia")
        self._scatter(ax, dl, axi, is3, color=C_DOM, marker="x", s=s, label="usunięte (zdominowane)")
        self._scatter(ax, pp, axi, is3, color=C_PARETO, marker="D", s=s * 1.4, edgecolors="black", linewidths=0.5, label="P(X)")
        if cmp_ >= 0:
            self._scatter(ax, np.array([cmp_]), axi, is3, color=C_CMP, s=s * 3, label="porównywany")
        if active >= 0:
            self._scatter(ax, np.array([active]), axi, is3, color=C_ACTIVE, s=s * 4, edgecolors="black", label="aktywny Y")
        ax.legend(loc="best", fontsize=8)
        fig.tight_layout()
        if fig is self.afig:
            self.acanvas.draw_idle()
            self.anim_info.set(f"Krok {self.frame_i}/{len(self.frames) - 1} · porównań: {nc} · {msg}")
            self.pos.set(self.frame_i)

    def _seek(self, i):
        if self.frames and i != self.frame_i:
            self.frame_i = max(0, min(i, len(self.frames) - 1))
            self.draw_frame()

    def step(self):
        if not self.frames:
            self.build_anim()
        elif self.frame_i < len(self.frames) - 1:
            self.frame_i += 1
            self.draw_frame()

    def rewind(self):
        self.playing = False
        self.play_btn.configure(text="▶ Odtwórz")
        self.frame_i = 0
        self.draw_frame()

    def toggle_play(self):
        if self.playing:
            self.playing = False
            self.play_btn.configure(text="▶ Odtwórz")
            return
        if not self.frames:
            self.build_anim()
        if not self.frames:
            return
        self.playing = True
        self.play_btn.configure(text="❚❚ Pauza")
        self._tick()

    def _tick(self):
        if not self.playing:
            return
        if self.frame_i >= len(self.frames) - 1:
            self.playing = False
            self.play_btn.configure(text="▶ Odtwórz")
            return
        self.frame_i += 1
        self.draw_frame()
        self.after(int(1000 / max(1, self.speed.get())), self._tick)

    def save_gif(self):
        if not self.frames:
            self.build_anim()
        if not self.frames:
            return
        path = filedialog.asksaveasfilename(defaultextension=".gif", filetypes=[("GIF", "*.gif")])
        if not path:
            return
        from matplotlib.animation import FuncAnimation, PillowWriter
        fig = Figure(figsize=(7, 5.5), dpi=90)
        cur = self.frame_i

        def upd(i):
            self.frame_i = i
            self.draw_frame(fig)
            fig.suptitle(self.frames[i][4], fontsize=8)

        anim = FuncAnimation(fig, upd, frames=len(self.frames))
        self.status.set("Zapisywanie GIF…")
        self.update_idletasks()
        anim.save(path, writer=PillowWriter(fps=max(1, self.speed.get())))
        self.frame_i = cur
        self.status.set(f"Zapisano animację: {path}")

    # ================================================================ seria eksperymentów
    def run_series(self):
        try:
            ns = [int(x) for x in self.s_n.get().replace(";", ",").split(",") if x.strip()]
            ks = [int(x) for x in self.s_k.get().replace(";", ",").split(",") if x.strip()]
            Ks = [int(x) for x in self.s_K.get().replace(";", ",").split(",") if x.strip()]
            seed = int(self.s_seed.get())
        except ValueError:
            messagebox.showerror("Seria", "Wpisz liczby oddzielone przecinkami.")
            return
        dist = {"jednostajny U[0,2]": ("uniform", {"a": 0, "b": 2}), "Gaussa N(1,1)": ("gauss", {"mu": 1, "sigma": 1}),
                "wykładniczy Exp(1)": ("exp", {"lambda": 1}), "Poissona(2)": ("poisson", {"lambda": 2})}[self.s_dist.get()]
        jobs = [(n, k, Ks[min(a, len(Ks) - 1)]) for a, n in enumerate(ns) for k in ks]
        self.s_prog.configure(maximum=sum(j[2] for j in jobs), value=0)
        self.s_log.delete("1.0", "end")
        self.series_rows = []
        self.stop_flag.clear()
        self.s_run.state(["disabled"])
        threading.Thread(target=self._series_worker, args=(jobs, dist, seed), daemon=True).start()
        self.after(100, self._poll)

    def _series_worker(self, jobs, dist, seed):
        import time
        for n, k, K in jobs:
            t0 = time.time()
            for rep in range(K):
                if self.stop_flag.is_set():
                    self.q.put(("log", "Przerwano."))
                    self.q.put(("done", None))
                    return
                seed += 1
                X = owd.generate(n, k, dist[0], dist[1], seed)
                ref = None
                for mid, alg, ps, label in owd.METHODS:
                    r = owd.run(X, alg, presort=ps)
                    if ref is not None and not np.array_equal(ref, r.inP):
                        self.q.put(("log", f"UWAGA: niezgodne wyniki {mid}"))
                    ref = r.inP if ref is None else ref
                    self.q.put(("row", dict(dist=dist[0], n=n, k=k, rep=rep, seed=seed, method=mid, label=label,
                                            nP=len(r.P), pc=r.pointCmpTotal, cc=r.coordCmpTotal, pc2=r.pointCmp, t=r.timeMs)))
                self.q.put(("prog", 1))
            self.q.put(("log", f"n={n} k={k} K={K}: {time.time() - t0:.2f} s"))
            self.q.put(("table", None))
        self.q.put(("log", "Gotowe."))
        self.q.put(("done", None))

    def _poll(self):
        done = False
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "row":
                    self.series_rows.append(val)
                elif kind == "prog":
                    self.s_prog.step(val)
                elif kind == "log":
                    self.s_log.insert("end", val + "\n")
                    self.s_log.see("end")
                elif kind == "table":
                    self.render_series()
                elif kind == "done":
                    done = True
        except queue.Empty:
            pass
        if done:
            self.render_series()
            self.s_run.state(["!disabled"])
        else:
            self.after(100, self._poll)

    def render_series(self):
        groups = {}
        for r in self.series_rows:
            groups.setdefault((r["n"], r["k"], r["method"]), []).append(r)
        ms = lambda a, d: f"{np.mean(a):.{d}f} ± {np.std(a, ddof=1) if len(a) > 1 else 0:.{d}f}"  # noqa: E731
        rows = []
        for (n, k, m), arr in groups.items():
            rows.append([arr[0]["label"], n, k, len(arr), f"{np.mean([x['nP'] for x in arr]):.1f}",
                         ms([x["pc"] for x in arr], 0), ms([x["cc"] for x in arr], 0), ms([x["t"] for x in arr], 3)])
        self.fill_tree(self.s_tree, ["Metoda", "n", "k", "K", "|P| śr.", "porównania punktów", "porównania współrzędnych", "czas [ms]"],
                       rows, [260, 60, 40, 40, 70, 170, 190, 140])

    # ================================================================ eksport
    def _save(self, header, rows, default):
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=default,
                                            filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx")])
        if not path:
            return
        if path.lower().endswith(".xlsx"):
            try:
                from openpyxl import Workbook
            except ImportError:
                messagebox.showerror("Zapis", "Do zapisu XLSX potrzebny jest pakiet openpyxl (pip install openpyxl).")
                return
            wb = Workbook()
            ws = wb.active
            ws.append(header)
            for r in rows:
                ws.append(list(r))
            wb.save(path)
        else:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(header)
                w.writerows(rows)
        self.status.set(f"Zapisano: {path}")

    def export_p(self):
        if self.result is None:
            return
        self._save(["nr"] + [c["name"] for c in self.crit],
                   [[int(i) + 1] + [float(v) for v in self.X[i]] for i in self.result.P], "punkty_niezdominowane.csv")

    def export_bench(self):
        if not self.bench:
            return
        self._save(["metoda", "|P|", "P2", "K2", "K1", "P", "K", "czas_ms"],
                   [[r.label, len(r.P), r.pointCmp, r.coordCmp, r.sortCmp, r.pointCmpTotal, r.coordCmpTotal, r.timeMs] for r in self.bench],
                   "benchmark.csv")

    def export_series(self):
        if not self.series_rows:
            return
        keys = ["dist", "n", "k", "rep", "seed", "method", "nP", "pc", "cc", "pc2", "t"]
        self._save(["rozklad", "n", "k", "powtorzenie", "ziarno", "metoda", "|P|", "porownania_punktow",
                    "porownania_wspolrzednych", "P2", "czas_ms"], [[r[x] for x in keys] for r in self.series_rows],
                   "seria_eksperymentow.csv")


def read_file(path):
    """Wczytuje macierz danych z pliku CSV/TXT (separator , ; tab spacja) lub XLSX; pomija wiersze nieliczbowe."""
    rows = []
    if path.lower().endswith(".xlsx"):
        from openpyxl import load_workbook
        for r in load_workbook(path, read_only=True, data_only=True).active.iter_rows(values_only=True):
            vals = [v for v in r if v is not None]
            try:
                rows.append([float(v) for v in vals])
            except (TypeError, ValueError):
                continue
    else:
        import re
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                line = line.strip()
                if ";" in line or "\t" in line:
                    parts = [p.replace(",", ".") for p in re.split(r"[;\t]+", line) if p.strip()]
                else:
                    parts = [p for p in re.split(r"[,\s]+", line) if p]
                try:
                    rows.append([float(p) for p in parts])
                except ValueError:
                    continue
    rows = [r for r in rows if r]
    if not rows:
        raise ValueError("Plik nie zawiera danych liczbowych.")
    k = min(len(r) for r in rows)
    return np.array([r[:k] for r in rows], dtype=float)


if __name__ == "__main__":
    App().mainloop()
