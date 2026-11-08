"""Generuje sprawozdanie (DOCX) z wyników eksperymentów. Uruchomienie: python3 experiments/build_report.py"""
import json
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent
RES = ROOT / "results"
FIG = RES / "figures"
S = json.loads((RES / "summary.json").read_text())
B = pd.read_csv(RES / "partB_summary.csv")
A = pd.read_csv(RES / "partA_test_sets.csv")
ENV = S["environment"]
REG = S["regression"]
MNAME = {"M1": "M1 – naiwny bez filtracji", "M1S": "M1S – bez filtracji + sortowanie wstępne",
         "M2": "M2 – naiwny z filtracją", "M2S": "M2S – z filtracją + sortowanie wstępne", "M3": "M3 – punkt idealny"}

doc = Document()
st = doc.styles["Normal"]
st.font.name = "Calibri"
st.font.size = Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2.2)
    s.top_margin = s.bottom_margin = Cm(2)

fig_no = [0]
tab_no = [0]


def p(text, bold=False, italic=False, size=None, align=None, after=6):
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.bold, run.italic = bold, italic
    if size:
        run.font.size = Pt(size)
    if align:
        para.alignment = align
    para.paragraph_format.space_after = Pt(after)
    return para


def rich(parts, style=None):
    """parts: lista (tekst, 'b'/'i'/'') """
    para = doc.add_paragraph(style=style)
    for t, f in parts:
        r = para.add_run(t)
        r.bold = "b" in f
        r.italic = "i" in f
    para.paragraph_format.space_after = Pt(6)
    return para


def bullet(text, level=0):
    para = doc.add_paragraph(style="List Bullet")
    if isinstance(text, str):
        para.add_run(text)
    else:
        for t, f in text:
            r = para.add_run(t)
            r.bold = "b" in f
            r.italic = "i" in f
    para.paragraph_format.space_after = Pt(3)
    return para


def figure(path, caption, width=16.5):
    doc.add_picture(str(path), width=Cm(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    fig_no[0] += 1
    p(f"Rys. {fig_no[0]}. {caption}", italic=True, size=9, align=WD_ALIGN_PARAGRAPH.CENTER, after=10)


def shade(cell, hex_):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_)
    tcPr.append(shd)


def table(header, rows, caption, widths=None, size=8.5, bold_rows=None):
    tab_no[0] += 1
    p(f"Tabela {tab_no[0]}. {caption}", italic=True, size=9, after=3)
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold = True
        r.font.size = Pt(size)
        shade(c, "DCE9E4")
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(v))
            r.font.size = Pt(size)
            if bold_rows and ri in bold_rows:
                r.bold = True
            if i > 0 and isinstance(v, (int, float)) or (isinstance(v, str) and v[:1].isdigit()):
                cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if widths:
        t.autofit = False
        tblPr = t._tbl.tblPr
        lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
        grid = t._tbl.tblGrid
        for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
            gc.set(qn("w:w"), str(int(w * 567)))
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def num(x, d=0):
    if d == 0:
        return f"{x:,.0f}".replace(",", " ")
    return f"{x:,.{d}f}".replace(",", " ")


def ms(m, s, d=0):
    return f"{num(m, d)} ± {num(s, d)}"


# ================================================================ strona tytułowa
p("AGH w Krakowie · Wydział EAIiIB · Automatyka i Robotyka, II stopień", size=10, align=WD_ALIGN_PARAGRAPH.CENTER)
p("Optymalizacja wielokryterialna – laboratorium", size=10, align=WD_ALIGN_PARAGRAPH.CENTER, after=30)
p("Sprawozdanie z ćwiczenia 2", bold=True, size=20, align=WD_ALIGN_PARAGRAPH.CENTER, after=4)
p("Optymalizacja wielokryterialna dyskretna – wyznaczanie zbioru punktów niezdominowanych.\n"
  "Eksperymenty obliczeniowe dla algorytmu naiwnego bez filtracji, z filtracją oraz metody punktu idealnego",
  size=12, align=WD_ALIGN_PARAGRAPH.CENTER, after=30)
p("Autor: Łukasz [nazwisko]\nGrupa: [numer grupy]\nProwadzący: dr inż. Przemysław Pukocz\nRok akademicki 2026/2027",
  size=11, align=WD_ALIGN_PARAGRAPH.CENTER, after=20)
doc.add_page_break()

