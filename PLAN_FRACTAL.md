# PLAN_FRACTAL.md — Fraktale jako funkcjonalność (4 finalistów)

**Status:** zatwierdzony przez usera 2026-07-05 (werdykt po procesie adwersarialnym). Kanoniczny plan — konsoliduje materiały ze Sprintów 1-3 (oryginały w gitignorowanym `output/fractal_proposals/`, ten plik jest jedynym trwałym zapisem).
**Zakres:** funkcjonalności fraktalne POZA kształtami siatki (kształty ma PLAN_SHAPES.md). Cztery finalne funkcje + trzej odłożeni + trzej skreśleni (nie proponować ponownie).
**Wizualizacje:** `output/fractal_proposals/*.png` — reprodukowalne przez `python -m src.tools.gen_fractal_feature_schemes` (commit `883d171`).

## Proces (2026-07-05)

Cztery role w procesie adwersarialnym, user werdyktuje po każdym sprincie:

1. **Sprint 1 — Wizjoner:** 10 pomysłów (opis + mechanika + efekt WOW).
2. **Sprint 2 — Inżynier-sceptyk + Esteta-kurator NIEZALEŻNIE**, potem **Arbiter** (synteza, ranking ważony: WOW 0.35 · wykonalność 0.30 · substancja 0.20 · niskie ryzyko 0.15).
3. **Sprint 3 — Inżynier:** specyfikacje MVP 4 finalistów (po lekturze `engine_smart.py`, `make_dzi.py`, `make_zoom_gif.py`, `cli.py`).
4. **Sprint 4 — ten dokument** (konsolidacja) → wdrożenie.

Filtr Estety (lekcje z rewizji kształtów): motyw musi przetrwać podmianę na zdjęcia; klasy rozmiarów ≥3×; matematyczna prawdziwość > efekciarstwo; 3 skale widza (pełny kadr / średni zoom / pełny zoom).

## Werdykt finalny usera

