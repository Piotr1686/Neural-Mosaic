# last_session.md

**Sesja:** 2026-07-16/17 · 22:00-00:57
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 2aaf567 @ main (zsynchronizowane z origin/main)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Sprint E3, krok 1: zróżnicować `stagger_tri` geometrycznie i wdrożyć jako `_gen_stagger_tri` w `src/engine_smart.py`.**

Konkretnie:
1. `gen_stagger_tri` (`src/tools/gen_extra_shape_schemes.py:239`) rysuje `(bl,br,tp)` + `(br,tp,tr)` na regularnej kracie — to **dokładnie** silnikowy tryb `triangle`; jego `on = (ci & rj) == 0` wybiera TYLKO paletę. **Nie przenosić tej geometrii 1:1** — powstałby duplikat.
2. Wdrożyć **realne przesunięcie rzędów o pół trójkąta** (decyzja usera 2026-07-17): co drugi rząd `+s/2`. T-junctions na poziomych granicach rzędów są legalne w partycji (precedens: `sierpinski`).
3. Wpis w `SHAPE_MODES` (aa=4, bez seeda — czysta konstrukcja).
4. **BRAMKA (obowiązkowa):** test porównujący WSPÓŁRZĘDNE z `triangle` musi wykazać różnicę — wzorzec gotowy: `test_bloom_geometry_differs_from_phyllotaxis` w `tests/test_grout_engine.py`. Statystyki pól NIE wystarczą (trójkąty są tej samej wielkości).
5. Potem `braid` (`:783`) i `moire` (`:740`) — oba oczyszczone audytem, przenosić wprost.
6. Domknięcie sprintu: goldeny ×2 border_mode w 2 procesach · test pokrycia rasteryzacją ≥4 kadry · regeneracja schematów Z SILNIKA (wzorzec: `src/tools/gen_e2_schemes.py`) · `pytest` · commit + push.

Kontekst: `PLAN_SHAPES_EXTRA.md` jest kanoniczny i ZATWIERDZONY; E1 (`b3e725c`) i E2 (`3990cfa`) zamknięte, rejestr=42, zostaje 14 kształtów. `stagger_tri` to jedyny element E3 wymagający decyzji projektowej — `braid` i `moire` są gotowe do przeniesienia, więc kolejność „najpierw stagger_tri" zdejmuje ryzyko z całego sprintu.

---

## Co zrobiono w tej sesji

- ✓ **Krok 5 (b++) → PLAN POINCARE UKOŃCZONY.** Drabinka 4:1 (`PeakRAMSampler` z `tests/benchmark.py`): 20 Mpx → 1,44 GB · 81 Mpx → 1,96 GB · **324 Mpx (36000×9000) → 4,02 GB / 80 422 kom. / 15,2 min**. **Model RAM `delta ≈ 1,27 GB stałe + 0,0085 GB/Mpx`, LINIOWY** (przewidział 4,03 vs 4,02). Zero członu superliniowego ⇒ tiling nie ma patologii do naprawy. Bramka 3,9 GB przekroczona o 3,1% — **decyzja usera: zaakceptować + raportować własną liczbę** (inwariant opisuje 16K, panorama to inny artefakt: 2,45× pikseli za 1,03× RAM). Eksport DZI = osobny etap: 2,37 GB / 1,9 min / 101,5 MB kafelków (szacunek 1,3 GB był o 80% za niski).
- ✓ **fix(dzi) `494333f` — REALNY BUG:** `make_dzi` gubił `Image.MAX_IMAGE_PIXELS = None`. Progi Pillow: ostrzeżenie 89,5 Mpx, **twardy błąd 179 Mpx**. 16K (133 Mpx) = warning ⇒ działało po cichu od 2026-06-27; panorama (324 Mpx) ⇒ **CLI `dzi` i przycisk GUI wywalały się `DecompressionBombError`**. META-LEKCJA: skrypt pomiarowy miał własną łatkę i MASKOWAŁ ścieżkę produkcyjną.
- ✓ **`PLAN_SHAPES_EXTRA.md` ZATWIERDZONY** (`d14b913`, odświeżony `2aaf567`): sprinty E1-E8, mapa linii, pułapki per grupa, definicja ukończenia (rejestr 56).
- ✓ **AUDYT KONSTRUKCJI puli** (`27b14a7`, decyzja usera — jednorazowo zamiast per sprint). Przyczyna systemowa: pula to SCHEMATY, gdzie różnicę niósł KOLOR. Wynik: 3 duplikaty + **6 podejrzanych OCZYSZCZONYCH** + 8 bezspornie odrębnych ⇒ realny rozmiar puli **14, nie 16**. Wynik WIĄŻĄCY — nie powtarzać per sprint.
- ✓ **`kepler_ty` USUNIĘTY** (`1e53982`): identyczne `(N, zeta, gamma)` co `penrose`. Usunięto też wpis w `SHAPES` (inaczej regeneracja przywróciłaby PNG).
- ✓ **Sprint E1 — `penrose_p2`** (`b3e725c`, rejestr=40): latawce/strzałki P2 (deflacja P3 → Robinson B→A → scalanie bliźniaków). Kontrola: latawce/strzałki **1.614 vs φ=1.618**. PUŁAPKA: scalanie porzuca niesparowane połówki, a tworzy je KAŻDA granica ⇒ sun dobrany „ledwo" dał **pasmo 42 px dziur** niewidoczne w liczbie kafli ani polach ⇒ `PRUNE_LEGS=3 > CULL_LEGS=1`.
- ✓ **Sprint E2 — `bloom` + `pebbles`** (`3990cfa`, rejestr=42): `bloom` = kąt Lucasa 99,502° (oś `power` nasycona); `pebbles` = Voronoi zmiennej gęstości (rozrzut pól 0,74-0,84 vs voronoi 0,49-0,70). Trzy pułapki zasiewania: stała suma przepełnia kadr · partia 4096 daje **stałe 425 kafli w każdej rozdzielczości** · ucięcie zagładza margines → **5,3% dziur**.
- ✓ **Korekty nieaktualnych zapisów:** „moire ≡ square" NIEAKTUALNE; `braid` = odrębny basketweave. Obie moje hipotezy „duplikatów do wycięcia" okazały się FAŁSZYWE — uratowało sprawdzenie PNG zamiast zaufania notatce.
- ✓ **398 testów** (z 377 na starcie): +10 E1, +8 E2, +1 DZI, +2 goldeny. Schematy regenerowane Z SILNIKA: `gen_penrose_p2_scheme.py`, `gen_e2_schemes.py` (oba commitowane).

