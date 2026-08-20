# MEMORY.md — Długoterminowa pamięć projektu Neural-Mosaic

> Ten plik kumuluje wiedzę o projekcie. Nigdy nie usuwaj wpisów — tylko dopisuj.
> Każdy wpis oznaczaj datą w formacie [YYYY-MM-DD].
> Historia zamkniętych sprintów/wdrożeń (cała saga rozbudowy rejestru kształtów
> 20→59→50, poprzednie fixy typo/CI/docs) przeniesiona do `MEMORY.archive.md`
> (konsolidacja 2026-07-27, plik przekroczył 400 linii) — wciąż aktualna, tylko
> nie w tym pliku.

---

## Architektura

[2026-04-18, zaktualizowano 2026-04-18] **SmartEngine — dopasowanie kolorowe (LAB 5×5)**
- Silnik w `src/engine_smart.py` używa 75-wymiarowego wektora cech (siatka 5×5 w przestrzeni CIELAB)
- Indeks buduje `src/indexer_smart.py` → `data/smart_index.pkl`; schema_version="5x5", feature_dim=75
- Dopasowanie przez `cKDTree` + `cdist` (euclidean), chunk_size=500, top-50 kandydatów
- Spatial anti-repetition: `cKDTree` po współrzędnych kafelka, search_radius = 1.5×base_s
- Obsługuje **50 geometrii** — jedyne źródło prawdy to `SHAPE_MODES` w `engine_smart.py` (kolejność ALFABETYCZNA od 2026-07-26); nie duplikuj listy w kodzie ani w dokumentach, czytaj przez `shape_names()`
- Geometria `kites` = deltoidalna trójheksagonalna: każdy spłaszczony heksagon dzielony na 6 latawców, każdy latawiec = osobny sektor/zdjęcie (per-tile, deterministyczne, bez RNG). Zastąpiła stary tryb `kite` (8-kite "hat" z losową orientacją) — 2026-06-30
- LIBRARY_DIRS: data/library_starter/tiles, library_public, library_extended, library_private
- Blokada renderowania przy niezgodnym indeksie (hard block jeśli dim≠75 lub schema≠"5x5")
- Post-processing: Color Blend (0–30%, Image.blend) + Tile Tint (0–40%, RGB mean shift)
- WAŻNE: po zmianie 3×3→5×5 istniejący smart_index.pkl jest niekompatybilny — wymaga przebudowy!

[2026-04-18] **TypoEngine — font/symbol mosaic**
- Silnik w `src/engine_typo.py`, indeks w `data/typo_index.pkl`
- Glify renderowane PIL, dopasowanie po density (jasność)
- Grupowanie fontów: `src/font_groups.py` — 7 grup (A_cjk, B_ancient, C_symbols, D_latin_clean, E_decorative, F_handwriting, G_uncategorized)
- Tryby: black_on_white, white_on_black, color_on_white, color_on_black
- color_on_white: HLS clamping l≤0.45, s≥0.4; color_on_black: l≥0.55, s≥0.5
- Posteryzacja przez PIL quantize(MEDIANCUT) — palette_size 8/16/32/None
- Parametr variation (domyślnie 20): niższy = ostrzejszy, wyższy = organiczny