# ================================================================ 1. Cel
doc.add_heading("1. Cel i zakres ćwiczenia", level=1)
p("Celem ćwiczenia była implementacja trzech algorytmów wyznaczania zbioru punktów niezdominowanych P(X) "
  "skończonego zbioru X ⊂ ℝᵏ, budowa aplikacji do przeprowadzania eksperymentów obliczeniowych oraz porównanie "
  "algorytmów pod względem liczby porównań punktów, liczby porównań współrzędnych i czasu obliczeń.")
p("Zakres wykonanych prac:")
bullet("implementacja algorytmów: (1) naiwnego bez filtracji punktów zdominowanych, (2) naiwnego z filtracją, "
       "(3) opartego o punkt idealny; algorytmy 1 i 2 dodatkowo w wariancie z sortowaniem wstępnym wg kryterium 1;")
bullet("aplikacja z graficznym interfejsem: konfiguracja kryteriów (min/max), generowanie danych z zadanym rozkładem, "
       "wczytywanie z pliku, sortowanie, wizualizacja 2D/3D/4D, animacja przebiegu algorytmu, benchmark i serie eksperymentów;")
bullet("część A: obliczenia dla zbiorów testowych (przykład z instrukcji oraz zbiór 25-punktowy);")
bullet("część B: zbiory losowe – K₁ = 50 zbiorów 100-elementowych, K₂ = 25 zbiorów 1000-elementowych, "
       "K₃ = 20 zbiorów 10000-elementowych, k ∈ {2, 3, 4, 5, 10}, rozkład jednostajny U[0,2] oraz Gaussa N(1,1) "
       "(łącznie 950 zbiorów i 4750 uruchomień algorytmów);")
bullet("część 2: zależności regresyjne udziału punktów niezdominowanych od liczby kryteriów (k₀ = 6 i k₀ = 7, po 50 zbiorów 100-elementowych).")

# ================================================================ 2. Algorytmy
doc.add_heading("2. Opis algorytmów", level=1)
p("We wszystkich algorytmach kryteria są minimalizowane (kryterium maksymalizowane jest mnożone przez −1). "
  "Punkt a dominuje punkt b (a ≤ b), gdy aᵢ ≤ bᵢ dla wszystkich i oraz a ≠ b.")
doc.add_heading("2.1. Porównanie dwóch punktów", level=2)
p("Porównanie punktów a i b przegląda kolejne współrzędne i zapamiętuje, czy wystąpiła współrzędna lepsza dla a "
  "i czy wystąpiła współrzędna lepsza dla b. Porównanie kończy się natychmiast, gdy oba zdarzenia zaszły "
  "(punkty są nieporównywalne). Jedno wywołanie to jedno porównanie punktów; każde sprawdzenie pary współrzędnych "
  "to jedno porównanie współrzędnych. Dla współrzędnych niezależnych o rozkładzie ciągłym oczekiwana liczba porównań "
  "współrzędnych w jednym porównaniu punktów wynosi 1 + Σⱼ₌₁ᵏ⁻¹ 2¹⁻ʲ = 3 − 2²⁻ᵏ (granica 3, zgodnie z analizą w instrukcji).")

doc.add_heading("2.2. Algorytm 1 – naiwny bez filtracji (M1)", level=2)
p("Dla kolejnych elementów X(i) pozostałych na liście: Y := X(i), fl := 0; Y jest porównywany z każdym dalszym "
  "elementem X(j). Gdy Y ≤ X(j), X(j) jest usuwany; gdy X(j) ≤ Y, usuwany jest Y, a X(j) staje się nowym Y (fl := 1). "
  "Po pętli wewnętrznej Y trafia do P(X); jeżeli fl = 0, Y jest usuwany z przeglądanej listy, w przeciwnym razie "
  "pozostaje na niej (bo nie został porównany z elementami leżącymi między X(i) a swoją pozycją). "
  "Złożoność pesymistyczna O(n²) porównań punktów.")
doc.add_heading("2.3. Algorytm 2 – naiwny z filtracją (M2)", level=2)
p("Pętla wewnętrzna jak w M1. Po znalezieniu punktu niezdominowanego Y jest on dodawany do P(X), usuwany z listy, "
  "a następnie z X usuwane są wszystkie elementy X(k), dla których Y ≤ X(k) (filtracja). Gdy na liście zostanie "
  "jeden element, jest on niezdominowany. Zgodnie z instrukcją (iteracja 2F) filtracja nie jest wykonywana, gdy "
  "jedyny pozostały element był już porównany z Y.")
