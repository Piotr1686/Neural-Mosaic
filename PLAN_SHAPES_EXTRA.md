# PLAN_SHAPES_EXTRA.md — Wdrożenie puli extra (17 kształtów, rejestr 39 → 56; E1+E2+E3 zamknięte, rejestr=45, zostaje 11)

**Status:** ZATWIERDZONY przez usera 2026-07-16. Kanoniczny plan puli extra. Kontynuacja `PLAN_SHAPES.md` (S3-S8 ZAMKNIĘTE — 39 kształtów w silniku, ostatni `poincare` 2026-07-15/16).
**Decyzja finalna:** bez zmian — po wdrożeniu WSZYSTKICH kształtów user generuje mozaiki testowe i dopiero wtedy decyduje, które zostają. Nie usuwać żadnego przed tą decyzją.

## Zakres

Punkt wyjścia (weryfikacja 2026-07-16, rejestr vs PNG): 39 kształtów w silniku, 57 schematów ⇒ **18 bez implementacji, 0 sierot**. Po usunięciu `kepler_ty` (duplikat) pula = **17**.

**ZOSTAJE 8** (rejestr=51 po E1-E4 + rodzinie puzzle):

```
gereh  nautilus  rosette  rosette_fractal  scales
sierpinski  sierpinski_carpet  sierpinski_d
```

Wdrożone: `penrose_p2` (E1, `b3e725c`) · `bloom`, `pebbles` (E2, `3990cfa`) · `stagger_tri`, `braid`, `moire` (E3). Cel końcowy puli: **rejestr 56**.

