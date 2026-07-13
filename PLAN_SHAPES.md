# PLAN_SHAPES.md — Wdrożenie 20 nowych kształtów kafelków

**Status:** zatwierdzony przez usera 2026-07-02. Kanoniczny plan — zastępuje szkic 7 sprintów z pamięci (`project_10_shapes_plan`).
**Decyzja finalna:** po wdrożeniu WSZYSTKICH kształtów user generuje mozaiki testowe i dopiero wtedy decyduje, które kształty zostają na stałe. Nie usuwać żadnego przed tą decyzją.

## Kontekst dla wykonawcy (Opus)

- Zrobione: Sprint 1a (schematy 19 PNG, commit `2ec504c`), Sprint 1b (GUI: schemat w podglądzie po wyborze kształtu, commit `3a186b7`), schematy 10 kształtów Fable (`assets/shape_schemes/{girih,ammann_beenker,pinwheel,voderberg,cairo,floret,poincare,escher_lizard,gosper,weave}.png` + generator `src/tools/gen_fable_shape_schemes.py`).
- **`src/tools/gen_fable_shape_schemes.py` zawiera działającą, zweryfikowaną wizualnie geometrię wszystkich 10 kształtów Fable — przenoś ją do silnika, nie wymyślaj od nowa.** Dla kształtów Opusa (penrose, voronoi, …) generatorów kodu nie ma (scratchpad z `shapes10.py` przepadł) — geometrię trzeba napisać, wskazówki niżej.
- User zatwierdza PO KAŻDYM sprincie. Po każdym sprincie: testy zielone + commit.

## Sprint 2 — refaktor (WARUNEK WSTĘPNY, zrobić najpierw)

Ekstrakcja wspólnego rdzenia z gałęzi kites/spectre w `_do_render` (`src/engine_smart.py:341`):

1. **Helper `_polygon_sector(target, poly, render_padding, aa)`** — przejmuje: shrink do centroidu, bbox, crop, repaste, `_mean_fill_outside_mask`, `_LazyMask`, feature. Strategia bboxa **od kites** (repaste z offsetem `sb[0]-safe_box[0]`, engine_smart.py:416-423), NIE od spectre (clamp min do 0) — kites'owa poprawnie obsługuje kafelki krawędziowe przy ujemnych współrzędnych.
2. **Kontrakt generatora:** generator kształtu emituje wielokąty w **przestrzeni obrazu (y w dół)**. Flip Y kites (`target_h - ny`, engine_smart.py:405) zostaje wewnątrz generatora kites, nie w helperze.
3. **AA:** nowe kształty `aa=4` (jak spectre). Kites zostaje `aa=1` — podbicie to świadoma decyzja łamiąca bit-repro (regeneracja golden testów).
4. **Rejestr `SHAPE_MODES`** w `engine_smart.py` jako **single source of truth**: `{nazwa: generator}` + metadane (czy wymaga seeda, min-area). GUI dropdown (`gui.py:389`), CLI choices, `make_showcase`, `benchmark` czytają z rejestru (rename kite→kites wymagał edycji 5 plików — nie powtarzać).
5. **Golden testy:** SHA-256 renderów kites + spectre + 2 grid shapes PRZED refaktorem, identyczne PO. Bez zielonych golden nie przechodzić dalej.

## Sprinty 3-8 — kolejność wdrażania kształtów

Pogrupowane po wspólnej maszynerii (nie po autorze propozycji):

| Sprint | Kształty | Wspólny mianownik |
|---|---|---|
| S3 | penrose, ammann_beenker | multigrid de Bruijna (1 implementacja, N=5 i N=4) |
| S4 | pinwheel, gosper, cairo, floret, pythagorean | czyste konstrukcje deterministyczne (substytucja/lattice) |
| S5 | voronoi, phyllotaxis, poincare | zmienna wielkość komórek: seeded RNG + próg min-area |
| S6 | sunburst, voderberg, trunc_square, trunc_hex, rhombitrihex | polar (polygonizacja łuków) + archimedesowe — **ZROBIONE** |
| S7 | girih, escher_lizard | geometria „projektowana" (patrz wyzwania) — **escher_lizard ZROBIONY**; girih został |
| S8 | truchet, truchet_hex, weave | ~~Tier B~~ — **ZROBIONE 2026-07-13**: `_CurvedMask` odrzucony (2026-07-11), weave = partycja, truchet ×2 = zwykłe `polygon` |
| S9 | docs (README EN+PL), montaż zbiorczy 20, mozaiki testowe dla usera | zamknięcie |