doc.add_heading("2.4. Algorytm 3 – metoda punktu idealnego (M3)", level=2)
p("Wyznaczany jest punkt idealny x_min (minimum każdej współrzędnej w X) oraz kwadraty odległości d(j) = ‖X(j) − x_min‖². "
  "Punkty są sortowane rosnąco wg d. Kolejny nieusunięty punkt w tej kolejności jest niezdominowany "
  "(gdyby był zdominowany przez y, to d(y) < d(x), więc y byłby wcześniej). Punkt ten trafia do P(X), a z X "
  "usuwane są wszystkie punkty, które dominuje. Do sortowania użyto sortowania przez scalanie z licznikiem porównań.")
doc.add_heading("2.5. Sortowanie wstępne (M1S, M2S) i porównywalność metod", level=2)
p("W wariantach M1S i M2S zbiór jest wstępnie sortowany (sortowanie przez scalanie, stabilne) rosnąco wg kryterium 1. "
  "Porównania w fazie sortowania to porównania pojedynczych liczb (K₁). Zgodnie z odpowiedzią na pytanie 1 z instrukcji "
  "przeliczono je na hipotetyczną liczbę porównań punktów: P₁ = K₁·P₂/K₂, gdzie P₂ i K₂ to liczby porównań punktów "
  "i współrzędnych w drugiej fazie algorytmu. Raportowana łączna liczba porównań punktów to P = P₁ + P₂, "
  "a łączna liczba porównań współrzędnych K = K₁ + K₂. To samo przeliczenie zastosowano do sortowania odległości w M3.")

doc.add_heading("2.6. Weryfikacja poprawności", level=2)
p("Wszystkie warianty sprawdzono automatycznie (skrypt test_owd.py) na 10 080 losowych przypadkach (n od 1 do 300, k od 1 do 5, "
  "rozkłady jednostajny, Gaussa, wykładniczy i Poissona – ten ostatni z powtarzającymi się punktami), porównując wynik "
  "z przeglądem zupełnym. Wszystkie wyniki były zgodne. W eksperymentach części B dla każdego zbioru sprawdzano, "
  "że pięć wariantów zwraca identyczny zbiór P(X), a dla n ≤ 1000 dodatkowo zgodność z przeglądem zupełnym.")
p("Dla przykładu z instrukcji (12 punktów) liczby porównań są zgodne z tabelami w instrukcji: M1 – 21 porównań punktów "
  "(42 współrzędnych), M2 – 16 porównań (32 współrzędnych), wynik P(X) = {(3,3), (1,8), (4,1)}.")

# ================================================================ 3. Aplikacja
doc.add_heading("3. Aplikacja do eksperymentów obliczeniowych", level=1)
p("Aplikację „OWD Pareto Lab” napisano w języku Python 3: interfejs graficzny w bibliotece tkinter, wykresy w matplotlib, "
  "obliczenia w numpy (plik app.py, uruchomienie: python app.py). Algorytmy znajdują się w module owd.py; pętle algorytmów są "
  "kompilowane kompilatorem JIT numba (jeżeli pakiet jest zainstalowany, w przeciwnym razie kod działa w czystym Pythonie, wolniej). "
  "Ten sam moduł owd.py jest używany przez skrypt eksperymentów run_experiments.py, dzięki czemu wyniki w aplikacji i w sprawozdaniu "
  "pochodzą z tego samego kodu. Moduły aplikacji:")
for t in [
    ("Kryteria – ", "dodawanie, usuwanie i zmiana nazw kryteriów, wybór kierunku (min/max) niezależnie dla każdego kryterium."),
    ("Dane wejściowe – ", "generowanie zbioru o zadanej liczności z rozkładu jednostajnego, Gaussa, wykładniczego lub Poissona "
     "(parametry i ziarno generatora), zbiory testowe z instrukcji, wczytanie z pliku CSV/TXT/XLSX, sortowanie wg wybranego kryterium, podgląd tabeli danych."),
    ("Algorytm – ", "wybór jednej z trzech metod, opcja sortowania wstępnego wg wybranego kryterium, przycisk „Rozwiąż”."),
    ("Wykres – ", "wizualizacja zbioru i punktów niezdominowanych w 2D, 3D oraz 4D (czwarte kryterium kodowane kolorem), wybór osi."),
    ("Wyniki i benchmark – ", "liczby porównań P₂, K₂, K₁, P, czas; porównanie wszystkich metod na tych samych danych; zapis do CSV lub XLSX."),
    ("Animacja – ", "odtwarzanie krok po kroku przebiegu algorytmu (element aktywny Y, porównywany punkt, usunięte punkty, P(X)), zapis animacji do pliku GIF."),
    ("Seria eksperymentów – ", "automatyczne wykonanie serii (listy n, k, liczby zbiorów K, rozkład) w osobnym wątku, z paskiem postępu, tabelą średnich ± odchyleń i zapisem do CSV."),
]:
    bullet([(t[0], "b"), (t[1], "")])
