# PLAN PRAC — A1 (peak-RAM) + A2 (eksport DZI)

> Utworzono: 2026-06-27. Źródło decyzji architektonicznych: [[project_a1_memory_arch]], [[project_a2_dzi_export_arch]].
> Zasada kolejności: **najpierw odblokuj/udowodnij → największa wartość → największe ryzyko na końcu.**
> Praca sekwencyjna (solo-dev, jeden kontekst), każdy krok = osobny commit (conventional commits).

## Kolejność wykonania

| # | Krok | Pliki | Ryzyko | Model | Status |
|---|------|-------|--------|-------|--------|
| 1 | **A1-Wariant 0** — wątek samplujący peak-RAM (~50 ms) wokół renderu; zastępuje niewiarygodny `rss_after − rss_before` | `tests/benchmark.py` (`:108`, `:133`, `:167`, `:205`) | zero | Opus/Sonnet | ✓ DONE (2026-06-27) |
| 2 | **A1-A-tani** — w pętli matchingu cdist float64 → squared-euclid float32 (GEMM); chunk adaptacyjny ≤256 MB. 3.6 GB → ~0.25 GB, ranking top-k bez zmian | `src/engine_smart.py` (`:658-668`) | niskie | `/sonnet` | ✓ DONE (2026-06-27) |
| 3 | **A2 całość** — przycisk „Export Deep Zoom…" (wzorzec `run_photo`) + skip-if-exists + podkomenda CLI `dzi`; reuse gotowego `make_dzi.py` | `src/gui.py` (`:991-1006`), `src/cli.py`, `src/tools/make_dzi.py` | niskie | Opus | ✓ DONE (2026-06-27) |
| 4 | **A1-B** — leniwe maski spectre/kite (`padded_poly`+bbox, rasteryzacja przy kompozycie); wymaga testu regresji pikselowej w CI | `src/engine_smart.py` (`:303`, `:729`) | **wysokie** | HIGH | ☐ |

**Uzasadnienie kolejności:** A2 (krok 3) wskakuje przed ryzykownym A1-B (krok 4) — więcej wartości portfolio przy mniejszym ryzyku. A1-Wariant 0 (krok 1) jest warunkiem wstępnym: bez wiarygodnego pomiaru nie udowodnimy efektu A-tani.

## Zadania poboczne (housekeeping)

- ☐ **README ↔ kod (1 commit)**: dodać `--res 2K` dla typo do tabeli (silnik wspiera, zwalidowane); workflow wymienia 2 z 6 katalogów → uzupełnić. **Decyzja: dokumentować, NIE blokować 2K.**
- ☐ **test_processor**: twarda asercja CUDA → `skipif(not cuda)`, by wrócił do CI. NISKI.
- ☐ **Demo polish** (na koniec, opcjonalne): zróżnicować źródła live-demo (triangle/photo = ta sama osoba); więcej mozaik 8K. NISKI, czysto kosmetyczne.

## Świadomie odłożone (over-engineering dla solo-portfolio)
Wariant C w A1 (pasmowe renderowanie kanwy — łamie kontrakt `_do_render → PIL`), Wariant C w A2 (publish-to-viewer, dotyka `docs/` Pages), CoC/SECURITY.md/CITATION.cff/Docker/plugin system.

## Protokół
Po każdym kroku: weryfikacja → propozycja commitu → pytanie „kontynuować?". Aktualizuj kolumnę Status.