| Status | Pomysły |
|---|---|
| **FINALIŚCI** (kolejność wdrożenia) | `hilbert_flow` → `quadtree_detail` → `fractal_crossfade` → `zoom_movie` |
| **ODŁOŻENI** (nie skreśleni) | `pifs_self_collage` (po fazie portfolio), `lsystem_veins` (pierwszy alternat, wariant recolor-LAB), `dla_growth_timelapse` (tani dodatek „Reveal") |
| **SKREŚLENI** (nie proponować) | `droste_infinite_zoom`, `julia_field_mod`, `fractal_dimension_match` |

## Sprint 1 — 10 pomysłów Wizjonera (skrót)

| # | Pomysł | Jedno zdanie |
|---|--------|--------------|
| 1 | `quadtree_detail` | Rozmiar kafla zależny od lokalnego detalu (rekurencyjny podział 4× przy wariancji > próg); „mapa uwagi" wpisana w geometrię. |
| 2 | `droste_infinite_zoom` | Doklejane poziomy piramidy DZI poniżej natywnej rozdzielczości — kafelek rozpada się na kolejną mozaikę, zoom bez końca. |
| 3 | `julia_field_mod` | Pole escape-time Julii moduluje rotację/nasycenie/blend kafla PO doborze; niewidzialny wir w fakturze. |
| 4 | `pifs_self_collage` | Trzeci silnik: biblioteką kafelków jest samo zdjęcie (partycjonowana IFS, domain→range, 8 izometrii, least-squares kontrast). |
| 5 | `hilbert_flow` | Dobór kafli WZDŁUŻ krzywej Hilberta z oknem anti-repeat K i karą gładkości LAB — „tkany" charakter, koniec sąsiadujących duplikatów. |
| 6 | `fractal_crossfade` | Dwie mozaiki na tej samej siatce zszyte progiem pola fBm — fraktalny front jak mróz na szybie; klatka graniczna = samodzielny print. |
| 7 | `zoom_movie` | Dolly-zoom wideo: kamera nurkuje w kafelek, ten okazuje się mozaiką następnego obrazu; łańcuch w pętli. |
| 8 | `lsystem_veins` | Żyły L-systemu po mozaice; komórki pod maską dostają inny styl (druga biblioteka / glify Typo / recolor-LAB). |
| 9 | `dla_growth_timelapse` | Timelapse narodzin mozaiki: kafelki pojawiają się w kolejności wzrostu DLA (permutacja kolejności wklejania, koszt ≈ 0). |
| 10 | `fractal_dimension_match` | Lokalny wymiar fraktalny (box-counting) jako dodatkowa cecha dopasowania — chropowate obszary dostają chropowate kafelki. |

## Sprint 2 — krytyki i synteza

### Fakty z kodu, na których stoi krytyka Inżyniera

- Sektor już dziś może mieć dowolny bounding box (kites/spectre), a cecha 5×5 LAB przez `resize((5,5), BOX)` jest **skalowo-niezależna** → ułatwia niejednorodne siatki.
- Anti-repetycja zależy od sztywnego `search_radius = base_s * 1.5` (`engine_smart.py:769`) — zakłada jednorodną wielkość komórki.
- `allow_mirror` robi `reshape(-1,5,5,3)` na 75-dim (l. 798) i jest w mutexie z `edge_aware` (79-dim) — każdy pomysł dokładający wymiary wchodzi w minę EDGE_WEIGHT.

### Werdykty Inżyniera (wykonalność) i Estety (portfolio)

| # | Pomysł | Inżynier (praca/ryzyko) | Esteta (WOW kadr/śr/zoom) | Arbiter (suma) |
|---|--------|---|---|:---:|
| 1 | quadtree_detail | ŻÓŁTY (M, R3) | MUST-HAVE (4/5/5) | **4.10** — rdzeń kolekcji |
| 5 | hilbert_flow | ZIELONY (S/M, R2) | LETNI jako feature / cichy always-on (2/2/2) | 3.75 (artefakt wag — taniość) |
| 7 | zoom_movie | ŻÓŁTY (M/L, R3) | MUST-HAVE headline (5/5/5) | 3.70 |
| 9 | dla_growth_timelapse | ZIELONY (S/M, R2) | WARTY tylko live (4 wideo / 1 statyk) | 3.55 (artefakt wag) |
| 6 | fractal_crossfade | ŻÓŁTY (M, R2-3) | WARTY (4/4/3) | 3.45 |
| 8 | lsystem_veins | ŻÓŁTY (M/L, R3) | WARTY, blisko must (3/4/5) | 3.33 — alternat |
| 4 | pifs_self_collage | ŻÓŁTY→CZERWONY (L, R4) | WARTY, najlepszy story (3/4/4) | 3.15 — faza silnikowa |
| 10 | fractal_dimension_match | ŻÓŁTY (M+reindeks, R3) | LETNI (3/2/3) | 2.50 — odłóż |
| 3 | julia_field_mod | ZIELONY* bez rotacji ciągłej (S/M, R2) | ODRADZAM (2/2/2) | 2.33 — odrzuć |
| 2 | droste_infinite_zoom | CZERWONY (XL, R5) | WARTY, redundantny z #7 (2/4/5) | 2.18 — odrzuć |

### Rozstrzygnięcia sporów Arbitra

- **#7** (Esteta MUST vs Inżynier ŻÓŁTY): przeważa Esteta — shareowalny nagłówek to waluta nr 1 fazy portfolio; szew skali to warunek powodzenia, nie blokada.
- **#3** (Inżynier ZIELONY vs Esteta ODRADZAM): przeważa Esteta — taniość bez znaczenia, gdy motyw nie przeżyje podmiany na zdjęcia.
- **#4** (Esteta WARTY vs Inżynier L→CZERWONY): przeważa Inżynier — indeks per-render (minuty) + trzeci silnik = koszt fazy silnikowej, nie portfolio.

### Synergie

1. #2 vs #7 kanibalizacja → #7 wygrywa, #2 skreślony.
2. #5 jako domyślny tryb doboru pod #1/#6/#7 (fundament jakościowy, nie eksponat).
3. #9 jako opcjonalny „tryb live" do dowolnego renderu (koszt ≈ 0), nie kosztem slotu.
4. #1+#8 komplementarne (gęstość + żyły); przy budżecie na jeden wygrywa #1.
5. Lukę thumbnaila (WOW z miniatury) pokrywają tylko #1 i #6 → oba są finalistami.

### Czego puli brakuje (notatka Estety na przyszłość)

1. Uzbrojenie PEŁNEGO KADRU z daleka (thumbnail — rekruter najpierw widzi miniaturę).
2. Kolor jako bohater — żaden pomysł nie robi spektaklu z samej barwy.
3. Interaktywność inna niż zoom (hover-reveal, suwak progu crossfade na żywo w DZI).

## Odłożeni — warunki powrotu

- **`pifs_self_collage` [trzeci silnik]:** najsilniejsza narracja matematyczna puli, ale indeks domain budowany per-render (~23 tys. pozycji × 8 izometrii ≈ 190 tys. wektorów z rgb2lab = minuty preprocessingu KAŻDORAZOWO — łamie model „indeks raz, render szybko") + pełny trzeci silnik (GUI/CLI/testy) + ryzyko kolapsu least-squares do „rozmytego oryginału". **Wraca** jako pierwszy duży feature po fazie portfolio; eksponat „dla technicznego widza" z podpisem; mitygacja: cache indeksu domain per obraz.
- **`lsystem_veins` [nakładka]:** jedyne obok #1 prawdziwe samopodobieństwo w głębokim zoomie + „miesza silniki" (świeży hak). Pełna obietnica (glify Typo w żyłach) = integracja cross-engine bez wspólnej abstrakcji sektora (L); drugi indeks = +136 MB RAM. **Wraca** jako pierwszy alternat, TYLKO wariant recolor-LAB pod maską (M), jeśli komplet finalistów okaże się za mało „zoomowy". Żyły jako ornament, nie uszkodzenie.
- **`dla_growth_timelapse` [tryb prezentacji]:** ZIELONY u Inżyniera, koszt ≈ 0 (permutacja `sector_assignments`, klatki w rozdzielczości podglądu, naturalne rozszerzenie `progress_cb`), ale nie tworzy artefaktu — finał identyczny ze zwykłą mozaiką. **Wraca** automatycznie jako tani dodatek „Reveal: instant / DLA timelapse (GIF)" przy okazji dowolnego wdrożenia. Uwaga: naiwna DLA mieli — wariant kratowy z ograniczonym błądzeniem; pierwsze RNG w silniku → jawny seed.

## Skreśleni — powody (nie proponować ponownie)

- **`droste_infinite_zoom`:** `make_dzi` ładuje JEDEN raster do RAM i resizuje w dół — poziomy poniżej natywnej rozdzielczości = raster setek gigapikseli; realnie własny proceduralny generator kafli + custom TileSource w JS (poza stackiem, koniec statycznego GitHub Pages); siatki 256 px (DZI) i 75 px (kafle) niewspółmierne. Jedyny pomysł ZASTĘPUJĄCY działającą funkcję. Największy rozjazd obietnica↔rzeczywistość (XL, R5). Oś „nieskończonego zanurzenia" przejął `zoom_movie` za ułamek kosztu. Wróciłby wyłącznie z gotowym zewnętrznym TileSource.
- **`julia_field_mod`:** modulacja działa PO doborze kafla i subtelnie — motyw NIE przetrwa podmiany kolorów zdjęciami, odczyta się jako brud/niekonsekwencja renderu; WOW „w żadnej skali"; dokładnie ten typ błędu, za który odrzucano kształty. Techniczne miny przy okazji: rotacja ciągła = czarne kliny (bezpieczne tylko 0/90/180/270 dla square); delta-L = tysiące konwersji RGB↔LAB w composite. Wróciłby tylko przeprojektowany tak, by pole sterowało DOBOREM kafli (= inny pomysł).
- **`fractal_dimension_match`:** box-counting na kafelku 75 px = fit log-log z 2-3 punktów = szum (cecha może nie dyskryminować); pełna re-indeksacja ~455 tys. kafli; drugi duplikowany inwariant wagi obok EDGE_WEIGHT (znany footgun) + kolizja z `reshape(5,5,3)` w allow_mirror → kombinatoryka mutexów w kruchym `_resolve_matching_modes`. Kolor dominuje percepcję — zysk na granicy zauważalności. Wróci co najwyżej jako cichy dodatek przy okazji innego reindeksu, po walidacji dyskryminacyjności na próbce.

---

# Sprint 3 — specyfikacje MVP (4 finaliści)

Kolejność wdrażania (uzasadnienie synergii): **hilbert_flow → quadtree_detail → fractal_crossfade → zoom_movie**. Najpierw edycje rdzenia dopasowania (hilbert i quadtree dzielą pętlę `_do_render` — jeden kontekst edycji), potem funkcje kompozycyjne (crossfade, zoom) traktujące silnik jak czarną skrzynkę. Hilbert idzie pierwszy, bo podnosi jakość *każdego* renderu — także kafli używanych potem w quadtree/crossfade/zoom.

> **Stan kodu (zweryfikowany 2026-07-05):** rejestr `SHAPE_MODES` + `ShapeSpec` już istnieją (`engine_smart.py:156`, kinds `grid`/`polygon`) — quadtree wchodzi jako nowy `kind`. Golden testy SHA-256 czterech reprezentatywnych kształtów też istnieją (`tests/test_golden_shapes.py`) — to gotowa siatka bezpieczeństwa dla refaktoru pętli w F1a.

## A. `hilbert_flow` — cichy tryb doboru (fundament)

### Zakres MVP
- **Wchodzi:** opcjonalny porządek przypisań wzdłuż krzywej Hilberta z oknem anti-repeat (ostatnie K) + mała kara za dystans LAB do poprzedniego kafla na krzywej. Domyślnie **ON dla `square`**, OFF (fallback do obecnego zachowania) dla wszystkich innych kształtów.
- **Odcinamy:** hex/kite/spectre/quadtree (nieregularna/przesunięta siatka — kwantyzacja do Hilberta zawodna); brak ekspozycji parametrów K/kary w GUI v1 (stałe w kodzie).

### Przepływ danych
1. Zbuduj sektory jak dziś (gałąź grid, `square`).
2. **Nowość:** oblicz dystanse i wyłuskaj `top_k` kandydatów (indeks + dystans) dla **wszystkich** sektorów w jednym przebiegu GEMM, zapisz kompaktowe tablice `cand_idx[N,k]`, `cand_dist[N,k]`.
3. Zbuduj permutację Hilberta z `(col,row)` (xy2d na najbliższej potędze 2 ≥ max(cols,rows)).
4. Drugi przebieg: iteruj sektory w porządku Hilberta; wybór = min(`dist + freq_penalty + kara_gładkości·‖LAB_kand − LAB_poprz‖`), z zakazem indeksów z okna ostatnich K.
5. Composite bez zmian.

### Dotykane moduły
- `src/engine_smart.py`: refaktor pętli dopasowania (l. 821-903) na **dwufazową** (najpierw kandydaci, potem przypisanie w wybranym porządku). Nowy prywatny helper `_hilbert_order(cols, rows)` (czysta arytmetyka bitowa). Nowe pole `flow_mode` (domyślnie `"hilbert"` dla square, `"none"` wpp).
- **NIE zmienia się:** `_euclid_f32`, ekstrakcja cech, `_get_neighbors_map`, maski, `create_mosaic`/`render_preview` (poza przekazaniem flagi), format indeksu.

### GUI/CLI
- GUI: pojedynczy checkbox „Flow (smooth ordering)" aktywny tylko gdy shape=`square` (szary wpp).
- CLI: `--flow {auto,hilbert,none}` w grupie smart, `auto` = hilbert dla square. Reszta bez zmian.

### Testy
- **Determinizm:** dwa rendery square+hilbert identyczne bit-w-bit.
- **Regresja:** `--flow none` na square = bit-w-bit obecny baseline (chroni 209 testów).
- **Inwariant okna:** żaden kafel nie powtarza się w oknie K sąsiadów na krzywej.
- **Fallback:** shape=hexagon ignoruje flow (identyczny z baseline).

### Pracochłonność i ryzyka
**2-3 dni, ryzyko 2.** RAM drugiego przebiegu (`cand_*` dla ~50k sektorów): `top_k=64` w fazie flow (nie 200) → ~25 MB. Pogorszenie czystego matchu koloru przez karę gładkości: kara mała, konfigurowalna stałą; test wizualny na obrazie referencyjnym. Sektory poza kwadratem Hilberta: dołożone na końcu porządku w kolejności rastrowej (deterministyczne).

## B. `quadtree_detail` — adaptacyjna gęstość (cap głębokości)

### Zakres MVP
- **Wchodzi:** rekurencyjny podział komórki na 4 ćwiartki gdy wariancja LAB/energia krawędzi > próg; **twardy cap głębokości** (min_leaf ≥ `base_s`, max 2-3 poziomy w górę). Liście = kwadraty (bez masek wielokątnych, wypełnienie prostokątne). Wspólny cKDTree (cecha 5×5 skalowo-niezależna).
- **Odcinamy (świadomie):** brak adaptacyjnego anti-repeat w v1 — **anti-repetycja sąsiedzka WYŁĄCZONA dla quadtree** (unik miny sztywnego `search_radius`; freq_penalty zostaje); brak liści rozdmuchanych 75→600 (cap min_leaf blokuje giganty → unik papki); tylko `square`.

### Przepływ danych
1. Zbuduj target jak dziś; policz mapę wariancji/energii krawędzi (jednorazowy numpy).
2. Rekurencyjny podział: kolejka węzłów; dziel gdy wariancja > próg i rozmiar > min_leaf, stop na cap. Zwróć listę liści (bbox kwadratowych).
3. Dla każdego liścia zbuduj sektor przez istniejącą ścieżkę bbox (crop → `resize(5,5,BOX)` → cecha) — reuse `_compute_sector_feature`.
4. Dopasowanie GEMM/top_k jak dziś, **bez** `neighbors_map` (freq_penalty zostaje, anti-repeat sąsiedzki nie).
5. Composite: `_smart_crop` kafla do rozmiaru liścia; brak maski (prostokąt).

### Dotykane moduły
- `src/engine_smart.py`: nowa gałąź `shape_mode == "quadtree"` budująca `sectors_data` z liści; nowy helper `_build_quadtree(target, min_leaf, thresh, max_depth)`. Wpis w `SHAPE_MODES` (nowy `kind`) + `shape_names()`. Warunkowe pominięcie `_get_neighbors_map`/forbidden gdy quadtree.
- **NIE zmienia się:** `_euclid_f32`, format indeksu, gałęzie grid/polygon, `make_dzi` (działa na płaskim rastrze wyniku).

### GUI/CLI
- GUI: `quadtree` w dropdownie kształtów + 2 suwaki: „Detail sensitivity" (próg) i „Max subdivisions" (cap, 0-3).
- CLI: `--shape quadtree`, `--qt-sensitivity FLOAT`, `--qt-max-depth INT`.

### Testy
- **Determinizm:** identyczny podział i render dla tego samego wejścia/parametrów.
- **Cap:** żaden liść < min_leaf ani > min_leaf·2^max_depth (brak gigantów).
- **Zgodność cech:** liść 4× większy i liść bazowy dają wektory 75-dim tej samej normy skali (sanity `resize(5,5)`).
- **Próg działa:** gładkie tło → mało liści, detal → dużo (liczba liści rośnie z czułością).

### Pracochłonność i ryzyka
**3-4 dni, ryzyko 3.** Szwy między skalami: liście kwadratowe abutują dokładnie; `render_padding=1.02` domyka piksel. Brak anti-repeat → powtórki w gładkich polach: freq_penalty (kwadratowa) wystarcza dla v1; adaptacyjny promień = backlog v2. Cap za ciasny = brak WOW: domyślny max_depth=2 daje kontrast 4× bez rozdmuchania — walidować na portrecie (efekt wymaga zdjęć z wyraźnym podziałem gładkie/detal).

## C. `fractal_crossfade` — jedna klatka graniczna (MVP)

### Zakres MVP
- **Wchodzi:** dwa obrazy na **identycznej geometrii siatki**, maska progowa fBm (seedowana), **pojedyncza klatka** hybrydowa: komórka bierze kafel z mozaiki A gdy pole < t, z B wpp. Pas |pole−t|<ε blendowany 50/50.
- **Odcinamy:** animacja/sekwencja klatek (backlog); cache kafli RAM na wiele klatek (niepotrzebny dla 1 klatki); siatka musi być wspólna — twarda walidacja identycznych parametrów.

### Przepływ danych
1. Renderuj mozaikę A i mozaikę B tymi samymi parametrami; MVP komponuje z **dwóch gotowych rastrów + maska pikselowa** (zero zmian w silniku). Wariant „re-composite z `sector_assignments`" (unik podwójnego kompozytowania) — opcjonalny, +1 dzień.
2. Wygeneruj pole fBm w rozdzielczości siatki (seedowany numpy) → wartość per sektor (środek komórki).
3. Dla progu t: wybierz per sektor źródło (A/B/blend w pasie ε).
4. Composite pojedynczej klatki; zapis PNG/JPG (klatka portfolio).

### Dotykane moduły
- **Nowy plik** `src/tools/make_crossfade.py`: orkiestruje dwa rendery przez publiczne API `SmartEngine` (`create_mosaic` jako czarna skrzynka), buduje pole fBm, składa klatkę.
- **NIE zmienia się:** rdzeń dopasowania, format indeksu, GUI silnika.

### GUI/CLI
- CLI-first: `python -m src.tools.make_crossfade <A> <B> <out> --res 8K --shape square --threshold 0.5 --seed 0 [--epsilon 0.03]`.
- GUI: backlog (docelowo mała sekcja „Crossfade (2 obrazy)" w zakładce Smart) — MVP tylko CLI.

### Testy
- **Determinizm:** ten sam seed+t → identyczna klatka bit-w-bit.
- **Walidacja geometrii:** różne parametry A/B (inny shape/scale) → czytelny błąd (nie IndexError).
- **Skrajne progi:** t=0 → czyste B, t=1 → czyste A (klatka = pojedynczy render).
- **Reprodukowalność fBm:** pole deterministyczne dla seeda (test na wartościach pola, nie na obrazie).

### Pracochłonność i ryzyka
**2-3 dni, ryzyko 2-3.** Dwa pełne rendery = 2× czas: MVP celuje w 8K; 16K to pojedynczy offline'owy przebieg. Front gruboziarnisty zamiast „mrozu": dobór częstotliwości fBm + pas ε konfigurowalny. Złe pary zdjęć = chaos-kolaż: seed sweep i ręczny wybór klatki (jak przy girih). **Pierwsze RNG w ścieżce portfolio — seed obowiązkowy.**

## D. `zoom_movie` — nieskończony dolly-zoom (GIF, bez ffmpeg)

### Zakres MVP
- **Wchodzi:** łańcuch **~4 obrazów w pętli**; kamera nurkuje w wybrany kafel mozaiki_i, który przy pełnym zbliżeniu przechodzi crossfade w pełną mozaikę_{i+1}; ostatni wraca do pierwszego. Wyjście **GIF** (reuse aparatu `make_zoom_gif`), bez ffmpeg.
- **Odcinamy:** mp4/H.264 (ffmpeg — backlog); interaktywność; dowolna długość łańcucha (fix ~4).

### Przepływ danych
1. Wyrenderuj 4 mozaiki wysokiej rozdzielczości (offline, przez `create_mosaic`).
2. Dla każdej pary (i, i+1): wybierz kafel w mozaice_i najlepiej pasujący kolorystycznie do **miniatury** obrazu_{i+1} (ta sama cecha 5×5 LAB — reuse `_compute_sector_feature` + argmin po cechach sektorów renderu).
3. Generuj klatki nurkowania w kafel (crop+resize+easing log — reuse `_crop_box`/`_easing`/`_render_frame` z `make_zoom_gif`), centrując zoom na tym kaflu.
4. W punkcie maksymalnego zbliżenia: crossfade kilku klatek między upscalowanym cropem kafla a pełną mozaiką_{i+1}.
5. Sklej klatki w zapętlony GIF (`frames[0].save(..., loop=0)`).

### Dotykane moduły
- **Nowy plik** `src/tools/make_zoom_movie.py`: orkiestracja łańcucha; **importuje i reużywa** `_crop_box`, `_easing`, `_render_frame` z `make_zoom_gif.py` (wydzielić jako publiczne — drobny refaktor tego pliku).
- Helper doboru kafla-portalu: cechy sektorów z renderu (`sectors_data`) lub przeliczone na gotowym rastrze.
- **NIE zmienia się:** `make_dzi`, rdzeń dopasowania, format indeksu.

### GUI/CLI
- CLI: `python -m src.tools.make_zoom_movie <img1> <img2> <img3> <img4> <out.gif> --res 8K --fps 14 --seconds-per-hop 3 [--loop]`.
- GUI: brak w MVP (narzędzie portfolio).

### Testy
- **Determinizm:** ten sam zestaw wejść → identyczna liczba i treść klatek (hash pierwszej/środkowej/ostatniej).
- **Dobór kafla:** dla znanej pary wybrany indeks = argmin dystansu LAB (jednostkowy, bez renderu GIF).
- **Ciągłość pętli:** ostatnia klatka ≈ pierwsza (próg różnicy).
- **Brak ffmpeg:** testy przechodzą w środowisku bez ffmpeg (tylko PIL).

### Pracochłonność i ryzyka
**4-5 dni, ryzyko 3** (najwięcej pracy manualnej: strojenie easingu/crossfade). Rozmycie kafla 75 px tuż przed przejściem: crossfade w kilku klatkach maskuje skok skali; easing log = stała prędkość wrażeniowa. Rozmiar GIF (128 kolorów, banding): 640×360 jak `make_zoom_gif`, ~4 hopy × ~40 klatek; mp4 = backlog. Szew centrowania między obrazami: wymusić `cx_frac/cy_frac` na środku wybranego kafla.

---

## Harmonogram i inwarianty

| Kolejność | Finalista | Dni | Ryzyko | Uzasadnienie pozycji |
|---|---|:---:|:---:|---|
| 1 | hilbert_flow | 2-3 | 2 | Fundament; podnosi jakość kafli używanych przez pozostałe 3 |
| 2 | quadtree_detail | 3-4 | 3 | Dzieli rdzeń `_do_render` z hilbertem (jeden kontekst edycji) |
| 3 | fractal_crossfade | 2-3 | 2-3 | Kompozycja czarnoskrzynkowa; nowy plik, minimalne zmiany silnika |
| 4 | zoom_movie | 4-5 | 3 | Najbardziej niezależny; kapstone reużywający `make_zoom_gif` |

**Łącznie ~11-15 dni.** Trzy inwarianty do pilnowania w KAŻDYM PR:
1. **Determinizm** — test bit-w-bit dla każdej nowej ścieżki.
2. **Brak regresji baseline'u przy trybach OFF** — `--flow none` i istniejące kształty identyczne bit-w-bit z obecnym zachowaniem.
3. **Jawne seedowanie każdego nowego RNG** — fBm w crossfade to pierwsze RNG w ścieżce renderu portfolio (silnik jest dziś RNG-free).

---

# Plan wykonawczy — krótkie sprinty (dla Opus/Sonnet po `/start`)

## Kontekst dla wykonawcy (przeczytaj PRZED pierwszym sprintem)

**Jak korzystać z tego planu:** po `/start` znajdź pierwszy nieodhaczony sprint poniżej i wykonaj go. Po KAŻDYM sprincie: (1) pełne testy zielone (`pytest tests/`), (2) commit (conventional, typ podany przy sprincie), (3) odhacz checkbox `[x]` w tym pliku i dopisz hash commitu, (4) pokaż userowi wynik do werdyktu — **nie zaczynaj następnego sprintu bez werdyktu**. Specyfikacje merytoryczne (zakres/przepływ/testy/ryzyka) są w sekcjach A-D wyżej — sprinty poniżej tylko tną je na kroki i dodają kotwice w kodzie; przy sprzeczności specyfikacja A-D wygrywa.

**Stan kodu (zweryfikowany 2026-07-05, HEAD `e4061d9`, 209 testów zielonych):**
- `SHAPE_MODES` + `ShapeSpec` — `engine_smart.py:156` (kinds `grid`/`polygon`; `shape_names()` = single source of truth dla GUI dropdown, CLI choices, showcase, benchmark).
- **Pętla dopasowania jest chunkowana i SKLEJONA z kompozycją** (`engine_smart.py:819-903`): per chunk GEMM `_euclid_f32` → `argpartition` top_k=200 → sekwencyjne przypisanie (forbidden z `neighbors_map`, `freq_penalty` z `used_counts**2`, l. 839-867) → **natychmiastowy** `alpha_composite` (l. 869-896). Rozdzielenie przypisania od kompozycji to sedno F1a.
- `search_radius = base_s * 1.5` (l. 769) → `_get_neighbors_map` (l. 210, cache po `_nkey`). `allow_mirror` → `reshape(-1, 5, 5, 3)` (l. 798), mutex z `edge_aware`.
- Golden testy: `tests/test_golden_shapes.py` — słownik `GOLDEN` (SHA-256, 4 kształty × border), deterministyczna biblioteka 32 kafli + gradient analityczny. Wzorzec do rozszerzania.
- `make_zoom_gif.py`: `_easing` (l. 41), `_crop_box` (l. 45), `_render_frame` (l. 89), `make_zoom_gif` (l. 97), zapis GIF `loop=0` (l. 157).
- CLI: `src/cli.py`, grupa „Smart engine options" (l. 82), `--shape` czyta `_SMART_SHAPES`.

**Twarde zasady projektu (z MEMORY.md — nie łam):** silnik jest dziś RNG-free — każdy nowy RNG z jawnym seedem; EDGE_WEIGHT identyczne indexer↔engine; allow_mirror ↔ edge_aware mutex; Pillow przyjmuje ujemne `px,py` — NIE clampuj (kliny krawędziowe); ASCII-only w print() w `src/tools/*` i `tests/*` (terminal CP1250); interpreter: `C:/Users/plazo/miniconda3/envs/mosaic/python.exe` (nie `conda run`); żadnego CLIP/semantyki.

**Routing modeli:** sprinty dotykające `_do_render` (F1a, F1b, F2a, O3b) = **HIGH (Opus)**; nowe narzędzia i GUI (F2b, F3, F4a, F4b, O1, O2a, O2b, O3a, O3c) = **LOW (Sonnet) z eskalacją do HIGH** po pierwszej nieudanej próbie naprawy.

## Faza I — finaliści

### F1a — refaktor pętli na trzy fazy (bez zmiany zachowania) — `refactor(engine)` ~1 dzień [HIGH]
- [ ] Rozdziel `engine_smart.py:819-903` na: **(1)** przebieg kandydatów — GEMM po chunkach, zapis `cand_idx[N,k]`, `cand_dist[N,k]` (+ warianty flip przy mirror); **(2)** przebieg przypisań — obecna logika forbidden/freq_penalty/used_counts, iteracja w porządku rastrowym (jak dziś); **(3)** przebieg kompozycji — paste z gotowych `sector_assignments` (przenieś l. 869-896 w całości, razem z tint i `_LazyMask.render()`).
- Uwaga na RAM: kandydaci dla WSZYSTKICH sektorów naraz — ogranicz zapis do `top_k=200` par (idx, dist) jak dziś; `progress_cb` przenieś do fazy kompozycji (to ona jest wolna).
- **DoD:** wszystkie 209 testów + `test_golden_shapes.py` bit-w-bit BEZ zmiany hashy (to jest cały sens sprintu). Zero nowych flag, zero zmian sygnatur publicznych.

### F1b — hilbert_flow właściwy — `feat(engine)` ~1-2 dni [HIGH]
- [ ] Helper `_hilbert_order(cols, rows)` (xy2d, potęga 2 ≥ max(cols,rows); sektory spoza kwadratu na końcu rastrowo). Nowy parametr `flow_mode` przez `create_mosaic`/`render_preview` → `_do_render` (`auto`→hilbert dla `square`, `none` wpp). W fazie przypisań: porządek Hilberta + okno ostatnich K (deque, stała w kodzie, start K=8) + kara `smooth_w * ||LAB_kand − LAB_poprz||` (stała, start mała — waliduj wizualnie). W fazie flow zawęź kandydatów do 64 z 200.
- [ ] GUI: checkbox „Flow (smooth ordering)" aktywny tylko dla `square`; CLI: `--flow {auto,hilbert,none}`.
- **DoD:** testy z sekcji A (determinizm; `--flow none` = golden baseline; inwariant okna K; fallback hexagon) + render porównawczy square z/bez flow dla usera (side-by-side — to na nim zapadnie werdykt o wartościach K/kary).

### F2a — quadtree_detail: rdzeń + CLI — `feat(engine)` ~2 dni [HIGH]
- [ ] `_build_quadtree(target, min_leaf, thresh, max_depth)` (mapa wariancji/energii krawędzi raz, kolejka węzłów, liście-kwadraty). Nowy `kind="quadtree"` w `ShapeSpec` + wpis `"quadtree"` w `SHAPE_MODES` + gałąź w `_do_render` budująca `sectors_data` z liści (reuse ścieżki bbox → `_compute_sector_feature`; composite prostokątny bez maski). Anti-repeat sąsiedzki WYŁĄCZONY (pomiń `_get_neighbors_map`), freq_penalty zostaje. Flow=none dla quadtree (wymusić).
- [ ] CLI: `--qt-sensitivity FLOAT`, `--qt-max-depth INT` (`--shape quadtree` wejdzie samo przez `shape_names()`).
- **DoD:** testy z sekcji B (determinizm podziału; cap min/max liścia; monotoniczność liczby liści względem czułości; sanity cechy 75-dim) + render CLI na portrecie dla usera.

### F2b — quadtree_detail: GUI + schemat — `feat(gui)` ~1 dzień [LOW]
- [ ] 2 suwaki („Detail sensitivity", „Max subdivisions" 0-3) widoczne tylko dla `quadtree`; wyszarz „Flow" gdy quadtree. Schemat `assets/shape_schemes/quadtree.png` do podglądu GUI (adaptuj panel z `gen_fractal_feature_schemes.py` do konwencji shape_schemes).
- **DoD:** GUI odpala render quadtree bez wyjątków; schemat pokazuje się po wyborze kształtu; werdykt wizualny usera na portrecie (domyślne wartości suwaków).

### F3 — fractal_crossfade (MVP = 1 klatka) — `feat(tools)` ~2-3 dni [LOW]
- [ ] Nowy `src/tools/make_crossfade.py` wg sekcji C: dwa `create_mosaic` (czarna skrzynka, twarda walidacja identycznych parametrów), pole fBm w rozdzielczości siatki (`np.random.default_rng(seed)` — jawny seed w CLI), wybór A/B per komórka + pas ε blend 50/50, kompozycja z dwóch gotowych rastrów + maska pikselowa. CLI jak w sekcji C.
- **DoD:** testy z sekcji C (determinizm bit-w-bit; walidacja geometrii → czytelny błąd; t=0/t=1 → czyste B/A; reprodukowalność pola fBm) + klatka 8K z seed-sweep (kilka seedów) do wyboru przez usera.

### F4a — zoom_movie: przygotowanie — `refactor(tools)` ~1 dzień [LOW]
- [ ] Wydziel `_easing`/`_crop_box`/`_render_frame` z `make_zoom_gif.py` jako publiczne (`easing`/`crop_box`/`render_frame`, stare nazwy jako aliasy dla zgodności). Helper doboru kafla-portalu: cecha 5×5 LAB miniatury obrazu docelowego vs cechy sektorów renderu → argmin.
- **DoD:** istniejące testy zielone; test jednostkowy doboru portalu (znana para → oczekiwany argmin, bez renderu GIF).

### F4b — zoom_movie: orkiestracja — `feat(tools)` ~2-3 dni [LOW, eskaluj przy szwie przejścia]
- [ ] Nowy `src/tools/make_zoom_movie.py` wg sekcji D: łańcuch ~4 obrazów w pętli, nurkowanie w kafel-portal (easing log, centrowanie `cx_frac/cy_frac` na środku kafla), crossfade kilku klatek w punkcie maksymalnego zbliżenia, zapętlony GIF 640×360 (`loop=0`), bez ffmpeg.
- **DoD:** testy z sekcji D (determinizm hashy klatek; ciągłość pętli; brak ffmpeg) + GIF z realnego łańcucha 4 obrazów usera — werdykt na płynności przejścia (najtrudniejszy moment całego planu; jeśli szew skali widoczny po 2 podejściach → eskalacja HIGH).

> **CHECKPOINT po F4b:** user ocenia komplet 4 finalistów. Decyzje: (1) czy komplet jest dość „zoomowy" — jeśli NIE → bramka O2 otwarta; (2) który artefakt idzie do galerii/README (PLAN_PORTFOLIO.md).

## Faza II — odłożeni (każdy za bramką; nie zaczynaj bez spełnienia warunku)

### O1 — dla_growth_timelapse „Reveal" — `feat(tools)` ~1-2 dni [LOW] — **bramka: automatyczna po F1-F4** (tani dodatek)
- [ ] DLA na kracie komórek z ograniczonym błądzeniem (jawny seed; naiwna DLA mieli — walker startuje z pierścienia wokół klastra). Porządek ujawniania = kolejność agregacji; klatki co N kafli w rozdzielczości podglądu z gotowych `sector_assignments` (reuse trójfazowej pętli z F1a — faza kompozycji z permutowanym porządkiem); GIF.
- [ ] CLI-first: `--reveal {instant,dla}` przy renderze (GUI backlog).
- **DoD:** determinizm dla seeda; finał bit-w-bit identyczny ze zwykłym renderem (to tylko permutacja kolejności wklejania); GIF demo dla usera.

### O2a — lsystem_veins: maska + recolor-LAB — `feat(engine)` ~2 dni [LOW] — **bramka: werdykt usera z CHECKPOINTU („za mało zoomowy")**
- [ ] Generator maski: L-system (2-3 predefiniowane gramatyki + jawny seed), żółw na bitmapie w rozdzielczości siatki, grubość maleje z głębokością rekursji. Komórki pod maską → transformacja recolor-LAB przypisanego kafla (wariant M ze specyfikacji; NIE glify Typo — to L, osobna decyzja). CLI: `--overlay {none,veins}` + `--veins-seed`, `--veins-grammar`.
- **DoD:** determinizm; `--overlay none` = baseline bit-w-bit; renders 2-3 gramatyk dla usera (werdykt: „ornament, nie uszkodzenie").

### O2b — lsystem_veins: GUI + strojenie — `feat(gui)` ~1 dzień [LOW] — **bramka: akcept O2a**
- [ ] Dropdown „Overlay: none / veins" + seed/gramatyka w zakładce Smart; strojenie siły recoloru wg werdyktu z O2a.
- **DoD:** GUI działa bez wyjątków; werdykt wizualny usera.

### O3a — pifs_self_collage: spike GO/NO-GO — `feat(tools)` ~2 dni [LOW] — **bramka: user ogłasza koniec fazy portfolio**
- [ ] Prototyp offline `src/tools/proto_pifs.py` (NIE silnik): bloki range 75 px, pula domain 150→75 px × 8 izometrii, cechy 5×5 LAB + cKDTree, least-squares kontrast/jasność domain→range. Cel: zweryfikować JEDYNE ryzyko dyskwalifikujące — czy wynik kolapsuje do „rozmytego oryginału".
- **DoD:** 3 obrazy testowe (portret/krajobraz/tekstura) + metryka dystansu wynik↔oryginał + werdykt usera **GO/NO-GO**. NO-GO = koniec tematu (wpis do „Odrzuconych" w MEMORY.md); nie budować silnika na zapas.

### O3b — pifs: silnik — `feat(engine)` ~3-4 dni [HIGH] — **bramka: GO z O3a**
- [ ] `src/engine_pifs.py` strukturą lustrzany do `engine_smart` (ta sama architektura co obecne silniki); cache indeksu domain per obraz (hash pliku → pkl w `data/`), by nie łamać modelu „indeks raz, render szybko" przy powtórnych renderach.
- **DoD:** testy jednostkowe (izometrie, least-squares, determinizm); render 8K bez OOM (RAM 32 GB, profil jak A1).

### O3c — pifs: GUI/CLI — `feat(gui)` ~2 dni [LOW] — **bramka: akcept O3b**
- [ ] Trzecia zakładka obok Smart/Typo + `--engine pifs` w CLI; podpis eksponatu (WOW intelektualny wymaga wyjaśnienia — tekst do galerii).
- **DoD:** pełny przepływ GUI→render→DZI; testy CLI; werdykt usera.

## Tablica postępu

| Sprint | Status | Commit | Werdykt usera |
|---|---|---|---|
| F1a trójfazowa pętla | ☐ | — | — |
| F1b hilbert_flow | ☐ | — | — |
| F2a quadtree rdzeń | ☐ | — | — |
| F2b quadtree GUI | ☐ | — | — |
| F3 crossfade | ☐ | — | — |
| F4a zoom przygotowanie | ☐ | — | — |
| F4b zoom orkiestracja | ☐ | — | — |
| **CHECKPOINT** | ☐ | — | decyzja: bramka O2 + wybór artefaktu |
| O1 reveal DLA | ☐ | — | — |
| O2a veins rdzeń | ☐ | — | — |
| O2b veins GUI | ☐ | — | — |
| O3a pifs spike | ☐ | — | GO / NO-GO |
| O3b pifs silnik | ☐ | — | — |
| O3c pifs GUI | ☐ | — | — |
