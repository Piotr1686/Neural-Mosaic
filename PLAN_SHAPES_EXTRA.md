# PLAN_SHAPES_EXTRA.md — Wdrożenie puli extra (18 kształtów, rejestr 39 → 57)

**Status:** ZATWIERDZONY przez usera 2026-07-16. Kanoniczny plan puli extra. Kontynuacja `PLAN_SHAPES.md` (S3-S8 ZAMKNIĘTE — 39 kształtów w silniku, ostatni `poincare` 2026-07-15/16).
**Decyzja finalna:** bez zmian — po wdrożeniu WSZYSTKICH kształtów user generuje mozaiki testowe i dopiero wtedy decyduje, które zostają. Nie usuwać żadnego przed tą decyzją.

## Zakres

18 kształtów ma **schemat PNG w `assets/shape_schemes/`, ale NIE MA implementacji w silniku**. Weryfikacja 2026-07-16 (rejestr vs PNG): 39 w silniku, 57 schematów, 18 brakujących, **0 sierot** (każdy kształt w silniku ma schemat).

```
bloom  braid  dragon  gereh  kepler_ty  koch_island  koch_snowflake  moire
nautilus  pebbles  penrose_p2  rosette  rosette_fractal  scales
sierpinski  sierpinski_carpet  sierpinski_d  stagger_tri
```

## Kontekst dla wykonawcy

- **`src/tools/gen_extra_shape_schemes.py` (1148 l.) zawiera działającą, zweryfikowaną wizualnie geometrię wszystkich 18 — PRZENOŚ ją, nie wymyślaj od nowa.** To ta sama zasada, która zadziałała dla puli Fable. Mapa funkcji: `gen_sierpinski:82`, `_sierp4:121`, `_gen_sierpinski_variant:132`, `gen_sierpinski_d:174`, `_carpet_cells:189`, `gen_sierpinski_carpet:211`, `gen_stagger_tri:237`, `gen_kepler_ty:267`, `gen_gereh:321`, `_twindragon_boundary:362`, `gen_dragon:413`, `_koch_edge:443`, `_snowflake:454`, `gen_koch_snowflake:462`, `_turtle_string:497`, `gen_koch_island:516`, `_p3_half_deflate:539`, `gen_penrose_p2:561`, `gen_rosette:669`, `gen_nautilus:740`, `gen_moire:792`, `gen_braid:835`, `gen_bloom:859`, `gen_scales:899`, `gen_pebbles:941`, `gen_rosette_fractal:987`.
- **Maszyneria silnika już istnieje** — nie budować od zera: `_polygon_sector:2408` (rdzeń), `_multigrid_dual:895` (Penrose/AB), `_gen_voronoi:628`, `_gen_penrose:957`, `_arc_pitch:1184` (łuki).
- **Wzorzec wdrożenia jednego kształtu** (ustalony przez 23 poprzednie): generator `_gen_<nazwa>` → wpis w `SHAPE_MODES` (single source of truth; GUI/CLI czytają przez `shape_names()`, nic nie hardkodować) → golden test (OBA border_mode) → test pokrycia rasteryzacją → **regeneracja schematu PNG z silnika**.
- User zatwierdza PO KAŻDYM sprincie. Po każdym sprincie: `pytest` zielony + commit.

## Sprinty (grupowane po WSPÓLNEJ MASZYNERII, nie po nazwie)