figure(FIG / "app_plot4d.png", "Aplikacja – wynik metody punktu idealnego dla 150 punktów i 4 kryteriów (kryterium 2 maksymalizowane, kryterium 4 kodowane kolorem).")
figure(FIG / "app_bench.png", "Aplikacja – benchmark wszystkich metod na tym samym zbiorze danych.")
figure(FIG / "app_anim.png", "Aplikacja – animacja przebiegu algorytmu bez filtracji dla zbioru z instrukcji.")
figure(FIG / "app_series.png", "Aplikacja – seria eksperymentów na zbiorach losowych.")

# ================================================================ 4. Warunki eksperymentów
doc.add_heading("4. Warunki eksperymentów", level=1)
table(["Parametr", "Wartość"], [
    ["Procesor", f"{ENV['cpu']}, {ENV['cores']} rdzenie (obliczenia jednowątkowe)"],
    ["Pamięć RAM", f"{ENV['memGB']} GB"],
    ["Środowisko", f"Python {ENV['python']}, numpy {ENV['numpy']}, numba {ENV.get('numba_version', '-')} (kompilacja JIT), {ENV['platform']}"],
    ["Generator liczb losowych", "numpy.random.default_rng (PCG64) z ustalonym ziarnem – wyniki powtarzalne"],
    ["Rozkłady", "jednostajny U[0,2] (obowiązkowy) oraz Gaussa N(1,1) (wybrany)"],
    ["Pomiar czasu", "time.perf_counter(); dla n = 100 średnia z 20 powtórzeń, dla n = 1000 z 3 powtórzeń; czas obejmuje sortowanie i wyznaczenie P(X)"],
], "Środowisko obliczeniowe.", widths=[4.5, 12])

# ================================================================ 5. Część A
doc.add_heading("5. Wyniki – część A: zbiory testowe", level=1)
rows = []
for _, r in A.iterrows():
    if r.method == "M1-BLAD":
        continue
    rows.append([r.set.split(" (")[0], r.method, r.nP, r.pointCmp, r.coordCmp, r.sortCmp,
                 num(r.pointCmpTotal, 1), r.coordCmpTotal, f"{r.timeMs * 1000:.2f}"])
table(["Zbiór", "Metoda", "|P|", "P₂", "K₂", "K₁ (sort.)", "P = P₁+P₂", "K = K₁+K₂", "czas [µs]"], rows,
      "Wyniki dla zbiorów testowych (zestaw 1: 12 punktów z instrukcji, zestaw 2: 25 punktów, k = 2, oba kryteria minimalizowane).",
      widths=[1.8, 1.4, 1.0, 1.4, 1.4, 1.8, 2.2, 2.2, 1.8], size=8)
p("Oznaczenia metod: M1 – naiwny bez filtracji, M1S – M1 z sortowaniem wstępnym wg kryterium 1, M2 – naiwny z filtracją, M2S – M2 z sortowaniem wstępnym, M3 – punkt idealny. P₂, K₂ – porównania punktów i współrzędnych w fazie właściwej, K₁ – porównania w fazie sortowania.", size=9)
wrong = A[(A.method == "M1-BLAD")].iloc[0]
p("Przykład błędnego wyniku (zestaw 1). Jeżeli w algorytmie bez filtracji punkt Y zostanie usunięty z listy po pierwszej "
  "iteracji (mimo fl = 1) i pominie się filtrację, otrzymuje się P(X) = {(3,6), (3,3), (1,8), (4,1)}: punkt (3,6) zostaje "
  "błędnie uznany za niezdominowany, ponieważ jedynym punktem, który go dominuje, jest usunięty wcześniej punkt (3,3). "
  "Jest to dokładnie sytuacja opisana w instrukcji; moduł owd.py odtwarza ją wywołaniem run(X, 'nofilter', wrong=True).")