## Geometria — konkrety i pułapki per kształt

### S3: multigrid (penrose, ammann_beenker)
- Jedna funkcja `_multigrid(N, gammas, window)`: rodziny linii o normalnych `ζ_k = e^{iπk/N}` (AB, N=4) / `e^{2πik/5}` (Penrose P3, N=5); przecięcie pary linii → romb dualny: `Σ_j K_j(p)ζ_j`, `K_j = ceil(Re(p·conj(ζ_j)) − γ_j)`, wierzchołki z `(m+a)ζ_k + (n+b)ζ_l`, `(a,b)∈{00,10,11,01}`.
- ⚠ **Pułapka (kosztowała iterację):** znak w Cramerze dla `py` — wzorcowa poprawna wersja w `gen_fable_shape_schemes.py::gen_ammann_beenker`.
- ⚠ Zakres `m,n` i filtr `|p|` muszą być większe niż okno renderu (RANGE≈okno+3), inaczej dziury przy brzegach.
- γ offsety: unikać sumy całkowitej (degeneracje); wartości z generatora sprawdzone.
- Penrose: `|k−l|∈{1,4}` → romb gruby, `{2,3}` → cienki; AB: `|k−l|=2` → kwadrat, inaczej romb 45°.

### S4: deterministyczne
- **pinwheel:** podział (prawy kąt w A, |AB|=2|AC|): `F` = rzut A na BC; `M1,M2,M3` = środki AF, FB, AB; dzieci: `(F,A,C), (M1,M3,A), (M2,B,M3), (F,M2,M1), (M3,M1,M2)` (konwencja: (kąt prosty, koniec długiej przyprostokątnej, koniec krótkiej)). Głębokość dobierana do `base_s` (leg ≈ base_s). ⚠ Nowe orientacje pojawiają się bardzo wolno — to normalne, nie bug.
- **gosper:** krawędź → 3 segmenty: mnożniki `r·e^{i·19.1066°}, r·e^{−i·40.8934°}, r·e^{i·19.1066°}`, `r=1/√7`; wyspy na siatce heksagonalnej pointy-top `t1=(√3,0), t2=(√3/2, 1.5)` (×side). Głębokość 2-3 (przy 16K głębokość 3 = ~162 wierzchołki/kafelek — OK dla `ImageDraw.polygon`).
- **cairo:** wierzchołki 4-walentne na kracie int; w kwadracie (i+j) parzystym para pionowa `(i+.5, j+.5∓d)`, nieparzystym pozioma; `d=(√7−1)/6` (równoboczny). 4 pięciokąty na każdy parzysty kwadrat — dokładne wzory w `gen_cairo` (przetestowane, zero dziur).
- **floret:** pentagon-płatek `[(0,0),(1,±1/√3),(1.5,±0.5/√3)]` (dokładnie w `gen_floret`), 6 rotacji co 60° = kwiat; kwiaty na kracie `t1=(2.5,√3/2), t2=(2.0,−√3)` (|t|=√7, chiralne jak snub hex). Zweryfikowane polami (bez dziur/nakładek).
- **pythagorean:** dwa rozmiary kwadratów (klasyczny bruk pitagorejski) — trywialny lattice; proporcja boków np. 2:1.

