# last_session.md

**Sesja:** 2026-06-27 · 20:30-21:40
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** c9f6101 @ main (UWAGA: branch ahead of origin o 1 commit — `c9f6101` plan portfolio niewypchnięty; README `e6766b5` już na origin)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Krok 1 z `PLAN_PORTFOLIO.md` — Live zoomable gallery jako HERO README.** Wygeneruj 1–2 prawdziwe mozaiki **16K** → DZI (gotowy `make_dzi` / przycisk GUI „Export Deep Zoom"), wrzuć do hostowanego viewera OpenSeadragon na GitHub Pages (dziś tylko „a handful of 8K", README l. 560), i dodaj na samej górze README (EN+PL) wielki link „🔍 Open the live zoomable gallery". Reuse `assets/examples/mosaic_zoom.gif`.

Kontekst: po domknięciu A1+A2 faza skupia się na PREZENTACJI/WIDOCZNOŚCI, nie kodzie ([[project_portfolio_phase]]). Krok 1 ma najwyższy ROI — infrastruktura DZI+Pages już istnieje i jest najbardziej niedoeksploatowana; daje efekt „wow" bez instalacji u odbiorcy. Krok 2 (GitHub social preview) łączy się naturalnie z tą samą pracą wizualną.

---

## Co zrobiono w tej sesji

- ✓ **Pomiar empiryczny peak-RAM 16K** — pełny `python -m tests.benchmark` (i5-12500H/16 wątków, CPU-only, indeks 454857). Peak RAM całego runu **3.90 GB** (vs ~10 GB analitycznie); per-op RAM+: 4K 1344 MB, 8K 1619 MB, 16K/kite 3212 MB, typo 255 MB. Bonus: render 3–5× szybszy (16K 21→5.9 min) — GEMM float32 wyparł cdist. Log: `logs/benchmark_16k_20260627.log`.
- ✓ **README EN+PL zaktualizowane** (`e6766b5`, wypchnięte) — tabela Performance (nowe czasy), nota Memory (~4 GB + „z ~10 GB"), Known Limitations, FAQ. Zweryfikowano brak zbłąkanego „~10 GB" (zostały tylko celowe „przed/po").
- ✓ **Push origin** — `4f01318..e6766b5`; objął też zaległy commit sesyjny `6c0ee46`. Origin był zsynchronizowany do tego momentu.
- ✓ **MEMORY zaktualizowane** — [[project_a1_memory_arch]] (pomiar 16K potwierdzony) + nowy wpis [[project_portfolio_phase]].
- ✓ **Prompt dla DriftScope** — gotowy do skopiowania prompt na dwujęzyczne README (EN źródłowe + PL), wzorzec przełącznika języka + zasady (badge CI tylko gdy workflow; polskie kotwice z diakrytykami). Tylko dostarczony userowi, nic w repo.
- ✓ **`PLAN_PORTFOLIO.md`** (`c9f6101`) — plan fazy portfolio, 6 zadań po ROI; decyzja: adwersarialni agenci ODRZUCENI dla appki desktop CPU-only.

## Co zostało (backlog sesji)

- ⟳ **PLAN_PORTFOLIO.md kroki 2–6:** GitHub social preview (1280×640) · sekcja Performance Engineering · post „aperiodic monotile mosaic" · zero-friction install (PyInstaller) · adwersarialny audyt twierdzeń README przed publikacją.
- ⟳ Świadomie ODŁOŻONE: Wariant C (A1 pasmowa kanwa / A2 publish-to-viewer), kolejne ML/CLIP, Docker/plugin system. test_dzi (follow-up z A2).

## Aktywne pliki

- `PLAN_PORTFOLIO.md` (nowy plan — krok 1 do startu), `PLAN_PRAC.md` (A1+A2 — wszystko ✓)
- `README.md` + `README.pl.md` (Performance/Memory zaktualizowane)
- `tests/benchmark.py` (`PeakRAMSampler` — użyty do pomiaru), `logs/benchmark_16k_20260627.log`
- Do kroku 1: `src/tools/make_dzi.py`, `src/gui.py` (przycisk DZI), `docs/` (GitHub Pages viewer), `assets/examples/` (16K + zoom assety)

## Otwarte pytania

- Krok 1: ile mozaik 16K do galerii i jakie źródła? (limit storage GitHub Pages — README l. 560 wspomina o „lightweight").
- Social preview: kompozycja w CC czy layout na Claude.ai (web)?
- `c9f6101` (plan) niewypchnięty — wypchnąć na starcie kolejnej sesji czy zostawić.

## Do MEMORY.md (przeniesiono/zaktualizowano w tej sesji)

- [[project_a1_memory_arch]] — dodano blok „POMIAR EMPIRYCZNY 16K POTWIERDZONY 2026-06-27" (peak 3.9 GB vs ~10 GB, README `e6766b5`); domyka jedyną otwartą pozycję A1.
- [[project_portfolio_phase]] — NOWY: faza portfolio, wow = prezentacja nie kod, adwersarialni agenci odrzuceni, lewary ROI, link do `PLAN_PORTFOLIO.md`.
