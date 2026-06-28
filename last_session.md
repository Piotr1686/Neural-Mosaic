# last_session.md

**Sesja:** 2026-06-28 · 22:05-22:30
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 26c5d0a @ main (origin ZSYNCHRONIZOWANY — `26c5d0a` wypchnięty, branch == origin/main)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Podmiana triangle + hexagon w galerii na prawdziwe 16K — CZEKA NA PLIKI OD USERA.** User sam wygeneruje 16K triangle+hexagon i napisze, że gotowe. Wtedy: (1) wstaw nowe `.dzi` + foldery `*_files/` do `docs/tiles/`, (2) usuń stare `showcase_triangle_20260502_101900*` i `hexagon_jump_16K*`, (3) zaktualizuj `tileSources` **oraz** etykiety w `docs/index.html` (8K→16K, nowe wymiary/MP, przyciski btn4/btn5). Pułapki: `Format="jpg"` w XML (nie `"jpeg"` → czarny ekran OpenSeadragon, [[project_dzi_format_bug]]); sprawdź budżet GitHub Pages (piramidy obecnie ~165 MB).

Kontekst: galeria miała „3×16K + 2×8K"; user chce 5×16K. Akcja jest zablokowana do momentu, aż user dostarczy pliki — jeśli na /start ich jeszcze nie ma, w międzyczasie zrób **Krok 6 portfolio** (audyt twierdzeń README, patrz backlog).

---

## Co zrobiono w tej sesji

- ✓ **README hero podmienione na magnifier papugi 4×4** (commit `26c5d0a`, na origin/main): stare `spectre_full.jpg` nie pokazywało kafelków nawet po zoomie → nowy `assets/examples/spectre_hero_magnifier.jpg` (1600×900, wariant „e" z 5 propozycji). Styl jak social_preview: żółty box na lewej krawędzi dzioba (przejście kolor→białe tło), linie łączące, inset ~4×4 kafelki, podpis „every tile is a separate photograph". Podmieniono w `README.md`+`README.pl.md` (linia 17); `spectre_full.jpg` ZOSTAJE w tabeli progressive-zoom (linia 103).
- ✓ **Audyt rozdzielczości galerii:** potwierdzono że tylko **photo/symbol/spectre = 16K**; **triangle (8192×4612) i hexagon (8192×6144) = 8K**. Etykiety w `docs/index.html` są uczciwe („8K"); plik hexagona myląco nazwany `hexagon_jump_16K.dzi` (realnie 8K) — kosmetyka, niewidoczna dla zwiedzających.
- ✓ Commit `26c5d0a` wypchnięty na origin; branch == origin/main.

## Co zostało (backlog sesji)

- ⟳ **Galeria 5×16K (NASTĘPNY KROK):** swap triangle+hexagon na 16K — czeka na pliki od usera.
- ⟳ **Krok 6 portfolio (standing):** adwersarialny audyt twierdzeń README.md/README.pl.md (każda liczba/feature/flaga/ścieżka pokryta kodem) → poprawki jednym commitem `docs(readme): fix unverified claims`. Nieaktualny w tej sesji, nadal otwarty.
- ⟳ **Krok 5 portfolio:** PyInstaller `.exe` (model-free) — wysiłek wysoki, ROI średni; osobny projekt.
- ⟳ **TODO odłożony:** pasek postępu „Export Deep Zoom" + `test_dzi` ([[project_dzi_gui_polish_todo]]).
- ⟳ Świadomie ODŁOŻONE: Wariant C (A1/A2), ML/CLIP, Docker/plugin.

## Aktywne pliki

- `docs/index.html`, `docs/tiles/{showcase_triangle_*,hexagon_jump_16K}*` (cel swapu 16K)
- `README.md` + `README.pl.md` (hero zmienione; cel Kroku 6)
- `assets/examples/spectre_hero_magnifier.jpg` (nowe hero)
- Generator (scratchpad, nie w repo): `gen_parrot_magnifier.py` (źródło: `output/github_readme/spectre_parrot_16K.jpg`, tile pitch ~140 px w 16K)

## Otwarte pytania

- Galeria: czy 5×16K zmieści się w budżecie GitHub Pages (obecnie ~165 MB piramid + 2×16K dojdzie ~70-100 MB)? Sprawdzić przy swapie.
- Przy swapie: zmienić też mylącą nazwę `hexagon_jump_16K.dzi` na coś bez „16K" w starej wersji / nadać sensowny slug nowym plikom.

## Do MEMORY.md (przeniesiono/zaktualizowano w tej sesji)

- [Aktywne TODO] NOWY wpis [2026-06-28] „Galeria — podmiana triangle+hexagon na 16K (CZEKA NA USERA)" — audyt rozdzielczości + plan swapu + pułapki.
- [Aktywne TODO] NOWY wpis [2026-06-28] „README hero = magnifier papugi 4×4" (commit `26c5d0a`) — co, dlaczego, generator, że `spectre_full.jpg` zostaje w tabeli zoom.
