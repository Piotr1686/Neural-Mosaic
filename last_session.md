# last_session.md

**Sesja:** 2026-06-24 · 22:10-23:21
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 68819bc @ main (origin zsynchronizowany)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Zwaliduj kurowany `requirements.txt` w CZYSTYM środowisku (definitywny dowód na must-fix #1):**
1. `C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m venv C:/Users/plazo/AppData/Local/Temp/nm_clean` (lub conda env tymczasowy z Python 3.10).
2. Aktywuj i `pip install -r requirements.txt` — sprawdź, że instalacja przechodzi bez torch/transformers i bez błędów buildu poza Windows-only pakietami.
3. `python -c "import src.gui"` → musi przejść bez `ModuleNotFoundError: matplotlib` (import top-level w `gui.py:29-30`).
4. `python -m src.cli render input/portrait.jpg --engine typo --res 4K` → potwierdź, że `fonttools` jest obecny i indekser/engine działają.

Kontekst: w tej sesji `requirements.txt` przepisano z surowego `pip freeze` na kurowaną listę (commit `68819bc`), ale poprawność zweryfikowano dotąd TYLKO analizą pokrycia importów (`grep` w `src/`), nie czystą instalacją. Czysty venv to ostateczny dowód, że obietnica „4 linie i działa" z README jest prawdziwa. Inwariant w [[project_requirements_curated]].

---

## Co zrobiono w tej sesji (2026-06-24)

- ✓ **Weryfikacja live-demo (end-to-end, na żywo)**: wszystkie 5 DZI `Format="jpg"`, piramida 0–13, wymiary zgodne z etykietami; GitHub Pages odpowiada; kafelki `13/0_0.jpg` to prawidłowe JPEG-i; motywy potwierdzone wizualnie (**hexagon=skok/niebo, spectre=papuga/safari**). Zero czarnego ekranu dla świeżego użytkownika.
- ✓ **Wariant typo `white_on_black` do galerii README** (commit `2875f99`, pushed): 2 mastery 8K z `IMG_20220727` (Latin monospace, BoW+WoB); reprodukowalny krok `build_mode_compare()` w `make_matrices.py` → `assets/examples/typo_mode_compare.jpg` (1562×644); podsekcja README „Symbol Mosaic — two style modes".
- ✓ **Debata adwersarialna nad README** (2 subagenci Krytyk vs Obrońca, 2 rundy z krzyżowym przesłuchaniem, konsensus) → pakiet poprawek (commit `68819bc`, pushed):
  - **requirements.txt** przepisany z surowego `pip freeze` na kurowany: dodano brakujące `matplotlib` (gui.py nie wstawało!) + `fonttools`; torch/transformers → opcjonalny zakomentowany blok.
  - sprostowanie **75/79-dim** (indeks zawsze 79-dim; `--edge-aware` przełącza tylko użycie cech, nie buduje indeksu) — 3 miejsca w README.
  - ujednolicenie **„6 vs 7 grup fontów"**; rozmiar repo ~100→~250 MB; kolumna kodów CLI w tabeli grup.
- ✓ Wszystkie 3 commity treści wypchnięte na origin; commit sesyjny `cc9f991` (zaległy z 06-21) też dopchnięty.

## Co zostało (backlog sesji)

- ⟳ **Walidacja requirements.txt w czystym venv** (patrz NASTĘPNY KROK) — najważniejsze
- ⟳ Live demo: `photo`(portrait.jpg) vs `triangle`(portrait2.jpg) = ta sama osoba — ewentualne zróżnicowanie (NISKI priorytet)
- ⟳ Świadomie odrzucone w debacie (over-engineering dla portfolio solo): krok conda/venv per-OS w README, dodatkowe badge'e, CoC, cross-platformowość/Docker/LFS, walidacja `--scale`, caveat 16:9 print-guide, alt-text w `<details>`, martwe assety, rozbicie węzła Mermaid
- ⟳ `benchmark.py`: pomiar peak-RAM niewiarygodny (psutil delta vs realne ~10 GB) — ewentualny sampling-thread
- ⟳ Drobne z rundy 1 Krytyka (do decyzji): typo realnie wspiera `--res 2K` (README mówi tylko 4K/8K/16K); workflow l.370 wymienia 2 z 6 skanowanych katalogów

## Aktywne pliki

- `requirements.txt` (kurowany — NIE pip freeze; [[project_requirements_curated]])
- `README.md` (sprostowania faktów: 79-dim, 6/7 grup, rozmiar repo, kody CLI grup; podsekcja two style modes)
- `src/tools/make_matrices.py` (krok `build_mode_compare`), `assets/examples/typo_mode_compare.jpg`
- `docs/index.html`, `docs/tiles/spectre_parrot.*`, `docs/tiles/hexagon_jump_16K.*` (live demo — zweryfikowane)
- Mastery w `output/github_readme/` (gitignored): `typo_mode_bow_8K.png`, `typo_mode_wob_8K.png`

## Otwarte pytania

- Czy zróżnicować pozostałe źródła live-demo (triangle/photo = ta sama osoba)? (rekomendacja: niski priorytet)
- Czy udokumentować/zablokować `--res 2K` dla typo (silnik to wspiera, README nie)?

## Do MEMORY.md (przeniesiono)

- [[project_requirements_curated]] — requirements.txt jest KUROWANY (nie pip freeze); musi mieć matplotlib + fonttools; torch/transformers opcjonalne (uśpiony ai_core); cv2 nieimportowane (2026-06-24)