p("Dla tak małych zbiorów najmniej porównań wykonuje metoda z filtracją (zestaw 1) lub bez filtracji (zestaw 2), a "
  "koszt sortowania w M1S, M2S i M3 jest większy niż zysk – sortowanie opłaca się dopiero przy większej liczbie "
  "kryteriów i większych zbiorach (część B).")

# ================================================================ 6. Część B
doc.add_heading("6. Wyniki – część B: zbiory losowe", level=1)
p("Tabele 3 i 4 zawierają średnie ± odchylenia standardowe (po K zbiorach) łącznej liczby porównań punktów P, "
  "liczby porównań punktów w fazie właściwej P₂, łącznej liczby porównań współrzędnych K oraz czasu obliczeń. "
  "Pełne surowe wyniki dla każdego zbioru zawiera plik results/partB_random_raw.csv.")
for dist, dl in [("uniform", "rozkład jednostajny U[0,2]"), ("gauss", "rozkład Gaussa N(1,1)")]:
    d = B[B.dist == dist].copy()
    d["mo"] = d.method.map({m: i for i, m in enumerate(["M1", "M1S", "M2", "M2S", "M3"])})
    d = d.sort_values(["n", "k", "mo"])
    rows, bold = [], []
    for (n, k), g in d.groupby(["n", "k"], sort=False):
        best = g.pc.idxmin()
        for idx, r in g.iterrows():
            if idx == best:
                bold.append(len(rows))
            rows.append([f"{n}", f"{k}", r.method, f"{r.nP:.1f}", ms(r.pc, r.pc_sd), ms(r.pc2, r.pc2_sd), ms(r.cc, r.cc_sd),
                         ms(r.t, r.t_sd, 3)])
    table(["n", "k", "Metoda", "|P| śr.", "P (łącznie)", "P₂", "K (łącznie)", "czas [ms]"], rows,
          f"Wyniki dla zbiorów losowych – {dl} (n = 100: K = 50, n = 1000: K = 25, n = 10000: K = 20). "
          "Pogrubiono metodę z najmniejszą średnią łączną liczbą porównań punktów.",
          widths=[1.1, 0.8, 1.3, 1.1, 3.3, 3.3, 3.5, 2.5], size=7, bold_rows=bold)

figure(FIG / "B_point_cmp_uniform.png", "Łączna liczba porównań punktów P w funkcji liczby kryteriów, rozkład jednostajny (skala logarytmiczna, słupki: ± odchylenie standardowe).")
figure(FIG / "B_point_cmp_gauss.png", "Łączna liczba porównań punktów P w funkcji liczby kryteriów, rozkład Gaussa.")
figure(FIG / "B_time_uniform.png", "Czas obliczeń w funkcji liczby kryteriów, rozkład jednostajny.")
figure(FIG / "B_time_gauss.png", "Czas obliczeń w funkcji liczby kryteriów, rozkład Gaussa.")
figure(FIG / "B_coord_cmp_uniform.png", "Łączna liczba porównań współrzędnych K, rozkład jednostajny.")
figure(FIG / "B_pareto_share.png", "Udział punktów niezdominowanych |P(X)|/n w zależności od k i n.", width=15)
figure(FIG / "B_coord_per_point.png", "Średnia liczba porównań współrzędnych przypadająca na jedno porównanie punktów (M1, n = 1000) na tle wartości teoretycznej.", width=10)

rows = []
for r in S["gain_10000"]:
    rows.append(["jednostajny" if r["dist"] == "uniform" else "Gaussa", r["k"]] + [f"{r[m]:.0f}%" for m in ["M1", "M1S", "M2", "M2S", "M3"]])
table(["Rozkład", "k", "M1", "M1S", "M2", "M2S", "M3"], rows,
      "Łączna liczba porównań punktów względem metody M1 (= 100%) dla n = 10000.", widths=[2.4, 1, 2, 2, 2, 2, 2])

