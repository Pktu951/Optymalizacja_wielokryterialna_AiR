# Ćw. 2 – OWD: punkty niezdominowane (Python)

## Instalacja (raz)
1. Zainstaluj Python 3.11–3.13 z https://www.python.org/downloads/ (przy instalacji zaznacz **Add python.exe to PATH**).
2. Otwórz terminal w tym folderze (Eksplorator → prawy przycisk na folder → „Otwórz w terminalu”) i wpisz:
   ```
   pip install -r requirements.txt
   ```

## Uruchamianie
| Co | Polecenie |
|---|---|
| Aplikacja z GUI | `python app.py` |
| Testy poprawności algorytmów | `python test_owd.py` |
| Pełne eksperymenty (ok. 3 min) | `python run_experiments.py` |
| Szybka wersja eksperymentów | `python run_experiments.py --quick` |
| Tabele, wykresy, regresje | `python analyze.py` |
| Sprawozdanie DOCX od nowa | `python build_report.py` |

`numba` przyspiesza obliczenia ok. 100×. Bez niej wszystko działa, ale pełne eksperymenty trwałyby kilka godzin.

## Pliki
- `owd.py` – algorytmy: naiwny bez filtracji, naiwny z filtracją, punkt idealny (+ sortowanie wstępne), liczniki porównań.
- `app.py` – aplikacja (tkinter + matplotlib): kryteria min/max, generowanie/wczytywanie danych, sortowanie, wykres 2D/3D/4D, benchmark, animacja (zapis GIF), serie eksperymentów, zapis CSV/XLSX.
- `run_experiments.py` – eksperymenty części A, B i 2 → `results/*.csv`.
- `analyze.py` – `results/partB_summary.csv`, `results/summary.json`, wykresy w `results/figures/`.
- `build_report.py` – `Sprawozdanie_Cw2_OWD.docx`.