[2026-07-08] **Dopasowanie świadome maski — plan jakości 1+2+3 WDROŻONY** (commity 3dd42d9, 0d2c5f8)
- `create_mosaic`: zapis JPEG z `subsampling=0` (4:4:4) — mozaika to tysiące ostrych granic kolorów, domyślne 4:2:0 rozmywało chrominancję na szwach/fugach
- `_mean_fill_outside_mask` rozszerzone na gałęzie grid (standardowa + hexagon_romb composite) — wcześniej tylko kites/spectre; triangle miał ~50% bboxa zanieczyszczone treścią sąsiadów
- `_mask_cell_weights` + **ważony re-scoring top-K**: wagi = pokrycie maską komórek 5×5 (BOX, ten sam kernel co cechy), normalizacja do średniej 1.0 (balans freq_penalty zachowany); maska pełna → None → square bit-w-bit; edge-dimy z wagą 1.0; `wmask` także w `_polygon_sector` (kształty S2+ dostają za darmo)
- DECYZJA ARCHITEKTONICZNA: re-scoring top-K ZAMIAST sqrt(w)-przed-GEMM — wiele masek w jednym renderze (triangle norm/flip, hexagon_romb×3, kites×6, spectre per sektor) wymagałoby kopii biblioteki per maska; GEMM/`_euclid_f32` nietknięty → inwariant A1 („prawdziwy euklides") bezpieczny
- Empiria (0013.jpg, triangle 2K): deltaE LAB do oryginału 9.27→8.46 (~9% skumulowane); czas renderu bez regresji; goldeny: 7 regen. (celowo), square/False niezmieniony przez OBIE zmiany = dowód izolacji ścieżki GEMM
- Punkt 4 planu: WDROŻONY 2026-07-09 — patrz wpis niżej (UWAGA: pierwotne założenie „re-fetch picsum po seedzie" okazało się błędne — seed dryfnął; głównym źródłem odzysku jest COCO)

[2026-07-09] **Nakładka hi-res `tiles_hires/` — punkt 4 planu jakości WDROŻONY i ZWERYFIKOWANY A/B** (commity 9e5b6cf, 3515769, 00df732, 7d8c3f9, 6bf7ac4, 6783a46; 303 testy; PLAN_HIRES.md = plan kanoniczny)
- DIAGNOZA: winowajcą miękkich kafli był `src/optimizer.py` (TARGET_SHORT_SIDE=250, nadpis in-place) — zmiażdżył całą bibliotekę 421k kafli z pełnej rozdzielczości datasetów (COCO ~640px, Food-101 512px…); archiwa źródłowe skasowane, oryginały nie istnieją lokalnie
- ARCHITEKTURA: paste-time overlay — `engine_smart.HIRES_DIR` (`data/tiles_hires/`, kluczowana nazwą pliku); `_load_hires_overlay()` buduje set nazw RAZ na render (zero stat per kafel), `_resolve_tile_path()` podmienia ścieżkę tylko przy wklejaniu; dopasowanie/indeks/GEMM NIETKNIĘTE (inwariant A1); pusta nakładka = render bit-w-bit (goldeny bez regeneracji). INWARIANT: `tiles_hires` NIGDY w LIBRARY_DIRS (indexer by zdublował, optimizer zmiażdżył) — guard + test
- PĘTLA: `create_mosaic` zapisuje `<stem>_used_tiles.json` (kafle z count>0; preview bez I/O) → `python -m src.tools.upgrade_tiles --used-json …` (router per-źródło, async fetch, zapis bajtów as-is) → następny render automatycznie ostry
- BRAMKA LAB (`verify_identity`, 5×5 CIELAB deltaE, próg 8.0): każdy pobrany plik porównywany z oryginałem 250px; złapała DRYF PICSUM — `picsum.photos/seed/{idx}` zwraca dziś INNE zdjęcia (deltaE ~49) → picsum NIEodzyskiwalny, domyślnie niepobierany (opt-in `--include-picsum`). COCO odzyskiwalny per-file (id z nazwy: `coco_train_*`→train2017, `coco_*`→unlabeled2017; kolejność prefiksów = inwariant routera)
- EMPIRIA A/B (0013.jpg, 8K, tile_scale=3.0): upgrade 313/313 COCO → re-render; przypisania identyczne; ostrość (wariancja Laplace'a) **+48.7% globalnie**, komórki do 4×; dowód `output/0013_ab_comparison.png`. Rozkład użytych kafli z realnych renderów: COCO ~69%, archiwa ~15%, stracone ~15%
- PREWENCJA (nowi userzy): `DOWNLOAD_SIZE=512` w config (odsklejone od TILE_SIZE=75 — to było źródło miękkich świeżych pobrań), optimizer 250→512 (env `OPTIMIZER_SHORT_SIDE`) + delete-corrupt tylko za flagą + guard na tiles_hires
- DECYZJA: Sprint 5 (archiwa food/places/dogs/flowers) ZAMKNIĘTY — NIE robić (8 GB pobrań za +16% przy ~15% straconych = zły ROI); wyjątek on-demand: places-only (2.3 GB → ~10%); ESRGAN odroczony — wraca TYLKO jeśli deep-zoom DZI ujawni widoczną miękkość kafli nie-COCO

[2026-07-19] **Grout: 10 stylów kreski + paleta 12 kolorów** (commit `8945009`; propozycje `86975a5`)
- `src/grout.py`: `draw_grout(style=…, color=…)` — `solid` = klasyczna ścieżka BIT-IDENTYCZNA (test `test_solid_default_is_the_classic_pass`); 10 stylów (zigzag, squiggle, double, stitch, beads, rope, bevel, neon, kintsugi, brush) przez `_draw_grout_styled`: syntezatory per-segment do masek L per warstwa koloru (bevel światło/cień, neon halo+rdzeń, kintsugi złoto+blik, beads obwódka+wypełnienie), kompozycja w kolejności deklaracji; ta sama maszyneria ss=4+BOX+paste-with-self co solid
- `GROUT_COLORS` (12, default black) + `resolve_color`/`color_names`/`style_names` (single source of truth dla GUI/CLI). CLI: `--grout-style`/`--grout-color` + sufiks batch tylko przy niedomyślnych; GUI: 2 menu, działają też w preview
- Determinizm: faza/jitter z crc32 kwantowanych końcówek segmentu (zero RNG); amplitudy/okresy skalują się z szerokością poziomu (presety spójnie przeskalowują wzór); segmenty krótsze niż okres degradują do cienkiej kapsuły solid (gęste szwy łukowe zostają czystą linią)
- Narzędzie propozycji stylów: `gen_grout_style_proposals.py` (NIE mylić z `gen_grout_proposals.py` 2026-07-05 = poziomy L1/L2/L3)

[2026-07-19] **Rodzina puzzle (sprint P) + E4 + E5 — rejestr 43→53** (commity `be64bdc`, `174a5a3`, `667bcf7`; wcześniej E3 `def6513`/`3c10f0e`)
- **Puzzle** (`puzzle_classic`/`puzzle_ribbon`/`puzzle_hex`, profil die-cut wg zdjęć referencyjnych usera — decyzja: jeden profil dla całej rodziny, NIE osobny kształt): tab = WSPÓLNA polilinia per krawędź (pierwsze-widziane końcówki kanoniczne, crc32 klucza → kierunek+jitter, zero RNG) ⇒ partycja dokładna z konstrukcji; tab oddaje sąsiadowi to co zabiera ⇒ średnie pole = base_s². Łuki: STAŁY krok kątowy 9° (strzałka ~0,003·R < 0,1 px w każdej realnej skali; pułapka truchet_hex dotyczyła stałego kroku CIĘCIWY). Bramka ribbon-vs-classic: CV odległości NAROŻNIKÓW (0 vs 0,046; narożniki nie centroidy — jitter tabów nie zamazuje; translacyjnie niezmienna)
- **E4**: `dragon` (twindragon order 8, brzeg 246 wierzchołków przez kasowanie krawędzi + najostrzejszy skręt w lewo; `(1+i)^8=16` ⇒ krata zwykła 16 jednostek, pole DOKŁADNIE base_s²; determinizm: tylko hashe int/int-tuple), `koch_island` (Minkowski depth 2 na CZYSTYCH INTACH — tabela kierunków zamiast cmath.exp; period=4^depth NIE bbox), `koch_snowflake` (2-rozmiarowa, bilans pól DOKŁADNY 1:3, Rb=0,6937·base_s; głębokość STAŁA=4 — depth 5 = ~1,2 GB poligonów @16K, odrzucony budżetem A1)
- **E5**: `gereh` (4.8.8 → 16 latawców/ośmiokąt + ROMBY w lukach; same czworokąty = odrębność od trunc_square; T-junctions ośmiokąt-kwadrat legalne), `rosette` (3.12.12 → 36 komórek/dwunastokąt + trójkąty międzywęzłowe kotwiczone ANALITYCZNIE jako centroidy trójkątów kraty — pułapka odfiltrowanego centrum niemożliwa z konstrukcji)
- Wszystko: goldeny ×2 cross-process (PYTHONHASHSEED=1), schematy Z SILNIKA (`gen_puzzle_schemes.py`/`gen_e4_schemes.py`/`gen_e5_schemes.py`), GUI/CLI przez `shape_names()`. Testy 442→540. Cel całości = **59** (56 puli + 3 puzzle)

[2026-07-20] **E6 + E7 — REJESTR = 59/59, CEL OSIĄGNIĘTY** (commity `b407d53`, `e2c8a91`, `494772b`, `280abf2`; 540→594 testy)
- **E6 `scales`** (rybia łuska): okręgi `r=base_s/√2` na siatce szachownicowej (`dx=2r, dy=r`), komórka = dysk MINUS dwa dyski wiersza niżej; przecięcia dokładnie w `(±r,0)` i `(0,r)`. PARTYCJA Z KONSTRUKCJI: brzeg złożony wyłącznie z ĆWIARTEK łuku pobieranych przez `center(i,j)` SĄSIADA — nigdy przez dodanie `r` do własnego środka (`c_y+r` ≠ `(j+1)*r` bit-w-bit!); łuk wygryziony = bit-w-bit ćwiartka kopuły sąsiada. Pole komórki `2r²` = wyznacznik kraty (niezależny cross-check partycji). `_join_arcs` (NOWY, współdzielony) dedupuje kolejne duplikaty na złączeniach łuków.
- **E6 `nautilus`**: biegun POZA kadrem `(-0,55·cx, -0,30·cy)` = wzorzec „dobrego środka" rozwiązany konstrukcyjnie — najbliższy punkt kadru to zawsze róg `(0,0)`, więc pasmo promieni ograniczone Z DOŁU i cap-fan zbędny. `g = 1 + 2π/nsec` (relacja sunburst; schemat `g=1,16` przy `nsec=40` to DOKŁADNIE ona ⇒ port, nie przeprojektowanie). `r_ref = √(r_near·r_far)·1,15`. Rozrzut rozmiarów MONOTONICZNY 4,4×. Bramka odrębności vs `sunburst`: odległość NAJMNIEJSZEJ komórki od środka kadru w półprzekątnych (0,97 vs 0,22).
- **E6 `rosette_fractal`** (aloes) — **BŁĄD SCHEMATU ZŁAPANY**: patrz „Rozwiązane problemy" [2026-07-20]. Partycja FORMALNIE zweryfikowana; `nseg` liczone SYMETRYCZNIE (średnia geometryczna promieni), żeby sąsiad idący szwem wstecz dostał ten sam podział. Rozrzut ograniczony 1,5–1,8× (RESETUJE się przy każdym podwojeniu — kontrast z monotonicznym nautilusem).
- **E7 sierpiński ×3** (`sierpinski` depth 3 + stagger S/2, `sierpinski_d` szachownica `(t+r)%2` na CELOWO niestaggerowanej siatce, `sierpinski_carpet` depth 4): KAŻDY trójkąt/kwadrat jest komórką — fraktal czyta się przez SKALĘ ZDJĘĆ, nie przez pustkę. Carpet: dziury dopiero od poziomu 2 (poziom 1 = rozmiar tła, zniknąłby po podstawieniu zdjęć). PRZYCINANIE REKURENCJI obowiązkowe: dywan emitował 42 129 komórek dla ~155 dotykających kadru 800×600 → 167 po odcięciu podkwadratów poza kadrem (`_tri_outside` analogicznie dla trójkątów). 16K: 34–41k komórek, 0,0 s.
- Wszystko: goldeny ×12 cross-process, schematy Z SILNIKA (`gen_e6_schemes.py`, `gen_e7_schemes.py`), surowa ścieżka CLI zweryfikowana dla wszystkich 6 (punkt 8 checklisty planu)

---

## Rozwiązane problemy

[2026-08-20] **Szum w niebie NAPRAWIONY — pasmo wierności koloru dla kary antypowtórzeniowej** (commit `4b675cc`; 574 testy; zamyka punkt ① z 2026-07-26)
- **Wada:** kara `used_counts**2 * freq_penalty * 0.001` była NIEOGRANICZONA, więc licznik w końcu przerastał dowolną różnicę odległości w top-K. W płaskim niebie spychało to wybór poza wszystkie pasujące kafle, aż do ciemnych.
- **Naprawa:** kara dostaje budżet `freq_tolerance_de` (ΔE na komórkę cechy, domyślnie 2,0) wokół najlepszego dopasowania w sektorze; przestawia kandydatów WEWNĄTRZ pasma, nigdy nie wypromuje kandydata spoza.
- ⚠ **Pasmo MUSI być absolutne, nie ułamkiem `d_best`** (plan zakładał względne — pomiar to obalił). Względne zawodzi po OBU stronach: zapada się przy dopasowaniu niemal dokładnym (`d_best`→0 wyłącza karę; zmierzone: pasmo 10% objęło 2 kafle z 41) i **rozdyma się tam, gdzie dopasowanie jest słabe** — dając karze najwięcej swobody dokładnie w obszarach, które ma chronić.
- **Przelicznik ΔE→dystans WYPROWADZONY:** cecha to 5×5 średnich LAB z `L/100` ⇒ jednorodna różnica ΔE jasności to `sqrt(25)·ΔE/100 = ΔE·0,05`. Por. wpis o `rosette_fractal` — ta sama klasa dyscypliny.
- ⚠ **Nasycenie miękkie `w·p/(p+w)`, NIE twarde `min(p,w)`:** twarde obcięcie parkuje wszystkich nadużywanych kandydatów na tym samym wyniku, a remis po indeksie karmi wtedy w kółko jeden kafel — odtwarza wadę, którą kara zwalcza.
- ⚠ **`dists_w_*` (ścieżka maskowana) to KWADRATY** odległości ważonych, a GEMM zwraca prawdziwe euklidesowe — próg dodaje pasmo liniowo i podnosi do kwadratu.
- **Wynik @8K:** ciemne 6,52%→1,30%, sky_std 10,93→5,23, dE 17,34→14,21, max powtórzeń 218 (fp=0)→118. **Cel z planu (szum na poziomie fp=0 PRZY max≲10) NIEOSIĄGALNY tym pokrętłem — to granica biblioteki**, nie scoringu (~800 kafli w wąskim ΔE od koloru nieba). Zdobycz jest jakościowa: `freq_penalty` działał BINARNIE, teraz jest ciągłe pokrętło szum↔powtarzalność.
- ⚠ **Drugi, niezależny mechanizm sięgania po zły kafel:** `forbidden_indices` (+1e6, zakaz sąsiedzki). Pasmo go NIE ogranicza — to on daje resztkowe 0,72% ciemnych przy karze całkiem wyłączonej. Przy małej bibliotece wyczerpuje dobre kafle (pułapka przy fixture'ach testowych).
- **Fixture goldenów przypina `freq_tolerance_de` jawnie** ⇒ strojenie domyślnej nie unieważnia hashy.

[2026-08-20] **Cull `bloom` + rename `escher_hex` — goldeny SĄ instrumentem audytu kolateralnego** (commit `68c8b33`; 568 testów; zamyka ⑤ i ⑦ z 2026-07-26)
- `bloom` USUNIĘTY (rejestr 50→**49**), `escher_lizard` → **`escher_hex`** (sama nazwa, geometria nietknięta), `_LUCAS_ANGLE` usunięty. Parametr `angle` w `_vogel_points`/`_graded_sunflower` ZOSTAJE — nazywa stałą definiującą kratę, usuwanie ruszałoby kod 5 ocalałych kształtów bez zysku.
- **Kryterium przyjęte na stałe:** *kształt zasługuje na slot, jeśli różni się w MOZAICE, nie na diagramie.* `bloom` przechodził bramkę odrębności na GEOMETRII (kąt Lucasa to realna różnica) i mimo to był duplikatem pod zdjęciami — **bramka geometryczna nie wystarcza**.
- **Audyt kolateralny: 88/88 goldenów BIT-W-BIT** ⇒ regeneracja zbędna. Przy cullu 59→50 trzeba było domykać graf AST; teraz goldeny pokrywają CAŁY rejestr, więc `python -m src.tools.regen_goldens --check` z raportem „BIT-IDENTICAL" jest gotowym dowodem braku szkód.
- ⚠ **PNG schematu musi iść razem z nazwą** — GUI szuka `assets/shape_schemes/<nazwa>.png` po nazwie kształtu, inaczej „no scheme preview".
- ⚠ **Konwencja narzędzi propozycji = ZERO SIEROT** względem rejestru (precedens `kepler_ty`): wyciąć generator + udokumentować powód w nagłówku.
- **Liczniki do aktualizacji przy KAŻDEJ zmianie rejestru:** README EN/PL (tabela 5 rodzin — nagłówki `(N)` muszą zgadzać się z liczbą wypisanych nazw, suma = rejestr; + 3 wzmianki „N tilings"), `docs/index.html` (title, meta description, OG, twitter, JSON-LD, `<h2>`, lista alfabetyczna). Weryfikować skryptem przeciw `SHAPE_MODES`, nie okiem.

[2026-07-26] **Ząbkowanie krawędzi `kites` — i pułapka TRZECH kopii tego samego przebiegu siatki**
- **Wada:** kafle odrzucane po CENTROIDZIE w kadrze zamiast po PRZECIĘCIU bbox z kadrem → każdy latawiec na brzegu ze środkiem poza kadrem znikał w całości. Pomiar (1200×900, base_s=75, maska FLOAT ss=4): **2,349% kadru bez pokrycia** — pasmo dolne 12,57%, prawe 9,09%, górne 6,69%; lewa czysta TYLKO przez fazę siatki (`cx = 1.5·s·q` kładzie środek heksagonu dokładnie na x=0, stąd złudzenie, że wada dotyczy tylko prawej/dołu). Po fixie 0,000% na wszystkich pasmach.
- **META-LEKCJA (najważniejsza):** pierwszy fix trafił tylko w `_gen_kites` i **nie zmienił ANI JEDNEGO piksela renderu** — golden `kites` został bit-w-bit ten sam. To NIE było potwierdzenie zgodności, tylko dowód, że dotknięty kod **nie jest ścieżką produkcyjną**. `kites` był jedynym kształtem poza generycznym dispatchem polygon i miał TRZY kopie przebiegu `(q,r,k)`: `_gen_kites`, dedykowana gałąź w `_do_render`, `_grout_cells_kites`. Produkcja renderowała przez kopię nr 2. Ta sama meta-lekcja co [2026-07-06] make_dzi (skrypt pomiarowy ≠ produkcja) i [2026-07-13] grout AA (tool propozycji rasteryzował SS=2, silnik 1:1).
- **ODRUCH:** przy zmianie geometrii kształtu NAJPIERW `grep` nazwy kształtu po `engine_smart.py` — jeśli występuje poza `SHAPE_MODES`, istnieje osobna gałąź. Nie łataj kopii: wyciągnij jeden przebieg (tu `_kite_lattice()` + modułowy `_kite_poly()`) i podepnij wszystkich konsumentów. Bramka testowa porównuje wtedy LICZBY komórek `generator == lattice == grout`, zamiast powielać kod, który miała sprawdzać.
- **Instrument:** formalny test partycji — suma pól przyciętych = **1 080 000,0 = DOKŁADNIE pole kadru**. Jedna liczba łapie i niedobór (dziury), i nadmiar (podwójne malowanie); mocniejszy niż test rastrowy. Sweep pokrycia po WSZYSTKICH 53 kształtach polygon: `kites` był JEDYNYM z wadą (reszta 0,000%, `girih` 0,011% — znana otoczka).

[2026-07-27] **Audyt collateral damage po cullu 59→50 — zero regresji, instrument = domknięcie AST + A/B geometrii**
- **Pytanie:** usunięcie 9 kształtów (`077fec3`, 2026-07-26) mogło cicho uszkodzić PRZEŻYŁE kształty dzielące z nimi helpery — „testy przechodzą" tego nie dowodzi, dowodzi tylko braku `NameError`.
- **Instrument:** domknięcie tranzytywne grafu wywołań (AST) na wersji SPRZED usunięcia — dla każdego kształtu policzony pełny zbiór helperów, przecięty ze zbiorem usuwanych. Wyszło 14 zagrożonych kształtów: `_sun_arc` → `nautilus`/`scales`/`truchet`/`truchet_hex`/`voderberg`; rodzina Voronoi (`_emit_cells`/`_voronoi_cells`/`_lloyd_relax`/`_vogel_points`/`_graded_sunflower`) → `bloom`/`pebbles`/`phyllotaxis`/`voronoi`/`sunflower_grande`/`sunflower_grande_inverse`/`sunflower_rings`/`sunflower_soft`; `_sierpinski_cells`/`_tri_outside` → `sierpinski`.
- **Wynik: zbiór faktycznie usuniętych helperów (24) pokrył się CO DO JEDNEGO ze zbiorem „wyłączne dla usuniętych kształtów"** — cięcie było chirurgicznie poprawne. A/B geometrii (stary moduł załadowany obok nowego przez `importlib.util.spec_from_file_location`, prefiks `src.` obowiązkowy — inaczej padają importy względne) na 14 kształtach × 3 kadry dało **42/42 strumienie wielokątów bit-w-bit identyczne**. Pokrycie kadru (maska FLOAT ss=4 + shoelace): pole/kadr=1,0000 wszędzie, dziury 0,000% (poza `nautilus` 0,008%/`voderberg` 0,012% — subpikselowa kwantyzacja łuków, znany precedens).
- **Jedyna realna wada:** docstring `_sun_arc` wymieniał 4 konsumentów zamiast 5 (brakował `truchet_hex`) — ten sam mechanizm, który przy poprzednim usunięciu wywalił 25 testów. Naprawiony + dopięty `TestSunArcConsumers` (liczy konsumentów z AST, porównuje z docstringiem), zweryfikowany MUTACYJNIE (celowe usunięcie nazwy z docstringa czerwieni test).
- **PUŁAPKA NARZĘDZIOWA:** dzielenie pliku na bloki po `^def` (regex) przypisuje komentarze LEŻĄCE MIĘDZY funkcjami do funkcji powyżej → fałszywe „CHANGED". Używać `ast.get_source_segment`, nigdy regexa, do diffowania funkcji.
- `ShapeSpec.generator` bywa `None` (legacy grid: `square`/`hexagon`/`triangle`/`romb`/`brick_wall`/`rectangle_3x1` — rasteryzuje je gałąź grid w `_do_render`, nie generator) — każdy przebieg po `SHAPE_MODES` musi to przeskoczyć.
- 567 testów przechodzi (565+2). Commit `e4c0153`.

[2026-07-21] **Trzy wady wykryte dopiero na realnym renderze 8K** (input airshow, edge-aware, grout thin)
- **Czarny padding częściowego cropu krawędziowego zatruwa dopasowanie LAB** → ciemne slivery na offsetowych krawędziach. `brick_wall` przesuwa co drugi rząd o `base_s//2`, więc przy lewej krawędzi powstaje pół-cegła `c=-1` (x od −38); widoczne 37 px, reszta kanwy była wypełniana `(0,0,0)` PRZED liczeniem cechy → mediana leci w czerń → dopasowany ciemny kafel, odcina się od nieba. `square` nie ma wady (skrajne kafle w pełni poza kadrem → pomijane `safe[2]<=safe[0]`). FIX: mean-fill reszty kanwy kolorem średniej cropu + paste w PRAWDZIWEJ pozycji `(safe[0]-px, safe[1]-py)` (branch grid + hexagon_romb). `_polygon_sector`/kites/spectre już pastowały z poprawnym offsetem — nietknięte. Zmienia dopasowanie krawędzi → goldeny `square`+`hexagon_romb` zregenerowane (4 hashe, udokumentowane w test_golden_shapes.py)
- **Grout hierarchiczny rysuje stopniowane L1<L2<L3 NAWET przy „each tile" (poziom 1)** — `square`/`hexagon` pokazywały granice grup 3×3/9×9 i 7-kwiaty jako ciężkie linie, mimo że user wybrał poziom 1. `min_level` tylko UPUSZCZA poziomy poniżej; przy 1 nic nie upuszcza, więc L2/L3 (grubsze) widoczne. FIX w `_apply_grout`: przy `min_level==1` rysuj UNIFORM (wszystkie szwy = szerokość L1), jak flat shapes i jak opisuje GUI „1 = every tile"; gradacja zarezerwowana dla jawnego poziomu ≥2. META: schemat/preview groutu nie ujawnia tego — trzeba realnego kadru
- **Presety grubości wybrane A/B na realnym 8K:** thin/medium/thick L1 = **1/3/5 px** @ base_s=75 (poziom 1 uniform). `base_s = int(100·tile_scale)` = 75 NIEZALEŻNIE od rozdzielczości ⇒ wygląd groutu względem kafla identyczny na 2K/4K/8K/16K; porównanie szerokości można robić przy tanim 4K i jest wierne 8K. `draw_grout` wspiera float szerokości przez `round(wd·ss)` (ss=4), ale `scale_widths` zaokrągla do int. Narzędzie porównawcze: baza render RAZ (grout=None → tint+blend bez groutu), nakładka 1..10 px na kopiach; wycinek Z NIEBA (kontrast) + montaż ≤2000 px (żeby podgląd nie pomniejszył 1 px)

[2026-07-19] **Parzystość scanline'a Pillow + drabinka instrumentów pokrycia** (sprinty P/E4/E5)
- **Zduplikowane KOLEJNE wierzchołki** (złączenia łuk/ramię w profilu tabu) łamią parzystość scanline'a `ImageDraw.polygon`, gdy leżą na linii skanowania: fill gubi cały 1-2 px WIERSZ wielokąta (784 px pasów @800×600, także w maskach aa=4 renderu — to było źródło „prostej cięciwy" w pierwszym renderze propozycji die-cut). Fix: dedup `[1:]` przy sklejaniu segmentów profilu. ZAWSZE dedupować złączenia polilinii
- **Raster binarny 1:1 to ZŁY instrument pokrycia dla KRZYWYCH szwów** (wielosegmentowe polilinie): zgłasza dziury przy dowodliwie dokładnej partycji. Drabinka instrumentów: (1) krawędzie proste → raster 1:1 holes==0; (2) krzywe szwy współdzielone → formalny test partycji (classify_edges, 0 niesparowanych wewnętrznych; dowodzi też pokrycia) + pokrycie FLOAT na ścieżce masek silnika (ss=4+BOX, próg 0,45; kalibracja: wdrożony voderberg = 0,502 min); (3) szwy nieparujące się z konstrukcji (koch_snowflake — aproksymacje wspólnej granicy z różnych baz) → tylko FLOAT + bilans pól. UWAGA: formalny test partycji NIE nadaje się dla kształtów z legalnymi T-junctions (gereh) — flagowałby je jako niesparowane
- **Bug schematu `gereh` złapany bramką pokrycia**: propozycja rysowała lukę 4.8.8 jako kwadrat OSIOWY (`_reg_poly` faza π/4) — nakładki na rogach + trójkątne dziury (11k px), niewidoczne pod konturami PNG; prawdziwa luka to ROMB o wierzchołkach na osiach. Wizualna akceptacja schematu NIE dowodzi partycji („schemat ≠ silnik" po raz kolejny)

[2026-07-20] **Stała schematu poprawna LOKALNIE, błędna GLOBALNIE — `rosette_fractal` m=3** (sprint E6)
- Schemat zaszywa `m=3` pierścieni na podwojenie sektorów z `g=2^(1/m)`. To trzyma kwadratowe komórki **wyłącznie przy N=24**. W obrębie okresu `N` jest stałe a `r` się podwaja, więc głębokość promieniowa `r(g-1)` też się podwaja; przy podwojeniu `N` połowi rozmiar STYCZNY, ale głębokości nie rusza ⇒ **PROPORCJA KOMÓRKI PODWAJA SIĘ CO OKRES**: 0,50 → 0,99 → 1,99 → 3,97 → … → 63,5 po 8 podwojeniach. Kadr 16K to ~5 podwojeń = 16:1 slivery przy brzegu, bezużyteczne jako kafle
- NIEWIDOCZNE na schemacie 720 px (ledwie jedno podwojenie) — ten sam mechanizm co bug `gereh` z E5: schemat kłamie w małej skali
- FIX bez zmiany konstrukcji: `m` WYPROWADZONE z bieżącego N, `m = round(ln2 / ln(1 + 2π/N))` — relacja kwadratowej komórki z `sunburst` (`g = 1 + 2π/N`) zrzutowana na siatkę podwojeń. Proporcja 0,79–1,00 przy każdym N. **`m=3` wypada naturalnie przy N=24**, czyli wartość schematu okazała się poprawna, ale tylko lokalnie — stała stała się konsekwencją. Bramka porównuje obie wersje wprost
- **META-LEKCJA:** stała liczbowa w schemacie/propozycji to często wynik dopasowania do JEDNEJ skali. Przed portem do silnika sprawdź, czy da się ją WYPROWADZIĆ z warunku, który stała miała spełniać — i czy warunek trzyma przy skalowaniu kadru. Por. „stała liczba kafli niezależna od rozdzielczości = bug" (E2 Voronoi)

[2026-07-20] **T-junctions WBUDOWANE — czwarta klasa w drabince instrumentów** (sprint E7)
- Rodzina sierpińskiego: dziura to JEDNA komórka, a otaczające ją trójkąty gasketu są podzielone własną rekurencją ⇒ krawędź dziury poziomu `d` styka się z `2^(d-1)` segmentami. T-junctions są tu ZAMIERZONE (dziura = jedno duże zdjęcie, o to chodzi w kształcie). Formalny test partycji = ZŁY instrument, oblałby poprawny kształt
- Ale wszystkie krawędzie proste ⇒ pokrycie **DOKŁADNE: min = 1,000** (zero dziur i zero pyłu szwów). To mocniejszy wynik niż próg 0,45 dla kształtów krzywych — dla prostokrawędziowych żądaj `min == 1.0`, nie progu
- **Rozdzielaj tezy przed napisaniem docstringa:** twierdziłem, że stagger S/2 „utrzymuje partycję dokładną" — było 102 niesparowane szwy. Teza o WYRÓWNANIU była słuszna (S/2 = 4 z 8 podsegmentów), ale wniosek fałszywy, bo 102 pochodzi od dziur. Pomiar rozdzielający: brak staggera i S/2 dają TAK SAMO 102, a S/3 i S/5 dokładają ~20. Nie naciągaj progu — znajdź ŹRÓDŁO liczby

---

## Aktywne TODO (długoterminowe)

[2026-08-15] **Szum w niebie ROZSTRZYGNIĘTY pomiarowo — to `freq_penalty`, nie blend/tint** (→ NAPRAWIONE 2026-08-20, patrz „Rozwiązane problemy")
- **Sweep blend/tint = ślepa uliczka.** `square` @2K, blend ∈ {0,10·0,20·0,30} × tint ∈ {0,10·0,25}: monotonicznie, BEZ kolana. Maksimum dozwolonego zakresu (0,30/0,25) daje `sky_std` 6,43 przy 8,89 dla 0/0 — tylko **−28%** i wciąż **4,9× oryginał** (1,307). Nie wracać do strojenia blend/tint jako lekarstwa na szum.
- **Grout zanieczyszczał metrykę.** `draw_grout` rysuje PO blendzie jako twarda nakładka (świadoma decyzja, komentarz w `_do_render`), więc czarne linie L\*≈0 w niebie L\*≈69 wchodzą wprost do `sky_std`: grout „thin" = **~32% wariancji** płata (8,891 z groutem vs 7,352 bez, przy identycznych ustawieniach). Wszystkie 50 mozaik z analizy 26.07 renderowano z groutem ⇒ teza „wada wspólna dla wszystkich kształtów" była częściowo pomiarem fug. **Każdy pomiar jakości dopasowania rób z `grout_preset=None`.**
- **Winowajca: `freq_penalty`** (człon `used_counts**2 * fp * 0.001`). W płaskim niebie sąsiednie sektory mają niemal te same cechy ⇒ tę samą listę top-50; kara kwadratowa + twardy zakaz `forbidden_indices` spychają wybór w dół listy, aż silnik bierze kafle ciemne. Bez groutu i post-processingu: `sky_std` 7,352 (fp=30) → 5,048 (fp=10) → 3,644 (fp=0) @2K.
- **PUŁAPKA SKALI — wnioski z 2K NIE PRZENOSZĄ SIĘ.** @8K (8034 komórek zamiast 546) fp=10 daje **−1,6%** (10,933 → 10,758), czyli nic; dopiero fp=0 schodzi do 3,958 (2,94× oryginał, ciemne piksele 6,52% → 0,72%, dE 17,34 → 13,33), ale kosztem powtarzalności: max użyć jednego kafla **218** z 8034 i top-10 kafli = 17,3% wklejeń (przy fp=30: max 5, top-10 = 0,6%). Efekt jest binarny, nie ciągły — przy małej liczbie komórek liczniki nie zdążą wystrzelić i kara wygląda na łagodną. **Nigdy nie kalibruj `freq_penalty` na 2K.**
- **Kierunek naprawy (NIEwdrożony, do decyzji usera):** nie strojenie stałej, lecz **ograniczenie kary tolerancją** — stosować ją tylko wśród kandydatów w paśmie ΔE od najlepszego, żeby nie mogła wypchnąć wyboru poza próg wierności koloru. Alternatywy: większe top-K dla płaskich rejonów, skalowanie kary liczbą komórek/rozmiarem biblioteki. Dotknie WSZYSTKICH renderów ⇒ regeneracja goldenów.

[2026-08-15] **Widoczność w Google — `docs/` przebudowane, reszta po stronie usera (`PLAN_SEO.md`)**
- Zweryfikowane empirycznie: repo nie wychodzi w wyszukiwaniu. Przyczyny wg wagi: brak backlinków (~80%), strona Pages była samą aplikacją OSD (zero tekstu do indeksacji), osierocone `posts/*.md`, brak sitemapy i zgłoszenia w GSC.
- Zrobione: `index.html` = strona lądowania z prozą + pełny head (canonical/OG/JSON-LD); przeglądarka OSD → **`viewer.html`** (adres główny NIE jest już przeglądarką — linki w README EN+PL przestawione); wpisy jako HTML z `hreflang`; `sitemap.xml`; `style.css`; `img/` z `og-cover.jpg`.
- **PUŁAPKA:** `docs/robots.txt` leży pod `/Neural-Mosaic/robots.txt`, a roboty czytają wyłącznie `piotr1686.github.io/robots.txt` ⇒ **jest ignorowany**. Nic na tym nie tracimy (domyślnie i tak wszystko dozwolone), ale nie liczyć na dyrektywy z tego pliku.
- Przy okazji domknięty backlog: tabela kształtów w README EN+PL (9 pozycji przy rejestrze 50) → sekcja „Tile shapes"/„Kształty kafelków", 5 rodzin, 12+15+6+6+11=50.
- Zostało dla usera: weryfikacja Google Search Console plikiem HTML (dla `github.io` metoda DNS niemożliwa), zgłoszenie sitemapy, backlinki (gotowe teksty Show HN / r/generative / r/Python / dev.to w `PLAN_SEO.md` — **nic nie opublikowane**).

[2026-07-26] **Analiza krytyczna 50 mozaik 8K — zmierzone wady** (①⑤⑦ ZAMKNIĘTE 2026-08-20; ②③④⑥ nadal otwarte, NIEZATWIERDZONE)
- ✓ **① ZAMKNIĘTE 2026-08-20** (`4b675cc`, pasmo ΔE — patrz „Rozwiązane problemy"). ~~Szum w płaskim niebie = NAJWIĘKSZA dźwignia.~~ Odchylenie L* w płacie nieba: oryginał **1,29**, mozaiki **6,3–9,9** (5–8×). Wspólne dla WSZYSTKICH kształtów ⇒ przyczyna leży w dopasowaniu/bibliotece, nie w geometrii. Najgorsze: `koch_snowflake` 9,87, `romb` 8,91, `dragon` 8,35. Najlepsze: `truchet` 6,31, `hexagon_romb` 6,44, `moire` 6,50. **Rekomendacja: nie zgadywać** — sweep `square` @2K po blend ∈ {0,10 · 0,20 · 0,30} × tint ∈ {0,10 · 0,25}, metryka gotowa, zero zmian w kodzie. Dopiero jeśli blend nie pomoże → podejrzany `freq_penalty` (wymusza różnorodność tam, gdzie chcemy jednorodności).
- **② Kształt jest niewidoczny przy oglądaniu całości.** Rozpiętość wierności całego zestawu to dE 11,3–12,6 (mediana 12,0) — przy dopasowaniu do ekranu wszystkie 50 czytają się jak ta sama fotografia. Wybór kształtu to oś **czysto estetyczna, działająca tylko przy 100%**. Konsekwencja dla galerii: wizerunkiem pozycji ma być crop 1:1 albo wymuszony zoom (DZI), NIE miniatura całej mozaiki.
- **③ Ziarno rozjeżdża się między kształtami przy tych samych ustawieniach.** Rozdziel dwa przypadki: (a) **jednorodne, ale źle wyskalowane** — `kites` 0,43, `truchet` 0,32, `koch_snowflake` 0,33, `poincare` 0,34 przy `p90/p10 ≈ 1,0`; naprawia to JEDNA liczba per kształt (pole `scale` w `ShapeSpec`); (b) **wewnętrznie bimodalne** — `trunc_hex` (p90/p10 = 25,9), `rhombitrihex`, `weave`, `pebbles`; tu żaden skalar nie pomoże, dwa rozmiary komórek TO JEST ten kształt (4.8.8 = ośmiokąt + trójkąt wypełniający). **UWAGA metodologiczna:** mediana pola to ZŁY statystyk (dla `trunc_hex` ląduje na mikroskopijnych trójkątach, choć oko widzi ośmiokąty — stąd alarmujące 0,04). Właściwy: **średnia ważona polem `Σa²/Σa`** = pole komórki pod losowym pikselem. Przemierzyć przed jakąkolwiek kalibracją.
- **④ `sierpinski`: największa komórka = 16× mediany.** Zdjęcie rozciągnięte na trójkąt ~600 px w płaskim niebie czyta się jako pusty klin. Hierarchia rozmiarów to TOŻSAMOŚĆ tego kształtu, więc nie wycinać — ewentualnie ograniczyć („komórka > 6× mediany dostaje własną rekurencję"), ale **najpierw A/B @8K, nie commit w ciemno**. Kontekst: usunięty `sierpinski_d` istniał dokładnie po to (`_sierp4` ograniczał największą dziurę do połowy) i został odrzucony estetycznie — różnica w tym, że tam było to osobnym KSZTAŁTEM, tu byłoby ograniczeniem jakości istniejącego.
- ✓ **⑤ ZAMKNIĘTE 2026-08-20** (`68c8b33`, rename na `escher_hex`). ~~`escher_lizard` nie wygląda jak jaszczurka~~ — przy 1:1 to postrzępiony plus/gwiazda. **Rekomendacja: zmienić NAZWĘ, nie geometrię** (`escher_hex` / `interlock`). Kafel działa jako splatający się nieregularny wzór; nie działa nazwa, która obiecuje coś, czego nie ma. Prawdziwa sylwetka = ręczne zaprojektowanie deformacji sześciokąta + dowód, że nadal teseluje (godziny, niepewny wynik); to, że pozycja leży w backlogu od dawna, samo jest informacją.
- **⑥ Grout wg obwodu — WYCOFANA sugestia, nie robić.** Stała szerokość jest fizycznie uczciwa (prawdziwa fuga ma stałą szerokość niezależnie od kształtu płytki), a skalowanie obwodem zrobiłoby z granic Kocha linie włoskowate i zabiło efekt. Realny problem jest węższy: preset „thin" sugeruje porównywalny wygląd i nie dowozi. Tanie rozwiązanie: policzyć udział czarnego tuszu per kształt i te powyżej ~15% renderować w batchu z **grout=off** — decyzja przenosi się do drivera, zero zmian w silniku.
- ✓ **⑦ ZAMKNIĘTE 2026-08-20** (`68c8b33`, `bloom` usunięty). ~~`bloom` vs `phyllotaxis`~~ — różnią się WYŁĄCZNIE kątem dywergencji (Lucas vs złoty ⇒ inne ramiona parastych), co jest widoczne tylko na schemacie z kolorowanymi komórkami; w mozaice każda komórka to inne zdjęcie, więc struktura ramion znika. Liczby: dE 11,47 vs 11,44, szum 7,61 vs 7,11 — w granicach szumu pomiaru. **Rekomendacja: usunąć `bloom`.** Kryterium do przyjęcia na stałe: *kształt zasługuje na slot, jeśli różni się w MOZAICE, nie na diagramie.*

[2026-04-18] **feature/semantic-clip — CLIP semantic tile matching**
- Branch: `feature/semantic-clip`
- Cel: zamiana 3×3 LAB features w SmartEngine na CLIP embeddings (semantyczne dopasowanie)
- Status: branch UTWORZONY, ale implementacja CLIP jeszcze nie zaczęta
- Decyzja architektoniczna do podjęcia: rozszerzyć SmartEngine czy nowy SemanticEngine?

---

## Odrzucone podejścia

[2026-07-26 / 2026-08-20] **Selekcja kształtów — 10 USUNIĘTYCH CAŁKOWICIE, nie proponować ponownie** (9 przy cullu 59→50, + `bloom` 2026-08-20)
- Werdykt usera po przeglądzie 59 mozaik 8K. Wycięte z projektu (generatory, `SHAPE_MODES`, goldeny, testy, `assets/shape_schemes/`, wpisy w `src/tools/gen_*_schemes.py`): `rhombs_funnel`, `rhombs_nopole`, `rhombs_star`, `sierpinski_carpet`, `sierpinski_d`, `sunburst`, `sunflower_disc`, `sunflower_grande_xl`, `sunflower_grande_soft`. **REJESTR = 50.**
- Wybór potwierdzony obiektywnie: 3 odrzucone `rhombs_*` miały NAJGORSZĄ wierność wobec oryginału (dE 15,1 / 15,2 / 15,7 przy medianie 12,0 w całym zestawie).
- **PUŁAPKI usuwania kształtu** (promień rażenia większy niż nazwa sugeruje): `_sun_arc` mimo nazwy od `sunburst` jest współdzielony przez `scales`/`nautilus`/`voderberg`/`truchet` — usunięcie razem z sunburstem wywaliło **25 testów** w kształtach nietkniętych. Cała maszyneria log-spiralna (`_log_quads`/`_log_mesh`/`_bridge`/`_rosette`/`_emit_polys`/`_rh_*`) była wyłącznie pod `rhombs_*` → 234 linie martwego kodu do usunięcia. `_sierp4` osierocony po `sierpinski_d`. `src/tools/gen_e7_schemes.py` importuje generatory wprost → crash na imporcie, jeśli nie zaktualizowany.
- Kolejność `SHAPE_MODES` zmieniona na **ALFABETYCZNĄ**; nic od niej nie zależy (każdy konsument szuka nazwy w słowniku). Dropdown kształtów w GUI otwiera się w **2 kolumnach** (`_spread_dropdown_columns` w `gui.py`: CTk dropdown to `tkinter.Menu`, wspiera per-wpis `columnbreak`) — 50 pozycji w jednej kolumnie nie mieści się na ekranie.

[2026-07-11] **`_CurvedMask` (osobna maszyneria masek krzywoliniowych) — ODRZUCONY, nie wracać**
- PLAN_SHAPES zakładał `_CurvedMask` jako warunek truchet ×2 („Tier B"). Zbędny: polygonizacja łuku z sub-pikselową strzałką + `aa=4` w `_LazyMask` daje ten sam wynik rastrowy, a sunburst udowodnił to w produkcji. Szczegóły w sekcji TODO, wpis [2026-07-11b].

[2026-07-05b] **Sunflower — odrzucone przez usera** (nie proponować ponownie):
- `sunflower_classic` (Voronoi Vogela, biegun w środku, złoto) — za blisko istniejącego `bloom`; różnica tylko paletą to za mało
- `sunflower_corner` (biegun w rogu kadru) i `sunflower_field` (2-3 głowy ściśnięte Voronoiem) — odrzucone wprost; generatory usunięte (historia w gicie, commit db6cee5)
- Środki rhombs — 3 nieudane podejścia zanim zapadł werdykt „same romby": 55 klinów z bieguna (slivery 9:1), pierścienie per-krawędź pętli (sunburst — pętla ma 55 krawędzi vs ~34 quady/obwód siatki), pierścienie skalowane pętlą (dziedziczą gwiaździsty zygzak; pętla to gwiazda ±25% promienia)

[2026-07-05] **Fraktale — 3 pomysły SKREŚLONE przez usera po procesie adwersarialnym** (nie proponować ponownie):
- `droste_infinite_zoom` (doklejane poziomy piramidy DZI poniżej natywnej rozdzielczości): make_dzi ładuje jeden raster i resizuje w dół — wymagałoby proceduralnego generatora kafli + custom TileSource w JS; oś „nieskończonego zanurzenia" przejęta przez zoom_movie
- `julia_field_mod` (pole Julii/Mandelbrota moduluje rotację/nasycenie PO doborze kafla): motyw nie przetrwa podmiany kolorów zdjęciami — czyta się jako brud renderu; wróciłby tylko jako sterowanie DOBOREM (inny pomysł)
- `fractal_dimension_match` (wymiar fraktalny box-counting jako cecha dopasowania): na kafelku 75 px fit log-log z 2-3 punktów = szum; plus reindeks ~455k kafli i trzeci duplikowany inwariant wagi obok EDGE_WEIGHT

[2026-06-14] **Refaktory świadomie odłożone po code-review (Fala 4)** — niski zysk / wysokie ryzyko / nieweryfikowalne headless:
- Dedup ~8 handlerów preview smart/typo w `gui.py` (GUI bez testów)
- Unifikacja 4 downloaderów (downloader, downloader_v2, get_mega_pack, get_special_datasets) pod wspólny interfejs
- Centralizacja `res_map`/listy rozdzielczości (zbiór 2K/4K/8K/16K stabilny, drift teoretyczny, przeciąga przez nieotestowane GUI)
- `range()` w `indexer_typo` gubi ostatni codepoint bloków — NIE ruszać: częściowo zamierzone subsety, a CJK już poprawnie półotwarte
- Usunięcie `CACHE_PATH` z `config.py` — ma testy (test_config), nieszkodliwe

---

## Słownik projektu

- **kite** — pojedynczy latawiec (1/6 spłaszczonego heksagonu): [środek, środek_kraw(k-1), wierzchołek(k), środek_kraw(k)]
- **kites** (tryb) — deltoidalne kafelkowanie per-tile: 6 latawców/heksagon, każdy osobnym sektorem (zastąpiło stary `kite`/hat)
- **density** — średnia jasność glifu typograficznego (0=biały, 1=czarny)
- **freq_penalty** — kara za ponowne użycie tego samego kafelka (domyślnie 30.0)

---

## Zewnętrzne zależności i integracje

[2026-04-18] **Fonty w assets/fonts/**
- 105+ plików .ttf, w tym IBM Plex Mono (14 wariantów), JetBrains Mono (variable), Inconsolata (variable)
- Wszystkie na dysku — nie pobieraj nic
- Indeks fontów trzeba przebudować po zmianach: `python -m src.indexer_typo`