# ================================================================ 7. Część 2
doc.add_heading("7. Wyniki – część 2: zależności regresyjne", level=1)
p("(A) Dla 50 zbiorów 100-elementowych z k₀ = 6 kryteriami wyznaczono P(X) dla wszystkich C(6,k) kombinacji k kryteriów, "
  "k = 2, …, 6 (57 problemów na zbiór, 2850 obserwacji na rozkład) i zbadano zależność ilorazu |P(X)|/|X| od k. "
  "(B) Dla 50 zbiorów 100-elementowych z k₀ = 7 kryteriami wyznaczono iloraz |P_k(X)|/|P_k₀(X)| dla wszystkich "
  "kombinacji k < 7 kryteriów (126 problemów na zbiór, 6300 obserwacji na rozkład) w funkcji różnicy k₀ − k. "
  "Do wyznaczania P(X) użyto metody punktu idealnego.")
rows = []
for dist, dl in [("uniform", "jednostajny"), ("gauss", "Gaussa")]:
    r = REG[f"2A_{dist}"]
    rows.append([f"(A) {dl}", "liniowy: y = a + b·k", f"a = {r['lin_a']:.4f}, b = {r['lin_b']:.4f} (SE {r['lin_se']:.4f})", f"{r['lin_r2']:.3f}", "p < 10⁻¹⁰⁰"])
    rows.append([f"(A) {dl}", "logistyczny: y = 1/(1+e^−(a+b·k))", f"a = {r['log_a']:.3f}, b = {r['log_b']:.3f}", f"{r['log_r2']:.3f}", "–"])
for dist, dl in [("uniform", "jednostajny"), ("gauss", "Gaussa")]:
    r = REG[f"2B_{dist}"]
    rows.append([f"(B) {dl}", "liniowy: y = a + b·(k₀−k)", f"a = {r['lin_a']:.4f}, b = {r['lin_b']:.4f} (SE {r['lin_se']:.4f})", f"{r['lin_r2']:.3f}", "p < 10⁻¹⁰⁰"])
    rows.append([f"(B) {dl}", "wykładniczy: y = e^(−c·(k₀−k))", f"c = {r['exp_c']:.4f}", f"{r['exp_r2']:.3f}", "–"])
table(["Zadanie / rozkład", "Model", "Współczynniki", "R²", "istotność b"], rows, "Wyniki regresji.",
      widths=[3, 4.8, 5.6, 1.2, 2], size=8)
rows = []
for dist, dl in [("uniform", "jednostajny"), ("gauss", "Gaussa")]:
    for m in REG[f"2A_{dist}"]["means"]:
        rows.append([dl, int(m["k"]), f"{m['mean']:.3f} ± {m['std']:.3f}", int(m["count"])])
table(["Rozkład", "k", "|P|/|X| (średnia ± odch.)", "liczba obserwacji"], rows, "Część 2A – średni udział punktów niezdominowanych w zależności od k (k₀ = 6, n = 100).", widths=[3, 1.2, 4.5, 3])
figure(FIG / "R2A_ratio_vs_k.png", "Część 2A – udział punktów niezdominowanych w zbiorze 100 punktów w zależności od liczby kryteriów; regresja liniowa i logistyczna.")
rows = []
for dist, dl in [("uniform", "jednostajny"), ("gauss", "Gaussa")]:
    for m in REG[f"2B_{dist}"]["means"]:
        rows.append([dl, int(m["diff"]), f"{m['mean']:.3f} ± {m['std']:.3f}", int(m["count"])])
table(["Rozkład", "k₀ − k", "|P_k|/|P_k₀| (średnia ± odch.)", "liczba obserwacji"], rows, "Część 2B – iloraz liczby punktów niezdominowanych dla k i k₀ = 7 kryteriów.", widths=[3, 1.2, 4.5, 3])
figure(FIG / "R2B_ratio_vs_diff.png", "Część 2B – iloraz |P_k(X)|/|P_k₀(X)| w funkcji różnicy liczby kryteriów k₀ − k (k₀ = 7).")

# ================================================================ 8. Wnioski
g = {(r["dist"], r["k"]): r for r in S["gain_10000"]}
bu = B[(B.dist == "uniform")]


def val(n, k, m, col="pc", dist="uniform"):
    return float(B[(B.dist == dist) & (B.n == n) & (B.k == k) & (B.method == m)][col].iloc[0])