| Sprint | Kształty | Wspólny mianownik | Ryzyko |
|---|---|---|---|
| **E1** | `penrose_p2`, `kepler_ty` | multigrid/deflacja — reużycie `_multigrid_dual` i `_gen_penrose` | niskie |
| **E2** | `bloom`, `pebbles` | Voronoi + próg min-area — reużycie `_gen_voronoi` | niskie |
| **E3** | `braid`, `moire`, `stagger_tri` | czyste lattice'y wielokątne, rdzeń `_polygon_sector` | niskie |
| **E4** | `dragon`, `koch_island`, `koch_snowflake` | rep-tile / Koch (geometria gotowa w gen_extra) | średnie |
| **E5** | `gereh`, `rosette` | islamskie partycje gwiaździste — wzorzec `girih` | średnie |
| **E6** | `scales`, `nautilus`, `rosette_fractal` | łuki + radialne (`_arc_pitch`, „dobry środek") | średnie |
| **E7** | `sierpinski`, `sierpinski_d`, `sierpinski_carpet` | rodzina sierpińskiego — wszystkie 3 warianty (decyzja usera 2026-07-16) | średnie |
| **E8** | docs + montaż zbiorczy 57 + mozaiki testowe | zamknięcie → selekcja finalna usera → galeria 16K | — |

Kolejność E1→E3 najpierw celowo: same reużywają istniejącą maszynerię, więc dają szybki, tani postęp i potwierdzają, że generyczny dispatch `polygon` zniesie +18 wpisów bez regresji.

## Pułapki per grupa (lekcje już opłacone — nie odkrywać ponownie)

### E1 — multigrid
- `penrose_p2`: **NIE wyprowadzać substytucji P2 ręcznie** — dwukrotnie dała T-junctions. Jedyna działająca droga: deflacja P3 (Preshing, `_p3_half_deflate:539`) + relacje Robinsona **BS=AL, BL=AL+AS** (cięcie połówki grubego rombu w U: `|BU|=ramię`; kierunek `|CU|` daje 410 niesparowanych!), potem scalanie połówek lustrzanych: para = ten sam rodzaj + wspólne ramię + WSPÓLNY apex (bez testu chiralności z etykiet — odrzuca prawdziwych bliźniaków); cykle przy słońcach/gwiazdach rozwiązuje matching stopień-1-najpierw.
- `kepler_ty`: pentagrid de Bruijna N=5 = kopia zwalidowanego kodu `ammann_beenker`; γ suma=1. ⚠ Znak w Cramerze dla `py` — wzorzec w `gen_fable_shape_schemes.py::gen_ammann_beenker`. RANGE ≈ okno+3, inaczej dziury przy brzegach.

### E2 — Voronoi
- Seed = `f(base_s, target_w, target_h)` przez `np.random.default_rng`, NIGDY globalny `random` (`seeded=True` w rejestrze). Inna geometria w preview niż w renderze jest OK (tak działa spectre), ale MUSI być powtarzalna dla tych samych wymiarów.
- `bloom` = Voronoi ziaren phyllotaxis (kąt złoty, `r=c√i` ⇒ komórki ~równopolowe). `pebbles` = Voronoi o zmiennej gęstości (blob-y gaussowskie + rejection sampling). Próg min-area `(base_s/4)²`.

### E3 — lattice'y
- `moire`: ⚠ **Historyczne ostrzeżenie „moire ≡ square" jest NIEAKTUALNE** — schemat po rewizji 2026-07-04 pokazuje prawdziwe moiré geometryczne (2 obrócone siatki → komórki = przecięcia, zmienny kształt). Zweryfikowano wizualnie 2026-07-16. Ale zasada nadrzędna zostaje: **kształt ma sens TYLKO gdy geometria komórki różni się od kwadratu** — po wdrożeniu sprawdzić na prawdziwym renderze, czy nie zdegenerował się do `square`.
- `braid`: basketweave (pary prostokątów 2:1, naprzemienna orientacja). Zweryfikowano 2026-07-16: to NIE jest duplikat `weave` (tam wstęgi + komórki-węzły) ani `brick_wall`. Płaski przeplot bez nad/pod — over-under = nakładanie, złamałoby regułę teselacji.

### E4 — rep-tile / Koch
- `dragon` = twindragon rep-tile order 8 (2^n kwadratów w bazie 1+i; brzeg przez kasowanie krawędzi + najostrzejszy skręt w lewo na pinchach; siatka `(1+i)^n·Z[i]`) — kafle w kształcie smoka, NIE wstęgi.
- `koch_island` = Minkowski reptile; **period = 4^depth, NIE bbox** (pułapka zapisana 2026-07-03).
- `koch_snowflake` = teselacja 2-rozmiarowa (duże płatki na siatce trójkątnej o kroku 2R stykają się w 6 punktach promienia R; 2 małe w skali 1/√3, obrót 30°, w dziurach; bilans pól DOKŁADNY). Sam płatek NIE kafelkuje — dlatego wariant 2-rozmiarowy.

### E5 — islamskie gwiazdy
- `gereh` = same czworokąty: gwiazda-8 rozbita na 8 rombów-latawców centralnych (`r_in=0.60·apotema`) + 8 latawców zewn. + kwadraty. NIE gwiazda-na-wierzchu (to była nakładka).
- `rosette` = 12-krotna rozeta islamska (zellij, Fez) jako partycja 3.12.12: dwunastokąt → 12 latawców rdzenia + 12 płatków-czworokątów + 12 trójkątów krawędziowych. ⚠ Trójkąty międzywęzłowe OSOBNĄ pętlą po WSZYSTKICH centrach (dziura może należeć do centrum odfiltrowanego!) + filtr BOX, nie promieniowy (rogowe rozety).
- Lekcja z `girih`: greedy nie wyhoduje dekagonu (10 z 1610 prób) — te dwa są konstrukcyjne, nie greedy. Jeśli mimo to zostaną dziury: otoczka wypukła dziur malowana 2× daje kontur (7-11% kadru) — patrz `project_girih_lattice`.

### E6 — łuki i radialne
- ⚠ **`scales` ma ŁUKI** (komórka = kopuła + 2 wklęsłe łuki; okręgi `r` na siatce szachownicowej `dx=2r, dy=r`, offset `r`, pokrycie DOKŁADNE, przecięcia w `(0,-r),(±r,0)`). Krok polygonizacji **MUSI** być `_arc_pitch(r, tol=0.35)` = `sqrt(8·r·tol)`, a **NIE `seg = base_s/3`** — ta pomyłka sfasetowała truchet_hex (promień łuku tu nie rośnie z kadrem, jest ~stały, więc stały `seg` daje strzałkę 1-3 px = widoczny wielokąt).
- **Wzorzec „dobrego środka"** (reguła usera): komórki radialne NIE mogą zbiegać do zera przy biegunie. `nautilus` rozwiązuje to biegunem log-spirali POZA kadrem `(-1.55,-1.30)` + stały `nsec` + geometryczne promienie ⇒ ~kwadratowe komórki w każdej skali. `rosette_fractal` (aloes) = sektory ×2 co `m=3` pierścienie z `g=2^(1/m)`; wspólne krawędzie próbkowane identycznie z obu stron (inaczej T-junctions).

### E7 — sierpiński
- Wszystkie warianty mają PNG: `sierpinski` (depth 3, nieparzyste rzędy przesunięte o S/2 — cegiełki; T-junctions legalne w partycji), `sierpinski_d`, `sierpinski_carpet` (dywan 3×3 depth 3 na cały kadr), plus `stagger_tri` (w E3).
- Nie-nośniki przez `_sierp4` (4 pod-gaskety depth 2, dziury capowane na `S/4`). Plan foto: liście = najmniejsze zdjęcia, dziury poziomu 1..3 = coraz większe pojedyncze zdjęcia.
- **DECYZJA USERA 2026-07-16: wdrażamy WSZYSTKIE 3 warianty** (`sierpinski`, `sierpinski_d`, `sierpinski_carpet`) — żaden nie wypada przed selekcją finalną, zgodnie z regułą nadrzędną planu. Historyczny zapis o wariantach `sierpinski_b`/`sierpinski_c` jest NIEAKTUALNY (nie istnieją na dysku).

## Wyzwania przekrojowe (checklista przed KAŻDYM sprintem)

1. **Schemat ≠ silnik** — po wdrożeniu **zregeneruj PNG Z SILNIKA** dedykowanym, COMMITOWANYM narzędziem (`src/tools/gen_*_scheme.py`). Ta pułapka trafiła girih, poincare i truchet: schemat reklamował wzór, którego silnik nie rysuje.
2. **Bit-repro preview↔render** — golden SHA-256 dla obu `border_mode`; RNG tylko seeded.
3. **Grout** — generyczny flat działa dla każdego wpisu w `SHAPE_MODES` za darmo. Hierarchiczny (`_grout_cells_<nazwa>` + `_HIERARCHICAL_GROUT` + `GROUT_HIERARCHICAL`) TYLKO tam, gdzie istnieje naturalna hierarchia: `rosette` (latawiec/płatek → rozeta), `gereh` (latawiec → gwiazda), sierpiński (poziom dziury). PUŁAPKA: selekcja poziomów to `>= N`, nie `<= N`. META-LEKCJA th-vs-step: maski nakładające → FLOAT th, abutujące → INT step.
4. **T-junctions** — liczba podziałów wspólnej krawędzi musi być globalną funkcją KRAWĘDZI, nie komórki. Test: zero niesparowanych szwów z oboma końcami wewnątrz kadru (wzorzec: sparametryzowany test partycji ×5 kadrów z `tests/test_grout_engine.py`).
5. **Reindeks NIEPOTRZEBNY** — kształty są po stronie targetu, indeks 79-dim jest agnostyczny.
6. **Peak-RAM** — model zmierzony 2026-07-16: `delta ≈ 1,27 GB stałe + 0,0085 GB/Mpx`, liniowy. Gęste kształty (sierpiński depth 3, rosette) podbijają liczbę komórek — przy wątpliwości pomiar `PeakRAMSampler` z `tests/benchmark.py`.
7. **ASCII-only** w printach `src/tools/*` i testach (terminal CP1250).
8. **Weryfikuj surową ścieżkę CLI/GUI**, nie tylko własny skrypt — wrapper potrafi zamaskować bug (patrz `project_dzi_decompression_bomb`).

## Definicja ukończenia (E8)

- 18 kształtów renderuje z CLI i GUI (`python -m src.cli render ... --shape <mode>`), rejestr = **57**,
- golden testy + pełny `pytest` zielone,
- schematy PNG wszystkich 18 zregenerowane Z SILNIKA,
- README EN+PL: tabela kształtów + montaż zbiorczy 57,
- seria mozaik testowych (batch CLI po wszystkich kształtach) → **user wybiera finalny zestaw** → galeria 16K.