### S5: zmienna wielkość komórek (voronoi, phyllotaxis, poincare)
- **Wspólny inwariant: determinizm preview↔render.** Seed = f(base_s, target_w, target_h) przez `np.random.default_rng` — NIGDY globalny `random`. Ten sam seed w preview (mniejszy target!) da INNĄ geometrię niż w renderze — to akceptowalne (tak samo działa spectre: inna liczba kafelków przy innej rozdzielczości), ale musi być powtarzalne dla tych samych wymiarów.
- **Wspólny mechanizm min-area:** komórki o powierzchni < (base_s/4)² scalać z sąsiadem lub pomijać (parametr w rejestrze). Dotyczy centrum phyllotaxis, rantu poincare, małych komórek voronoi.
- **voronoi:** punkty Poissona (rozrzedzanie przez odrzucanie, promień ≈ base_s) + `scipy.spatial.Voronoi` (jest w env); przycinanie komórek nieskończonych do ramki.
- **phyllotaxis:** punkty `r=c√n, θ=n·137.508°`; komórki jako Voronoi tych punktów (ta sama maszyneria co wyżej); `c` dobrane by mediana komórki ≈ base_s.
- **poincare {7,3}:** `cosh R = cot(π/p)·cot(π/q)` → r₀ = tanh(R/2)·R_dysku. ⚠ **Pułapka (kosztowała iterację):** wzór `cos(π/q)/sin(π/p)` jest ZŁY (kafelki nachodzą). Odbicia = inwersje względem okręgów geodezyjnych (rozwiązanie 2×2: `2z·c = |z|²+1`); BFS z dedup po centroidzie **zaokrąglonym do 1e-3** (drobniejszy klucz przepuszcza dryfujące duplikaty). Krawędzie rysować jako spolygonizowane łuki. Mozaika = dysk; poza dyskiem tło (parametr kolor/czarny). Kompletny kod w `gen_poincare`.

### S6: polar + archimedesowe
- **sunburst:** sektory pierścieniowe — **łuki polygonizować** (N segmentów ∝ promień), wtedy zostaje w rdzeniu wielokątnym. Mikrosektory w centrum → próg min-area z S5.
- **voderberg (stylizowany):** pierścienie wygiętych klinów: krawędź radialna = polilinia `r=lerp, θ=θ₀+twist·t+bend·sin(πt)`, twist=6°/pierścień. Kod w `gen_voderberg`. Prawdziwy dziewięciokąt Voderberga = opcjonalny follow-up (trudna konstrukcja, niski zysk wizualny vs stylizacja).
- **trunc_square (4.8.8), trunc_hex (3.12.12), rhombitrihex (3.4.6.4):** proste okresowe lattice'y wielokątów foremnych — bez pułapek; wzory wierzchołków z definicji parkietaży archimedesowych.

### S7: geometria projektowana
- **girih — NAJRYZYKOWNIEJSZY Tier A.** Greedy edge-gluing (jak w `_girih_attempt`) osiąga ~97% pokrycia, ale zostawia dziury — w schemacie OK, w mozaice NIE. Opcje (decyzja z userem na starcie S7): (a) zaprojektowany okresowy patch dekagon+heksagony (najlepszy seed greedy jako wzorzec jednostki), (b) greedy + wypełnianie dziur kafelkami tła w kolorze średnim, (c) najpierw prototyp, potem decyzja. Kafelki-szablony (turtle, kąty ×36°) w `_girih_attempt`.
- **escher_lizard:** system p1 na heksagonie pointy-top: krawędzie e0,e1,e2 deformowane polilinią, e3,e4,e5 = translacje odwrotności (`t01=h0+h1` itd. — dokładnie w `gen_escher`); kafelkowanie CZYSTĄ translacją `(√3,0),(√3/2,1.5)` — silnikowo trywialne. ⚠ Wyzwanie artystyczne: obecny profil to „abstrakcyjny stworek"; docelowa sylwetka jaszczurki wymaga ręcznego dostrojenia polilinii (iteracje wizualne z userem) — geometria się nie zmienia, tylko offsety.

