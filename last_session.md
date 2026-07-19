# last_session.md

**Sesja:** 2026-07-19 · dzień-wieczór (~21:00)
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 667bcf7 @ main (zsynchronizowane z origin/main)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Sprint E6, krok 1: wdrożyć `scales` jako `_gen_scales` w `src/engine_smart.py`** (geometria źródłowa: `gen_scales:847` w `src/tools/gen_extra_shape_schemes.py`).

Konkretnie:
1. `scales` = rybia łuska: okręgi promienia r na siatce szachownicowej (`dx=2r, dy=r`, offset r); komórka = kopuła półkolista + 2 wklęsłe łuki zbiegające w dolny wierzchołek; przecięcia okręgów DOKŁADNIE w `(0,−r)` i `(±r,0)`. PRZENIEŚĆ geometrię wprost.
2. ⚠ **ŁUKI**: krok polygonizacji **MUSI** być `_arc_pitch(r, tol=0.35)` — NIE `seg = base_s/3` (ta pomyłka sfasetowała truchet_hex; promień łuski ~base_s, stały w px przy każdej rozdzielczości).
3. ⚠ **Instrument pokrycia wg drabinki** (MEMORY [2026-07-19]): krzywe szwy — jeśli łuki współdzielone konstrukcyjnie (ta sama polilinia z obu stron, wzorzec `_sun_arc` / puzzle) → formalny test partycji + pokrycie FLOAT ss=4 (próg 0,45; kalibracja voderberg 0,502); raster binarny 1:1 SKŁAMIE.
4. ⚠ Dedup KOLEJNYCH duplikatów wierzchołków na złączeniach łuków (parzystość scanline'a Pillow — pasy 1-2 px).
5. Domknięcie: wpis w `SHAPE_MODES` (aa=4) · goldeny ×2 border_mode w 2 procesach (jeden `PYTHONHASHSEED=1`) · schemat Z SILNIKA (nowy `gen_e6_schemes.py`, wzorzec `gen_e5_schemes.py`) · pełny `pytest`.
6. Potem `nautilus` (`gen_nautilus:688`; biegun POZA kadrem `(-1.55,-1.30)` — wzorzec „dobrego środka") i `rosette_fractal` (`:935`; sektory ×2 co `m=3` pierścienie, `g=2^(1/m)`; wspólne krawędzie próbkowane identycznie z obu stron) — domykają E6.

Kontekst: E1–E5 + rodzina puzzle ZAMKNIĘTE (rejestr=53, cel 59). Zostało 6 kształtów: E6 (`scales`/`nautilus`/`rosette_fractal`) + E7 (`sierpinski` ×3). User dał standing approval „rób pozostałe" — po E6 przejść do E7, potem E8 (docs + montaż + selekcja finalna usera).

---

## Co zrobiono w tej sesji

- ✓ **E3 domknięty**: `braid` (`def6513`, bramka izometryczna `_max_overlap` + zęby na flip parzystości) i `moire` (`3c10f0e`, ostrzeżenie „≡ square" obalone pomiarem: CV pola 0,27, 28% krawędzi osiowych). Rejestr=45.
- ✓ **Propozycje na życzenie usera**: 5 puzzli + 10 stylów groutu (`86975a5`), potem profil die-cut wg zdjęć referencyjnych (`060b1e5`). Werdykt usera: grout — WSZYSTKIE 10 + kolor; puzzle — classic/ribbon/hex (organic/penrose odrzucone), die-cut jako profil rodziny.
- ✓ **Grout: 10 stylów kreski + paleta 12 kolorów WDROŻONE** (`8945009`): `draw_grout(style=…, color=…)`, solid bit-identyczny, style per-segment do masek warstwowych, crc32 bez RNG, fallback krótkich segmentów; CLI `--grout-style`/`--grout-color` + GUI 2 menu (też preview).
- ✓ **Sprint P: rodzina puzzle** (`be64bdc`, rejestr=48): 3 kształty na wspólnej maszynerii tabów (wspólna polilinia per krawędź, crc32); bramka ribbon-vs-classic CV narożników (0 vs 0,046).
- ✓ **E4: fraktale** (`174a5a3`, rejestr=51): `dragon` (twindragon, pole DOKŁADNE), `koch_island` (żółw na intach, period=4^depth), `koch_snowflake` (2-rozmiarowa, depth STAŁE=4 — RAM-budżet).
- ✓ **E5: islamskie gwiazdy** (`667bcf7`, rejestr=53): `gereh` (16 latawców/ośmiokąt + ROMBY; **bug schematu złapany bramką**: kwadrat osiowy zamiast rombu = 11k px dziur pod konturami PNG), `rosette` (36 komórek/dwunastokąt; dziury kotwiczone analitycznie — pułapka odfiltrowanego centrum niemożliwa).
- ✓ **META-LEKCJE opłacone i zapisane** (MEMORY + auto-memory `project_pillow_raster_instrument`): (a) duplikaty kolejnych wierzchołków łamią parzystość scanline'a Pillow (pasy 1-2 px, też w aa=4); (b) drabinka instrumentów pokrycia: proste→raster 1:1 / krzywe współdzielone→partycja formalna+FLOAT / nieparujące→FLOAT; (c) formalna partycja NIE dla kształtów z legalnymi T-junctions.
- ✓ **442→540 testów**; goldeny ×20 nowych (wszystkie cross-process, PYTHONHASHSEED=1); schematy z silnika (gen_puzzle/e4/e5_schemes.py); wszystko na origin/main.

## Co zostało (backlog sesji)

- ⟳ **E6 (3 kształty):** `scales` (NASTĘPNY KROK) + `nautilus` + `rosette_fractal`.
- ⟳ **E7 (3 kształty):** `sierpinski`, `sierpinski_d`, `sierpinski_carpet` (wszystkie 3 — decyzja usera 2026-07-16).
- ⟳ **E8:** docs + montaż zbiorczy 59 + mozaiki testowe → selekcja finalna usera → galeria 16K.
- ⟳ README: dokumentacja `--grout-style`/`--grout-color` (i zaległe `--grout`/`--grout-level`); panorama 4,0 GB @324 Mpx osobno od 3,9 GB @16K.
- ⟳ Hero panorama: lokalna, NIE opublikowana (Wariant C odłożony).
- ⟳ (przeniesione) PLAN_FRACTAL F1a; escher_lizard sylwetka.

## Aktywne pliki

- `PLAN_SHAPES_EXTRA.md` — kanoniczny plan (E1–E5 ✓, sekcje E6/E7 z pułapkami — czytać przed E6).
- `src/engine_smart.py` — generatory: `_gen_braid`/`_gen_moire`/`_puzzle_*`/`_gen_dragon`/`_gen_koch_*`/`_gen_gereh`/`_gen_rosette` (NOWE); następne: `_gen_scales`/`_gen_nautilus`/`_gen_rosette_fractal`.
- `src/grout.py` — style + kolory (NOWE: `_STYLES`, `GROUT_COLORS`, `_draw_grout_styled`).
- `src/tools/gen_extra_shape_schemes.py` — źródło geometrii E6/E7 (`gen_scales:847`, `gen_nautilus:688`, `gen_rosette_fractal:935`, `gen_sierpinski:84`…).
- `tests/test_grout_engine.py` — sekcje puzzle/E4/E5 + style groutu; `tests/test_golden_shapes.py` — 20 nowych goldenów.
- `assets/proposals/` — propozycje (historia); `assets/shape_schemes/` — schematy wdrożonych (z silnika).

## Otwarte pytania

- **Selekcja finalna kształtów przez usera** — po wdrożeniu wszystkich (E8); kandydaci do odrzucenia: `bloom` (subtelny).
- **Publikacja hero panoramy** (Wariant C) — decyzja usera.
- **koch_snowflake depth=4**: szwy sub-pikselowe (min cov 0,686) — jeśli zoom DZI ujawni miękkość szwów, rozważyć depth 5 tylko dla małych kadrów.
- **Grout styles na 16K**: style testowane na previews; pierwszy render 16K z kintsugi/neon warto obejrzeć (wydajność: capsule per segment — przy gęstych kształtach dużo segmentów).

## Do MEMORY.md (przeniesiono)

- **repo MEMORY.md:** [2026-07-19] Architektura: grout styles+kolory · rodzina puzzle+E4+E5 (rejestr 43→53, cel 59); Rozwiązane problemy: parzystość scanline'a Pillow + drabinka instrumentów pokrycia + bug schematu gereh.
- **auto-memory:** `project_pillow_raster_instrument.md` (NOWY — drabinka instrumentów, dedup wierzchołków).