**POZA PULĄ — rodzina puzzle (sprint P, 2026-07-19, decyzja usera):** `puzzle_classic`, `puzzle_ribbon`, `puzzle_hex` — trzy siatki (kratka / kratka falowana / hex) z tabami die-cut jako WSPÓLNYMI poliliniami per krawędź (crc32, bez RNG; profil wg zdjęć referencyjnych usera). Bramki wg precedensu kształtów krzywoliniowych: **formalny test partycji** (classify_edges, 0 niesparowanych wewnętrznych — binarny raster 1:1 to ZŁY instrument dla krzywych: parzystość scanline'a Pillow gubi całe wiersze, zmierzone 784 fałszywe „dziury" przy dowodliwie dokładnej partycji) + pokrycie FLOAT na ścieżce masek silnika ss=4+BOX (kalibracja: wdrożony `voderberg` = 0,502 min / 210 px <0,9; puzzle ≤ tego) + goldeny ×2 cross-process. PUŁAPKA opłacona: zduplikowane KOLEJNE wierzchołki (złączenia ramię/łuk) łamią parzystość scanline'a Pillow także w maskach aa=4 → pasy 1-2 px; dedup `[1:]` jest nośny. Odrębność: `ribbon` vs `classic` bramką CV odległości narożników (0 vs 0,046, niewrażliwa na translacje); od `square`/`hexagon`/`moire` — krzywe tabów (>150 wierzchołków/komórkę). **Rejestr po sprincie P = 48; cel końcowy całości = 59.**

## ⚠ AUDYT KONSTRUKCJI (2026-07-17) — czytaj przed każdym sprintem

Pula powstała jako **schematy**, gdzie różnicę niósł KOLOR. Pod zdjęciami kolor znika, więc każde rozróżnienie „tylko paletą" zapada się w duplikat. Trzy trafienia (`kepler_ty`, `bloom`, `stagger_tri` — przy czym werdykt dla `stagger_tri` sam okazał się błędny, patrz niżej) ⇒ jednorazowy audyt konstrukcji wszystkich pozostałych, wykonany 2026-07-17. **Wynik jest wiążący — nie powtarzać analizy per sprint.**

**Duplikaty (różnica tylko w palecie):**
- `kepler_ty` — identyczne `(N, zeta, gamma)` co `penrose` → **USUNIĘTY** (`1e53982`).
- `bloom` — identyczna krata co `phyllotaxis` (kąt złoty, `r=c√i`, stała `(√2+0.45)`); motyw „21 ramion" był kolorem `i mod 21` → **ZRÓŻNICOWANY kątem Lucasa** (decyzja usera; `3990cfa`).
- ~~`stagger_tri`~~ — **WERDYKT AUDYTU OBALONY 2026-07-17 pomiarem (E3, `_gen_stagger_tri`).** Flaga `on = (ci & rj) == 0` faktycznie wybierała tylko paletę (to trafne), ale wniosek „geometria = tryb `triangle`" był **fałszywy i odwrócony**: to `triangle` przesuwa fazę o pół podstawy co rząd (jego reguła flipu `(c+r)%2` JEST tym przesunięciem — patrz `_grout_cells_triangle`, parzystość wierzchołka zmienia się z linią), a schemat trzymał fazę STAŁĄ. Pokrycie z `triangle` przy dowolnej translacji: **50%, nie 100%** ⇒ geometria była odrębna od początku i została przeniesiona 1:1. **Zalecone „przesunięcie o pół trójkąta" odtworzyłoby `triangle` w 100%** (przesunięty o `s/2`) — czyli zbudowałoby duplikat, który miało usunąć.

**Sprawdzone i ODRĘBNE** (dzielą maszynerię, ale różnią się KOMÓRKĄ — planować bez obaw; zweryfikować wizualnie po wdrożeniu):

| kształt | dzieli z | różnica w komórce |
|---|---|---|
| `gereh` | `trunc_square` (4.8.8) | ośmiokąt rozbity na 8+8 latawców |
| `rosette` | `trunc_hex` (3.12.12) | dwunastokąt rozbity na 12+12+12 komórek |
| `nautilus` | `sunburst` (log-polar) | biegun POZA kadrem (nie w środku) |
| `rosette_fractal` | `sunburst` (log-polar) | podwajanie sektorów co m pierścieni + trójkątne liście |
| `braid` | `brick_wall` | basketweave (naprzemienne pary 2:1), nie wozówkowy |
| `sierpinski_carpet` | `square` | kwadraty WIELU rozmiarów (tło 1/81, dziury od 1/27) |

**Bezspornie odrębne:** `moire` (wierzchołki wyginane polem interferencji — ostrzeżenie „≡ square" NIEAKTUALNE), `dragon`, `koch_island`, `koch_snowflake`, `scales`, `sierpinski`, `sierpinski_d`, `pebbles`.

**REGUŁA:** przed wdrożeniem porównuj **KONSTRUKCJĘ** z tym, co silnik ma — nie nazwę, nie docstring i nie werdykt tego audytu (patrz `stagger_tri`: audyt orzekł duplikat, pomiar orzekł odwrotnie). Drabinka narzędzi, rosnąco:
1. **Statystyki pól potrafią NIE wystarczyć** — `bloom` i `phyllotaxis` mają identyczny rozkład pól (wspólne promienie `r=c√n`), różni je tylko kąt.
2. **Porównanie współrzędnych potrafi NIE wystarczyć** — gdy rodziny dzielą KOMÓRKĘ i różnią się tylko UŁOŻENIEM (faza/orientacja), translacja zmienia każdą współrzędną, więc naiwny `a != b` przepuści duplikat (`stagger_tri`: wariant `s/2` = `triangle` przesunięty, 0/78 surowo vs 78/78 po wyrównaniu).
3. **Wtedy mierz z dokładnością do izometrii** — `_max_overlap` w `tests/test_grout_engine.py`, plus test kontrolny dowodzący, że bramka łapie znany duplikat.

---

**`kepler_ty` USUNIĘTY z puli (decyzja usera 2026-07-16)** — był **geometrycznie identyczny z wdrożonym `penrose`**: ta sama konstrukcja dualna pentagrid, `N=5`, `zeta=e^(2πik/5)`, `gamma=[0.05,0.15,0.25,0.35,0.20]`. Konstrukcja jest w pełni zdeterminowana przez `(N, zeta, gamma)` ⇒ ta sama teselacja; różniły je wyłącznie paleta (`pal_fat`/`pal_thin`) i okno, a kolor pod zdjęciami znika. Klasyczny tryb awarii „`moire` ≡ `square`”. Chronologia: schemat `kepler_ty` powstał 2026-07-03/04, `penrose` trafił do silnika 2026-07-10 tą samą maszynerią i unieważnił go po cichu. PNG skasowany. **Lekcja: przed wdrożeniem kształtu z puli porównaj jego KONSTRUKCJĘ z tym, co silnik już ma — nie nazwę.**

## Kontekst dla wykonawcy

- **`src/tools/gen_extra_shape_schemes.py` zawiera działającą, zweryfikowaną wizualnie geometrię wszystkich pozostałych — PRZENOŚ ją, nie wymyślaj od nowa.** To ta sama zasada, która zadziałała dla puli Fable. Mapa funkcji (odświeżona 2026-07-17 po usunięciu `gen_kepler_ty` — numery się przesunęły, zweryfikuj grepem po każdej edycji tego pliku):
  `gen_sierpinski:84` · `_sierp4:123` · `_gen_sierpinski_variant:134` · `gen_sierpinski_d:176` · `_carpet_cells:191` · `gen_sierpinski_carpet:213` · `gen_stagger_tri:239` · `gen_gereh:269` · `_twindragon_boundary:310` · `gen_dragon:361` · `_koch_edge:391` · `_snowflake:402` · `gen_koch_snowflake:410` · `_turtle_string:445` · `gen_koch_island:464` · `gen_rosette:617` · `gen_nautilus:688` · `gen_moire:740` · `gen_braid:783` · `gen_scales:847` · `gen_rosette_fractal:935`
- **Maszyneria silnika już istnieje** — nie budować od zera: `_polygon_sector` (rdzeń), `_multigrid_dual` (Penrose/AB), `_gen_voronoi` + `_emit_cells` + `_shape_seed` (Voronoi), `_graded_sunflower`/`_vogel_points` (Vogel, z parametrem `angle`), `_arc_pitch` (łuki — OBOWIĄZKOWY dla `scales`), `_lattice_mn_range` (lattice'y).
- **Wzorzec wdrożenia jednego kształtu** (ustalony przez 23 poprzednie): generator `_gen_<nazwa>` → wpis w `SHAPE_MODES` (single source of truth; GUI/CLI czytają przez `shape_names()`, nic nie hardkodować) → golden test (OBA border_mode) → test pokrycia rasteryzacją → **regeneracja schematu PNG z silnika**.
- User zatwierdza PO KAŻDYM sprincie. Po każdym sprincie: `pytest` zielony + commit.

## Sprinty (grupowane po WSPÓLNEJ MASZYNERII, nie po nazwie)

| Sprint | Kształty | Wspólny mianownik | Ryzyko |
|---|---|---|---|
| ~~**E1**~~ | ~~`penrose_p2`~~ | **ZAMKNIĘTY** `b3e725c` (rejestr=40) | — |
| ~~**E2**~~ | ~~`bloom`, `pebbles`~~ | **ZAMKNIĘTY** `3990cfa` (rejestr=42) | — |
| ~~**E3**~~ | ~~`stagger_tri`, `braid`, `moire`~~ | **ZAMKNIĘTY** (rejestr=45) | — |
| ~~**E4**~~ | ~~`dragon`, `koch_island`, `koch_snowflake`~~ | **ZAMKNIĘTY** (rejestr=51, z rodziną puzzle) | — |
| **E5** | `gereh`, `rosette` | islamskie partycje gwiaździste — wzorzec `girih` | średnie |
| **E6** | `scales`, `nautilus`, `rosette_fractal` | łuki + radialne (`_arc_pitch`, „dobry środek") | średnie |
| **E7** | `sierpinski`, `sierpinski_d`, `sierpinski_carpet` | rodzina sierpińskiego — wszystkie 3 warianty (decyzja usera 2026-07-16) | średnie |
| **E8** | docs + montaż zbiorczy 56 + mozaiki testowe | zamknięcie → selekcja finalna usera → galeria 16K | — |

Kolejność E1→E3 najpierw celowo: same reużywają istniejącą maszynerię, więc dają szybki, tani postęp i potwierdzają, że generyczny dispatch `polygon` zniesie kolejne wpisy bez regresji (potwierdzone: E1 i E2 nie wymagały ANI JEDNEJ edycji GUI/CLI — `shape_names()` podchwycił wszystko sam).

## Pułapki per grupa (lekcje już opłacone — nie odkrywać ponownie)

### E1 — deflacja P3
- `penrose_p2`: **NIE wyprowadzać substytucji P2 ręcznie** — dwukrotnie dała T-junctions. Jedyna działająca droga: deflacja P3 (Preshing, `_p3_half_deflate:539`) + relacje Robinsona **BS=AL, BL=AL+AS** (cięcie połówki grubego rombu w U: `|BU|=ramię`; kierunek `|CU|` daje 410 niesparowanych!), potem scalanie połówek lustrzanych: para = ten sam rodzaj + wspólne ramię + WSPÓLNY apex (bez testu chiralności z etykiet — odrzuca prawdziwych bliźniaków); cykle przy słońcach/gwiazdach rozwiązuje matching stopień-1-najpierw.
- ⚠ **Okno vs `base_s`:** schemat `gen_penrose_p2` produkuje STAŁY kwadrat jednostkowy (sun `Rd=2.2`, depth 6). W silniku głębokość musi wynikać z `base_s`: skala `k ≥ półprzekątna_kadru / 2.09` (2.09 = inradius dekagonu sun), głębokość `d = log(k·Rd/base_s)/log(φ)`. Liczba kafli rośnie ~`φ^(2d)` (@16K, base_s=100: d≈9, ~58k trójkątów) — mieści się w modelu RAM, ale sprawdzić `PeakRAMSampler` przy gęstych ustawieniach.

### E2 — Voronoi (ZAMKNIĘTY, `3990cfa`) — lekcje dla kolejnych sprintów
- Seed = `f(base_s, target_w, target_h)` przez `np.random.default_rng`, NIGDY globalny `random` (`seeded=True`).
- ⚠ **Liczenie ziaren:** `voronoi` skaluje sumę marginesem, bo jednorodne ziarna dzielą się w stałej proporcji. Przy NIEjednorodnej gęstości to zawodzi — zatrzymuj się na liczbie ziaren WEWNĄTRZ kadru.
- ⚠ **Partia przestrzeliwuje:** akceptacja ~11% ⇒ jedna partia 4096 daje ~450 ziaren i mały kadr dostaje stałe 425 kafli w KAŻDEJ rozdzielczości. Ucinaj prefiks na n-tym ziarnie w kadrze (prefiks próby i.i.d. = próba i.i.d.).
- ⚠ **Ucięcie zagładza margines** ⇒ komórki brzegowe nieograniczone ⇒ odrzucone ⇒ **5,3% dziur**. Potrzebne rusztowanie: jednorodny pierścień ziaren poza kadrem (rola `freeze_r` z `voronoi`). Trim i pierścień testować RAZEM.
- ⚠ **Znaleziona wada w istniejącym `voronoi`** (NIE naprawiona, poza zakresem E2): przy 384×288 `base_s=100` daje **12,8% dziur** — wchodzi podłoga `max(16, ...)` i 16 ziaren nie pokrywa kadru. Dotyczy skrajnie zgrubnych ustawień.

### E3 — lattice'y
- ✓ `stagger_tri` **WDROŻONY 2026-07-17** (rejestr=43, wariant A — przeniesienie 1:1, decyzja usera po obaleniu werdyktu audytu). Rzędy trójkątów o **stałej fazie x** ⇒ każda pozioma linia rzędu to linia poślizgu z T-junctions (legalne — każdy rząd dzieli własny pas niezależnie, więc faza nie może otworzyć dziury; precedens `sierpinski`). Skala `s = 2·base_s/3^(1/4)` (konwencja puli: średnie pole = `base_s²`; schemat używał `s = base_s`, czyli konwencji `triangle` — pole 0,433·base_s²). Flaga palety `on` porzucona.
  - **META-LEKCJA (bramka): zalecony test „porównaj współrzędne z `triangle`" BYŁBY ŚLEPY.** Wariant z przesunięciem o `s/2` to `triangle` przesunięty o `s/2` — **każda** współrzędna się różni (0/78 wspólnych surowo), więc naiwny `a != b` (wzorzec `test_bloom_geometry_differs_from_phyllotaxis`) dałby zielone światło duplikatowi; po wyrównaniu translacji: 78/78. Bramka MUSI być niewrażliwa na translację. Wdrożone w `tests/test_grout_engine.py`: `_max_overlap` (kandydaci na translację = różnice centroid od kotwicy — wyczerpujące, bez skanowania siatki offsetów) + test kontrolny `test_translation_gate_catches_the_half_base_phase_duplicate`, który dowodzi, że bramka ma zęby (łapie wariant `s/2` jako 100%).
  - Uogólnienie: dla rodzin dzielących KOMÓRKĘ, a różniących się tylko UŁOŻENIEM (faza/orientacja), różnica musi być mierzona z dokładnością do izometrii — inaczej test mierzy układ współrzędnych, nie kształt.
- ✓ `moire` **WDROŻONY 2026-07-18** (rejestr=45, `_gen_moire`, przeniesienie 1:1). Siatka quadów o wierzchołkach przesuniętych polem interferencji dwóch krat; sąsiednie quady dzielą PRZESUNIĘTE wierzchołki ⇒ partycja bez dziur, ale każda komórka faluje kształtem/rozmiarem. Amplituda `A=0,42 < 0,5` (jednostki siatki) gwarantuje brak inwersji komórek. **Częstotliwość w jednostkach SIATKI, nie px** ⇒ dudnienie obejmuje stałą liczbę kafli w każdej rozdzielczości (lekcja girih/truchet: „ten sam wzór, tylko więcej"). Skala `s = base_s` (dudnienie biasuje średnie pole ~3% w górę — warp tylko I-rzędu area-preserving; wciąż „~base_s²"). **⚠ Ostrzeżenie „moire ≡ square" ROZSTRZYGNIĘTE POMIAREM na prawdziwym renderze:** NIE degeneruje się — CV pola komórek ≈ 0,27, tylko ~28% krawędzi osiowych (square = 0 i 100%), max/min pola = 2,85. Test `test_moire_does_not_degenerate_to_square` mierzy oba (na geometrii, nie schemacie — konwencja po `kepler_ty`). Goldeny ×2 cross-process, pokrycie ×5, schemat z silnika. +9 testów (452→461).
- ✓ `braid` **WDROŻONY 2026-07-18** (rejestr=44, `_gen_braid`, przeniesienie 1:1). Basketweave: cegiełki 2:1 w naprzemiennych parach poziomych/pionowych na szachownicy bloków 2×2 — płaski przeplot bez nad/pod (over-under = nakładanie, złamałoby partycję). Skala `u = base_s/√2` (pole cegiełki = 2·u² = base_s²). **Bramka odrębności zbudowana na `_max_overlap` (izometryczna), NIE na surowym `a != b`** — bo to klasa „różnica w UŁOŻENIU, nie komórce" (jak `stagger_tri`): (a) `test_braid_is_not_a_running_bond_under_any_translation` — wozówkowy jednoorientacyjny z tej samej cegiełki nie odtwarza `braid` (<0,99; jego pionowe cegiełki to orientacja, której `brick_wall` nie ma); (b) **zęby** `test_braid_parity_flip_is_a_pure_translation_duplicate` — odwrócenie parzystości `(I+J)` (kuszący „restagger") to `braid` przesunięty o jeden blok ⇒ surowo różny, ale bramka MUSI dać pełne dopasowanie (1,0). Goldeny ×2 cross-process (PYTHONHASHSEED=1), pokrycie ×5 kadrów (holes==0), schemat zregenerowany z silnika (`gen_e3_schemes.py`). +10 testów (442→452).

### E4 — rep-tile / Koch — ZAMKNIĘTY 2026-07-19 (rejestr=51)
- ✓ `dragon` **WDROŻONY** (`_gen_dragon` + `_twindragon_boundary`): twindragon order 8 (256 kwadratów w bazie 1+i; brzeg przez kasowanie krawędzi + najostrzejszy skręt w lewo na pinchach; 246 wierzchołków). `(1+i)^8 = 16` ⇒ krata przesunięć to ZWYKŁA kratka 16 jednostek; `u = base_s/16` ⇒ pole DOKŁADNIE base_s². Krawędzie osiowe + wspólne coasty bit-identyczne (int·float) ⇒ klasyczny raster 1:1 holes==0 jest tu poprawnym instrumentem. Determinizm: tylko hashe int/int-tuple (nieslone).
- ✓ `koch_island` **WDROŻONY** (`_gen_koch_island`): Minkowski depth 2, żółw na CZYSTYCH INTACH (tabela kierunków, zero pyłu `exp(iπ/2)`); **period = 4^depth = 16, NIE bbox** (pułapka 2026-07-03; test `test_koch_island_period_is_lattice_not_bbox` — sąsiad = translacja o okres). Generator area-preserving ⇒ pole DOKŁADNIE base_s². Punkt domykający pętlę zrzucony (pułapka duplikatów kolejnych wierzchołków ze sprintu P).
- ✓ `koch_snowflake` **WDROŻONY** (`_gen_koch_snowflake`): teselacja 2-rozmiarowa (duże płatki krok 2Rb; 2 małe 1/√3, obrót 30°, w dziurach; bilans pól DOKŁADNY 1:3, `Rb = 0,6937·base_s` ⇒ duży ≈ base_s²). **Głębokość STAŁA = 4** — skończona aproksymacja wspólnej granicy z RÓŻNYCH baz ⇒ szwy nie parują się dokładnie: NIE stosować formalnego testu partycji ani rastra 1:1; bramka = pokrycie FLOAT na maskach silnika (zmierzone min 0,686 / 0 px <0,45 / 0 px >1,5 — lepiej niż voderberg 0,502). Depth 5 odrzucony: ~1,2 GB poligonów @16K (budżet A1).

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

- 14 pozostałych kształtów renderuje z CLI i GUI (`python -m src.cli render ... --shape <mode>`), rejestr = **56**,
- golden testy + pełny `pytest` zielone,
- schematy PNG wszystkich zregenerowane Z SILNIKA,
- README EN+PL: tabela kształtów + montaż zbiorczy 56,
- seria mozaik testowych (batch CLI po wszystkich kształtach) → **user wybiera finalny zestaw** → galeria 16K.