### S8: Tier B
- **truchet/truchet_hex — WDROŻONE 2026-07-13** (`_CurvedMask` nigdy nie powstał — odrzucony 2026-07-11). Komórki = REGIONY wycięte przez łuki, nie same łuki: kwadrat → 2 ćwierćdyski (łuki r=s/2 na przeciwległych rogach) + wstęga „S"; heksagon → 3 wycinki 120° na NAPRZEMIENNYCH wierzchołkach (łuk r=a/2 łączy środki dwóch krawędzi tego wierzchołka) + zakrzywiony środek. Ciągłość krzywych: łuk dochodzi do krawędzi w jej środku pod kątem prostym (promień biegnie wzdłuż krawędzi), a każda krawędź ma dokładnie jeden koniec w wybranej trójce ⇒ krzywe łączą się przez krawędzie NIEZALEŻNIE od orientacji sąsiada.
- ⚠ **Pułapka kroku polygonizacji (kosztowała iterację — fasetowane łuki w truchet_hex):** `seg = base_s/3` (jak sunburst/voderberg) jest ZŁE dla truchetu. Tam promień łuku rośnie z kadrem, tu promień to zawsze ~`base_s/2` — przy `seg=base_s/3` strzałka wychodzi 1–3 px i widać wielokąt. Nowy helper `_arc_pitch(r, tol=0.35)` = `sqrt(8·r·tol)` (ze wzoru strzałka ≈ krok²/8r) trzyma strzałkę pod-pikselowo przy każdym `r`.
- **Orientacja bez RNG:** `_truchet_flip(i, j)` = hash całkowitoliczbowy indeksu komórki ⇒ ta sama komórka ma tę samą orientację w KAŻDEJ rozdzielczości (podgląd 2K pokazuje wzór, który będzie w 16K — lekcja z seeda girih), `seeded=False`, render reprodukowalny bit-w-bit.
- **Schematy GUI zregenerowane z geometrii silnika** (`src/tools/gen_truchet_schemes.py`, COMMITOWANY): stare PNG (2ec504c) rysowały cienkie łuki na tle — mozaika takich linii nie narysuje, rysuje komórki. Dwutonowa paleta (ćwierćdyski akcentem) sprawia, że krzywe truchetu nadal się czytają.
- **weave — ROZSTRZYGNIĘTE 2026-07-13 (wdrożone):** pierwotny zapis („nie jest partycją, kompozycja sekwencyjna z-order, przerwa między wstęgami = tło") jest **UNIEWAŻNIONY** przez twardą regułę usera z 2026-07-03 (każdy kształt = prawdziwa teselacja brzeg-w-brzeg, bez nakładek i bez luk). W silniku nakładki = dwa zdjęcia walczące o piksele, a przerwy = czarne kwadraty. Wdrożona **partycja**: komórka = WIDOCZNY kawałek wstęgi (wstęga znika dokładnie na swoich skrzyżowaniach „pod", więc jej widoczny kawałek biegnie od jednego takiego skrzyżowania do następnego → prostokąt `w × (2·pitch − w)` wyśrodkowany na skrzyżowaniu „nad"; parzystość `(i+j)` przydziela każde skrzyżowanie dokładnie jednej wstędze) + **komórka-węzeł** `(pitch − w)²` w dziurze między czterema wstęgami (mały kafel teselacji mieszanej, jak trójkąty w rhombitrihex). Schemat `assets/shape_schemes/weave.png` zregenerowany z tej samej geometrii (`gen_weave`, rev 2026-07-13) — GUI pokazuje to, co silnik naprawdę renderuje. Dominujący kafel: `pitch = base_s/√0.9324`.

## Wyzwania przekrojowe (checklista przed każdym sprintem)

1. **Bit-repro preview↔render** — golden testy po każdym sprincie; RNG tylko seeded (patrz S5).
2. **`search_radius = base_s*1.5`** (engine_smart.py:615) zakłada stały rozmiar kafelka — dla S5/S6 rozważyć promień per-sektor (z przekątnej bboxa sektora). Nie zmieniać dla istniejących kształtów.
3. **`_nkey`** zawiera już shape_mode/border_mode — nowe kształty z seedem geometrii nie wymagają zmiany klucza (seed pochodny od wymiarów, które już są w kluczu).
4. **Reindeks NIEPOTRZEBNY** — kształty po stronie targetu, indeks 79-dim agnostyczny.
5. **GUI:** dropdown rozszerzać z rejestru per sprint; schematy PNG dla wszystkich 20 już są w `assets/shape_schemes/`.
6. **Wydajność 16K:** liczba sektorów rośnie (pinwheel/floret gęste przy małym base_s) — pilnować peak-RAM (inwarianty A1: `_euclid_f32`, `_LazyMask`); przy wątpliwości pomiar `PeakRAMSampler`.
7. **ASCII-only** w printach `src/tools/*` i testach (CP1250).

## Definicja ukończenia (S9)

- 20 nowych kształtów renderuje z CLI i GUI (`python -m src.cli render ... --shape <mode>`),
- golden testy + pełny `pytest` zielone,
- README EN+PL: tabela kształtów + montaż zbiorczy,
- seria mozaik testowych (batch CLI po wszystkich kształtach, 1 obraz) → **user wybiera finalny zestaw kształtów**.