doc.add_heading("8. Wnioski", level=1)
concl = [
    ("Poprawność. ", "Wszystkie trzy algorytmy (oraz warianty z sortowaniem wstępnym) zwracały identyczne zbiory P(X), zgodne "
     "z przeglądem zupełnym. Usunięcie punktu Y bez filtracji w algorytmie naiwnym prowadzi do błędnego wyniku – "
     "flaga fl (algorytm 1) albo filtracja (algorytm 2) są niezbędne."),
    ("Liczba punktów niezdominowanych rośnie gwałtownie z liczbą kryteriów. ",
     f"Dla k = 2 średnio |P| ≈ {val(100,2,'M1','nP'):.1f}, {val(1000,2,'M1','nP'):.1f} i {val(10000,2,'M1','nP'):.1f} dla n = 100, 1000, 10000, "
     "co odpowiada teoretycznej wartości oczekiwanej Hₙ = 1 + 1/2 + … + 1/n ≈ ln n + 0,577 (5,19; 7,49; 9,79). "
     f"Dla k = 10 niezdominowanych jest ok. {val(100,10,'M1','nP'):.0f}% punktów przy n = 100 i ok. {val(10000,10,'M1','nP')/100:.0f}% przy n = 10000. "
     "Ponieważ koszt wszystkich metod jest proporcjonalny w przybliżeniu do n·|P(X)|, liczba kryteriów jest głównym czynnikiem decydującym o czasie obliczeń."),
    ("Metoda punktu idealnego (M3) jest najlepsza dla k ≥ 5, a dla k = 4 przy n ≤ 1000. ",
     f"Dla n = 10000 wykonuje ona {g[('uniform',4)]['M3']:.0f}%, {g[('uniform',5)]['M3']:.0f}% i {g[('uniform',10)]['M3']:.0f}% "
     f"porównań metody M1 dla k = 4, 5, 10 (rozkład jednostajny; dla k = 4 i n = 10000 nieco mniej porównań wykonuje M2 – {g[('uniform',4)]['M2']:.0f}%). Dla n = 10000 i k ≥ 5 jest też najszybsza (np. k = 10: {val(10000,10,'M3','t'):.0f} ms wobec "
     f"{val(10000,10,'M1','t'):.0f} ms dla M1 i {val(10000,10,'M2','t'):.0f} ms dla M2); dla małych zbiorów czasy są rzędu setnych części milisekundy i decyduje o nich stały narzut (wywołania numpy, obliczenie odległości), więc tam najszybsze są metody naiwne. Kolejność wg odległości od punktu idealnego "
     "gwarantuje, że każdy rozpatrywany punkt jest od razu niezdominowany, więc nie ma porównań „zmarnowanych” na punkty, które później zostaną usunięte, "
     "a punkty bliskie punktu idealnego dominują dużą część zbioru i usuwają ją wcześnie."),
    ("Dla małej liczby kryteriów (k = 2, 3) najlepsze są metody naiwne bez sortowania (zwłaszcza M2). ",
     f"Liczba porównań punktów w M1 i M2 dla k = 2 wynosi tylko ok. 1,1·n (np. {val(10000,2,'M2'):.0f} dla n = 10000), "
     "ponieważ element aktywny Y szybko „wspina się” do punktu, który dominuje prawie cały zbiór. Koszt sortowania "
     "(ok. n·log₂n porównań liczb) jest wtedy wielokrotnie większy od kosztu właściwej fazy, dlatego M3 wykonuje dla k = 2 "
     f"ok. {g[('uniform',2)]['M3']/100:.1f} razy więcej porównań niż M1, choć w samej fazie właściwej (P₂) jest najoszczędniejsza."),
    ("Filtracja (M2) pomaga, gdy punktów niezdominowanych jest mało, a szkodzi, gdy jest ich dużo. ",
     f"Dla k = 3–5 i n = 10000 M2 wykonuje {min(g[('uniform',kk)]['M2'] for kk in (3,4,5)):.0f}–{max(g[('uniform',kk)]['M2'] for kk in (3,4,5)):.0f}% porównań M1, natomiast dla k = 10 aż "
     f"{g[('uniform',10)]['M2']:.0f}%: przy |P| ≈ 0,5·n filtracja prawie niczego nie usuwa, a powtarza porównania z elementami, które były już porównane z Y w pętli wewnętrznej. "
     "Ograniczenie filtracji do elementów leżących przed pozycją ostatecznego Y usunęłoby tę nadmiarowość."),
    ("Sortowanie wstępne wg jednego kryterium nie poprawia znacząco metod naiwnych. ",
     f"M1S jest wyraźnie lepszy od M1 tylko dla dużej liczby kryteriów (k = 10: {g[('uniform',10)]['M1S']:.0f}% porównań M1; dla k = 4–5 wynik zależy od n, a dla k ≤ 3 sortowanie się nie opłaca), a M2S jest najgorszy we wszystkich przypadkach "
     "losowych. Punkt minimalny wg kryterium 1 jest wprawdzie niezdominowany, ale przy k ≥ 3 zwykle słabo wypada w pozostałych kryteriach i dominuje mało punktów, "
     "więc nie redukuje zbioru tak skutecznie jak „wspinający się” element aktywny w kolejności losowej. Sortowanie wg odległości od punktu idealnego (M3) uwzględnia "
     "wszystkie kryteria jednocześnie i dlatego jest skuteczne."),
    ("Liczba porównań współrzędnych jest proporcjonalna do liczby porównań punktów. ",
     "Średnia liczba porównań współrzędnych na jedno porównanie punktów wynosi 2,0 dla k = 2 i rośnie do ok. 2,9–3,0 dla k = 10, "
     "zgodnie z wartością teoretyczną 3 − 2²⁻ᵏ dla losowej pary. Dzięki wczesnemu przerywaniu porównania koszt porównania punktów praktycznie nie zależy od k, "
     "a liczba porównań punktów jest dobrą miarą do porównywania algorytmów; czas obliczeń jest z nią silnie skorelowany."),
    ("Rozkład danych (jednostajny vs Gaussa) praktycznie nie wpływa na wyniki. ",
     "Różnice mieszczą się w granicach rozrzutu losowego. Wynika to z faktu, że relacja dominacji zależy tylko od uporządkowania wartości "
     "w każdej współrzędnej, a dla niezależnych współrzędnych o tym samym rozkładzie ciągłym rozkład tych uporządkowań jest taki sam niezależnie od rozkładu. "
     "Inaczej byłoby dla rozkładów dyskretnych (np. Poissona), gdzie pojawiają się równe współrzędne i punkty."),
    ("Zależność udziału punktów niezdominowanych od liczby kryteriów jest nieliniowa. ",
     f"W części 2A regresja logistyczna (R² = {REG['2A_uniform']['log_r2']:.3f}) opisuje dane lepiej niż liniowa (R² = {REG['2A_uniform']['lin_r2']:.3f}); "
     "model liniowy daje ujemny udział dla k = 1 i udział powyżej 100% dla dużych k, czego model logistyczny nie robi – potwierdza to uwagę z instrukcji, "
     f"że prawidłowym modelem jest regresja logistyczna. W części 2B każde usunięte kryterium zmniejsza liczbę punktów niezdominowanych średnio o ok. "
     f"{-REG['2B_uniform']['lin_b']*100:.0f} punktów procentowych liczby |P_k₀| (R² = {REG['2B_uniform']['lin_r2']:.3f}); dla k₀ − k = 1 zostaje ok. 82% punktów, "
     "a dla k = 1 – jeden punkt."),
    ("Rekomendacja. ", "Dla k ≤ 3 należy stosować algorytm naiwny (najlepiej z filtracją) bez sortowania; dla k ≥ 4 – metodę punktu idealnego, "
     "której przewaga rośnie wraz z liczbą kryteriów i licznością zbioru."),
]
import re
for i, (h, t) in enumerate(concl, 1):
    t = re.sub(r'(\d)\.(\d)', r'\1,\2', t)
    para = doc.add_paragraph(style="List Number")
    r = para.add_run(h)
    r.bold = True
    para.add_run(t)
    para.paragraph_format.space_after = Pt(4)

doc.add_heading("Załączniki", level=1)
for a_, b_ in [("app.py", "aplikacja z interfejsem graficznym (python app.py)"),
               ("owd.py", "moduł z algorytmami"),
               ("test_owd.py", "testy poprawności (python test_owd.py)"),
               ("run_experiments.py", "pełna seria eksperymentów (python run_experiments.py)"),
               ("analyze.py, build_report.py", "opracowanie wyników (tabele, wykresy, regresje) i generowanie sprawozdania"),
               ("results/*.csv", "surowe i zagregowane wyniki eksperymentów"),
               ("results/figures/*.png", "wykresy i zrzuty ekranu aplikacji")]:
    bullet([(a_ + " – ", "b"), (b_, "")])

out = ROOT / "Sprawozdanie_Cw2_OWD.docx"
doc.save(out)
print("zapisano", out)