## Co zostało (backlog sesji)

- ⟳ **E3:** `stagger_tri` (wymaga zróżnicowania) + `braid` + `moire` (NASTĘPNY KROK).
- ⟳ **E4-E7:** `dragon`/`koch_island`/`koch_snowflake` · `gereh`/`rosette` · `scales`/`nautilus`/`rosette_fractal` · `sierpinski` ×3. **E8:** docs + montaż 56 + selekcja finalna usera → galeria 16K.
- ⟳ **Hero panorama:** wyeksportowana lokalnie (`output/hero_pano_dzi/`, gitignored), NIE opublikowana na GitHub Pages — Wariant C wciąż odłożony (ryzyko publicznego artefaktu).
- ⟳ README: dopisać liczbę panoramy **4,0 GB @324 Mpx** jako OSOBNĄ od 3,9 GB @16K.
- ⟳ (przeniesione) PLAN_FRACTAL F1a; escher_lizard sylwetka; README `--grout`/`--grout-level`.

## Aktywne pliki

- `PLAN_SHAPES_EXTRA.md` — kanoniczny plan puli + **audyt konstrukcji** (czytać przed E3).
- `src/engine_smart.py` — `_PHI`/`_LUCAS_ANGLE`, `_p3_half_deflate`, `_gen_penrose_p2`, `_gen_pebbles`, `_gen_bloom`, `angle` w `_vogel_points`/`_graded_sunflower`. E3: dodać `_gen_stagger_tri`/`_gen_braid`/`_gen_moire`.
- `src/tools/gen_extra_shape_schemes.py` — źródło geometrii (17 SHAPES; mapa linii w planie, ODŚWIEŻONA po usunięciu `gen_kepler_ty`).
- `src/tools/gen_penrose_p2_scheme.py`, `src/tools/gen_e2_schemes.py` — WZORCE regeneracji schematu z silnika.
- `tests/test_golden_shapes.py` — goldeny (penrose_p2/bloom/pebbles ×2).
- `tests/test_grout_engine.py` — pokrycie + partycja + testy odrębności geometrycznej.

## Otwarte pytania

- ⚠ **Wada w istniejącym `voronoi`: 12,8% dziur @384×288 base_s=100** (podłoga `max(16, ...)` — 16 ziaren nie pokrywa kadru). Wykryta przy E2, zgłoszona, NIE naprawiona (poza zakresem). Naprawiać osobno?
- **Publikacja hero panoramy** na GitHub Pages (Wariant C) — nietknięte, decyzja usera.
- **`bloom` — różnica realna, ale subtelna:** kąt Lucasa daje inny układ ramion, ale oba czytają się jako „słonecznikowe Voronoi". Kandydat do odrzucenia przy selekcji finalnej.
- **Preview vs render:** nd zależy od skali px → podgląd ma grubszą siatkę niż finalny render. Zaakceptowane milcząco.
- Selekcja finalna kształtów przez usera — po wdrożeniu wszystkich (bez zmian).

## Do MEMORY.md (przeniesiono)

- **repo MEMORY.md:** wpis `[2026-07-16]` (krok 5, model RAM, decyzja o bramce, fix DZI, plan, kepler_ty, E1 + pułapka pierścienia) oraz `[2026-07-17]` (audyt konstrukcji, E2, 3 pułapki zasiewania Voronoi, meta-lekcja „statystyki nie rozstrzygną duplikatu", wada `voronoi`).
- **pamięć długoterminowa:** `project_dzi_decompression_bomb.md` (NOWY — bug + „skrypt pomiarowy ≠ produkcja") · `project_penrose_p2_pruning.md` (NOWY — niesparowane połówki przy każdej granicy; konwencja pola = base_s²) · `project_e2_voronoi_seeding.md` (NOWY — 3 pułapki zasiewania; `angle` w `_vogel_points`) · `project_poincare_bpp_plan.md` (krok 5 zamknięty) · `project_extra_15_shapes.md` (audyt wiążący, korekty).
