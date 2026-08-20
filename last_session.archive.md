## ═══ Sesja zarchiwizowana [2026-08-15 12:15] ═══

# last_session.md

**Sesja:** 2026-08-15 · ~10:30-12:15
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 7eb3433 @ main (2 commity PRZED origin/main — push nie wykonany)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Wdrożyć karę antypowtórzeniową ograniczoną tolerancją ΔE w `_do_render`
(`src/engine_smart.py`, pętla scoringu ok. linii 4247).**

Konkretnie: dziś `score = base_d + used_counts[idx]**2 * freq_penalty * 0.001`
stosuje się do KAŻDEGO z 50 kandydatów top-K bez ograniczenia, przez co w płaskim
niebie kara wypycha wybór poza kafle zbliżone kolorem i silnik sięga po ciemne.
Zmiana: policzyć `d_best = min(base_d)` w danym sektorze i nakładać karę wyłącznie
na kandydatów spełniających `base_d <= d_best * (1 + tol)` (albo `base_d - d_best <=
tol_abs`), a pozostałych nie ruszać — kara nigdy nie może przeważyć nad progiem
wierności koloru. Dobrać `tol` empirycznie: `freqpen_probe.py --res 8K` daje gotową
metrykę (sky_std + ciemne% + dE + powtarzalność z `save_used_tiles` w jednej tabeli).
Cel: sky_std @8K blisko 3,96 (poziom fp=0) przy max powtórzeń ≲ 10 (fp=0 daje 218).

⚠ Zmiana dotknie WSZYSTKICH renderów ⇒ regeneracja goldenów. Przed startem upewnij
się, że user to akceptuje — pomiar jest zrobiony i jednoznaczny, ale sama zmiana
silnika nie została jeszcze zatwierdzona.

Kontekst: to jedyna pozycja blokująca galerię 16K (E8 krok 3). Sesja rozstrzygnęła
pomiarowo, że winowajcą szumu w niebie jest `freq_penalty`, a nie blend/tint —
i że strojenie samej stałej nie działa (fp=10 daje −31% @2K, ale −1,6% @8K).

---

## Co zrobiono w tej sesji

### Szum w niebie — rozstrzygnięty pomiarowo (punkt ① z 2026-07-26 ZAMKNIĘTY)

- ✓ **Sweep blend/tint wykonany** (`square` @2K, PYTHONHASHSEED=1, scale=0.75,
  grout thin/L1, edge_aware=ON, mirror=OFF, 7 renderów z baseline 0/0):
  monotonicznie, **BEZ kolana**. Maksimum dozwolonego zakresu (0,30/0,25) daje
  `sky_std` 6,43 wobec 8,89 przy 0/0 — tylko **−28%** i wciąż **4,9× oryginał**
  (poziom odniesienia zmierzony: **1,307**).
- ✓ **Znaleziony confound: grout zanieczyszczał metrykę.** `draw_grout` rysuje PO
  blendzie jako twarda nakładka, więc czarne linie L\*≈0 w niebie L\*≈69 wchodzą
  wprost do `sky_std`: grout „thin" = **~32% wariancji** płata (8,891 z groutem vs
  7,352 bez, identyczne ustawienia). Wszystkie 50 mozaik z analizy 26.07 miały
  grout ⇒ teza „wada wspólna dla wszystkich kształtów" była częściowo pomiarem fug.
  **Każdy pomiar jakości dopasowania rób z `grout_preset=None`.**
- ✓ **Zidentyfikowany winowajca: `freq_penalty`.** Bez groutu i post-processingu
  @2K: 7,352 (fp=30) → 5,048 (fp=10) → 3,644 (fp=0).
- ✓ **Weryfikacja @8K ODWRÓCIŁA rekomendację.** Przy 8034 komórkach zamiast 546:
  fp=10 daje **−1,6%** (10,933 → 10,758), czyli nic; dopiero fp=0 schodzi do 3,958
  (2,94× oryginał, ciemne piksele 6,52% → 0,72%, dE 17,34 → 13,33), ale max użyć
  jednego kafla skacze **5 → 218** z 8034, a top-10 kafli = 17,3% wklejeń.
  Efekt jest binarny, nie ciągły. **Nigdy nie kalibruj `freq_penalty` na 2K.**

### Widoczność w Google (na wyraźne polecenie usera: „wykonaj wszystkie punkty")

- ✓ **Zdiagnozowane empirycznie**, dlaczego repo nie wychodzi w wyszukiwaniu:
  brak backlinków (~80% problemu), strona Pages była samą aplikacją OSD (zero
  tekstu do indeksacji), osierocone `posts/*.md`, brak sitemapy i zgłoszenia w GSC.
- ✓ **`docs/` przebudowane** (commit `420dd1d`): `index.html` = strona lądowania
  z prozą + canonical/OG/JSON-LD; przeglądarka OSD → **`viewer.html`** (1:1 +
  przycisk Home); wpisy jako HTML z `hreflang` en/pl; `sitemap.xml`; `style.css`;
  `img/` z `og-cover.jpg` 1200×630.
- ✓ **Zweryfikowane wizualnie w Chrome** (lokalny serwer): landing, wpis
  i przeglądarka renderują się poprawnie; 0 złamanych odnośników lokalnych;
  wszystkie 4 URL-e z sitemapy istnieją. Naprawiony zawijający się nagłówek viewera.
- ✓ **Domknięty backlog README** (commit `7eb3433`): tabela kształtów wymieniała
  9 pozycji przy rejestrze 50 → sekcja „Tile shapes"/„Kształty kafelków",
  5 rodzin, 12+15+6+6+11=50. Linki galerii przestawione na `/viewer.html`.
- ✓ **`PLAN_SEO.md`** — diagnoza + instrukcja Google Search Console krok po kroku
  (wersja dla laika) + gotowe teksty 4 postów (Show HN z pierwszym komentarzem,
  r/generative, r/Python, dev.to z canonicalem). **Nic nie zostało opublikowane.**
- ✓ **`C:\Users\plazo\Desktop\Neural-Mosaic_google_console.md`** — samodzielna
  instrukcja GSC na pulpicie usera (z alternatywną metodą „Plik HTML" i listą
  kontrolną). Poza repo, nie wersjonowana.
- ✓ **567 testów przechodzi** (72 s), zero regresji.
- ✓ **2 commity** (`420dd1d`, `7eb3433`) — **BEZ push**.

## Co zostało (backlog sesji)

- ⚠ **PUSH NIEWYKONANY** — `main` jest 2 commity przed `origin/main`. Dopóki nie
  ma pusha, nowa strona NIE jest live, więc weryfikacja GSC nie ma szans przejść.
- ⟳ **Czekam na tag `<meta name="google-site-verification" …>` od usera** —
  po otrzymaniu: wstawić do `docs/index.html`, commit, push, dać znać, kiedy
  klikać „Zweryfikuj" (GitHub Pages przebudowuje ~1-2 min).
- ⟳ **Punkt 4 SEO (backlinki) NIEWYKONANY z rozmysłem** — publikacja szłaby pod
  nazwiskiem usera. Teksty gotowe w `PLAN_SEO.md`, czekają na jego decyzję.
- ⚠ **`output/shapes/…_kites_….jpg` NIEAKTUALNY** — plik z 22.07, geometria
  zmieniona 26.07. Wymaga renderu @8K.
- ⟳ **E8 krok 3: galeria 16K** — wciąż zablokowana, ale blokada zmieniła naturę:
  to już nie „ustalić blend/tint", tylko „naprawić `freq_penalty`".
- ⟳ **Driver renderu wciąż efemeryczny** — `render_all_shapes.py` odtwarzany 3×.
  Rozważyć `src/tools/render_shapes_batch.py`.
- ⟳ Pozostałe rekomendacje z 2026-07-26: usunąć `bloom` → rename `escher_lizard`
  → kalibracja `scale` dla 4 kształtów jednorodnych → A/B `sierpinski` →
  grout=off dla kształtów o dużym udziale tuszu.
- ⟳ medium=3px / thick=5px wciąż NIEzweryfikowane na realnym renderze.
- ⟳ Hero panorama: lokalna, NIE opublikowana (Wariant C odłożony).
- ⟳ (przeniesione) PLAN_FRACTAL F1a.

## Aktywne pliki

- `docs/index.html` — strona lądowania (NOWA rola; był tu viewer).
- `docs/viewer.html` — przeglądarka OSD (przeniesiona z `index.html`).
- `docs/style.css`, `docs/sitemap.xml`, `docs/img/` (7 plików) — nowe.
- `docs/posts/aperiodic-monotile-mosaic{,.pl}.html` — nowe; pliki `.md` ZOSTAJĄ.
- `docs/robots.txt` — komentarz o tym, że plik w podkatalogu projektu jest ignorowany.
- `README.md`, `README.pl.md` — sekcja kształtów + linki na `/viewer.html`.
- `PLAN_SEO.md` — nowy, kanoniczny plan SEO.
- `MEMORY.md` — 2 nowe wpisy [2026-08-15].
- `src/engine_smart.py` — **NIETKNIĘTY** (zmiana `freq_penalty` czeka na decyzję).
- EFEMERYCZNE (scratchpad): `blend_tint_sweep.py` (sweep + sky_std + dE),
  `grout_confound.py` (grout on/off), `freqpen_probe.py --res {2K,4K,8K,16K}`
  (renderuje + liczy sky_std, ciemne%, dE i powtarzalność w jednej tabeli —
  **najbardziej wart utrwalenia**), `repeat_cost.py` (wchłonięty przez freqpen_probe).

## Otwarte pytania

- **Czy zatwierdzasz zmianę kary antypowtórzeniowej w silniku?** Pomiar jednoznaczny,
  ale zmiana dotyka wszystkich renderów i wymusi regenerację goldenów.
- **Kiedy push?** 2 commity czekają lokalnie; bez pusha strona nie jest live.
- **Tag weryfikacyjny GSC** — user miał go wkleić po dodaniu usługi w Search Console.
- **`bloom`** — rekomenduję usunięcie (dE 11,47 vs 11,44 dla `phyllotaxis`);
  user go NIE wskazał, więc został.
- **`escher_lizard`** — rename czy prawdziwa sylwetka? Rekomenduję rename.
- **Kalibracja `base_s`** — przemierzyć średnią ważoną polem `Σa²/Σa`, nie medianą.
- **Publikacja hero panoramy** (Wariant C) — wciąż otwarta.

## Do MEMORY.md (przeniesiono)

- **`MEMORY.md` → Aktywne TODO, wpis [2026-08-15]** „Szum w niebie ROZSTRZYGNIĘTY
  pomiarowo" — komplet liczb 2K/8K, confound groutu, pułapka skali, kierunek naprawy.
- **`MEMORY.md` → Aktywne TODO, wpis [2026-08-15]** „Widoczność w Google" —
  co zrobione w `docs/`, pułapka `robots.txt` w podkatalogu, co zostało dla usera.
- **Pamięć długoterminowa:** `project_freq_penalty_sky_noise.md` (NOWY) —
  freq_penalty jako źródło szumu, grout jako confound pomiaru, zakaz kalibracji
  na 2K; `project_docs_site_seo.md` (NOWY) — nowa struktura `docs/`,
  `index.html` = landing i `viewer.html` = przeglądarka (nie cofać),
  robots.txt w podkatalogu ignorowany.


## ═══ Sesja zarchiwizowana 2026-08-15 12:13 ═══

# last_session.md

**Sesja:** 2026-07-27 · ~21:20-21:48
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** e4c0153 @ main (zsynchronizowane z origin/main)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Sweep blend/tint na `square` @2K — pomiar szumu w płaskim niebie.**

Konkretnie: wyrenderuj `square` @2K, `PYTHONHASHSEED=1`, scale=0.75,
grout_preset="thin", grout_level=1, edge_aware=ON, mirror=OFF, input
`input/IMG_20220727_095216.jpg` — sześć wariantów: blend ∈ {0.10, 0.20, 0.30}
× tint ∈ {0.10, 0.25}. Dla każdego policz **odchylenie L\* w płacie nieba**
(patch: `[0.03h:0.13h, 0.03w:0.30w]` po konwersji `skimage.color.rgb2lab`,
kanał 0) i porównaj z poziomem odniesienia oryginału = **1,29**. Skrypt
pomiarowy do odtworzenia: `quality.py` ze scratchpada (deltaE + sky std,
opisany w MEMORY.md → Aktywne TODO [2026-07-26] punkt ①).

Kontekst: mozaiki mają szum w niebie **6,3–9,9 vs 1,29 w oryginale (5–8×)** i
jest to jedyna wada **wspólna dla wszystkich 50 kształtów** — czyli tkwi w
dopasowaniu/blendzie, nie w geometrii. Jest to najtańsza dźwignia (zero zmian w
kodzie, metryka gotowa) i **gatuje galerię 16K**: nie ma sensu renderować 50
obrazów @16K przed ustaleniem właściwych blend/tint. Jeśli sweep nie da kolana
— następny podejrzany to `freq_penalty`.

⚠ Rekomendacja moja z sesji 2026-07-26, **wciąż niezatwierdzona przez usera**
— ta sesja była audytem (patrz niżej), nie dotknęła priorytetu. Przed
rozpoczęciem sweepu upewnij się, że to nadal to, co user chce zrobić dalej.

---

## Co zrobiono w tej sesji

- ✓ **Audyt collateral damage cullu 59→50** (`e4c0153`): sprawdzone, na jakie
  PRZEŻYŁE kształty wpłynęło usunięcie 9 kształtów (`077fec3`, sesja
  2026-07-26). Zbudowane domknięcie tranzytywne grafu wywołań (AST) na
  wersji SPRZED usunięcia — 14 kształtów dzieliło helpery z usuniętymi:
  `_sun_arc` → `nautilus`/`scales`/`truchet`/`truchet_hex`/`voderberg`;
  rodzina Voronoi (`_emit_cells`/`_voronoi_cells`/`_lloyd_relax`/
  `_vogel_points`/`_graded_sunflower`) → `bloom`/`pebbles`/`phyllotaxis`/
  `voronoi`/`sunflower_grande`/`sunflower_grande_inverse`/`sunflower_rings`/
  `sunflower_soft`; `_sierpinski_cells`/`_tri_outside` → `sierpinski`.
- ✓ **Wynik: ZERO regresji.** Zbiór faktycznie usuniętych helperów (24)
  pokrył się CO DO JEDNEGO ze zbiorem policzonym jako „wyłączne dla
  usuniętych kształtów" — cięcie było chirurgicznie poprawne.
- ✓ **A/B geometrii** (stary moduł załadowany obok nowego przez
  `importlib.util.spec_from_file_location`, prefiks `src.` obowiązkowy):
  14 zagrożonych kształtów × 3 kadry = **42/42 strumienie wielokątów
  bit-w-bit identyczne**.
- ✓ **Pokrycie kadru** (maska FLOAT ss=4 + shoelace): pole/kadr = 1,0000
  dla wszystkich 14, dziury 0,000% (`nautilus` 0,008% / `voderberg` 0,012%
  = subpikselowa kwantyzacja łuków, znany zaakceptowany precedens).
- ✓ **20 narzędzi `src/tools/gen_*.py`** importują się bez błędu.
- ✓ **Jedna realna wada znaleziona i naprawiona**: docstring `_sun_arc`
  wymieniał 4 konsumentów zamiast 5 (brakował `truchet_hex`). Poprawiony +
  dopięty test `TestSunArcConsumers` (liczy konsumentów z AST, porównuje z
  docstringiem). Bramka **zweryfikowana mutacyjnie** — po celowym usunięciu
  `truchet_hex` z docstringa test czerwienieje.
- ✓ **567 testów przechodzi** (565 + 2 nowe).
- ✓ **Zapisano instrument audytu do pamięci** —
  `project_removal_collateral_audit.md` (domknięcie AST + A/B geometrii jako
  powtarzalna procedura na przyszłe usuwanie kształtów).
- ✓ **Commit + push na origin/main** (`e4c0153`).

## Co zostało (backlog sesji)

- ⚠ **`output/shapes/…_kites_….jpg` NIEAKTUALNY** — plik z 22.07 22:00,
  geometria zmieniona 26.07. Wymaga ponownego renderu @8K (świadomie odłożone).
- ⟳ **README EN+PL: tabela kształtów wymienia 9 pozycji, rejestr ma 50.**
  Na ścieżce krytycznej przed publikacją galerii.
- ⟳ **E8 krok 3: galeria 16K** — zablokowana do czasu rozstrzygnięcia blend/tint
  (patrz NASTĘPNY KROK).
- ⟳ **Driver renderu wciąż efemeryczny** — `render_all_shapes.py` odtwarzany już
  3× ze scratchpada. Rozważyć utrwalenie jako `src/tools/render_shapes_batch.py`.
- ⟳ Rekomendacje z analizy 2026-07-26 (kolejność wg mojej oceny): sweep
  blend/tint → usunąć `bloom` → rename `escher_lizard` → kalibracja `scale`
  dla 4 kształtów jednorodnych → A/B `sierpinski` → grout=off dla kształtów
  o dużym udziale tuszu.
- ⟳ medium=3px / thick=5px wciąż NIEzweryfikowane na realnym renderze.
- ⟳ Hero panorama: lokalna, NIE opublikowana (Wariant C odłożony).
- ⟳ (przeniesione) PLAN_FRACTAL F1a.

## Aktywne pliki

- `src/engine_smart.py` — docstring `_sun_arc` poprawiony (5 konsumentów:
  nautilus/scales/truchet/truchet_hex/voderberg).
- `tests/test_smart_engine.py` — nowa klasa `TestSunArcConsumers` (2 testy):
  domknięcie AST konsumentów `_sun_arc` vs docstring; strażnik przed cichym
  ponownym usunięciem współdzielonego helpera.
- `MEMORY.md` — 1 nowy wpis [2026-07-27].
- EFEMERYCZNE (scratchpad, narzędzia audytu do odtworzenia w razie potrzeby):
  `astdiff.py` (diff funkcji po AST, nie po regexie — regex myli komentarze
  między funkcjami z ciałem), `shared_deps.py` (domknięcie grafu wywołań +
  przecięcie z usuniętymi), `geom_ab.py` (A/B strumienia wielokątów stary/nowy
  moduł), `cover_ab.py` (pokrycie FLOAT ss=4 + shoelace).

## Otwarte pytania

- **Od czego zacząć następną sesję** — wciąż nierozstrzygnięte z 2026-07-26:
  przedstawiłem 6 rekomendacji z priorytetem, user nie wybrał. Ta sesja była
  audytem na wyraźne życzenie usera, nie decyzją o priorytecie.
- **`bloom`** — rekomenduję usunięcie (nierozróżnialny od `phyllotaxis` w
  mozaice: dE 11,47 vs 11,44); user go NIE wskazał do usunięcia, więc został.
- **`escher_lizard`** — rename czy prawdziwa sylwetka? Rekomenduję rename.
- **Kalibracja `base_s`** — przed jakąkolwiek zmianą przemierzyć średnią ważoną
  polem `Σa²/Σa`, nie medianą (mediana kłamie dla kształtów bimodalnych).
- **Publikacja hero panoramy** (Wariant C) — decyzja usera, wciąż otwarta.

## Do MEMORY.md (przeniesiono)

- **`project_removal_collateral_audit.md`** (NOWY, [2026-07-27]): instrument
  audytu „co jeszcze ucierpiało" po usunięciu kształtów — domknięcie
  tranzytywne grafu wywołań AST (przecięcie z usuniętymi = lista zagrożonych)
  + A/B geometrii przez `importlib.util.spec_from_file_location`. Wynik
  audytu cullu 59→50: zero regresji, 14/14 kształtów bit-w-bit identyczne.
  Pułapka narzędziowa: split pliku po `^def` przypisuje komentarze między
  funkcjami do funkcji powyżej — używać `ast.get_source_segment`, nie regexa.
  `ShapeSpec.generator` bywa `None` (legacy grid) — każdy przebieg po
  `SHAPE_MODES` musi to przeskoczyć.

---

## ═══ Sesja zarchiwizowana 2026-07-27 21:48 ═══

# last_session.md

**Sesja:** 2026-07-26 · 21:00-21:55
**Punkt odniesienia (git):** 75cbf8b @ main
**Status:** ✓ Zakończona poprawnie

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Sweep blend/tint na `square` @2K — pomiar szumu w płaskim niebie.**

Konkretnie: wyrenderuj `square` @2K, `PYTHONHASHSEED=1`, scale=0.75,
grout_preset="thin", grout_level=1, edge_aware=ON, mirror=OFF, input
`input/IMG_20220727_095216.jpg` — sześć wariantów: blend ∈ {0.10, 0.20, 0.30}
× tint ∈ {0.10, 0.25}. Dla każdego policz **odchylenie L\* w płacie nieba**
(patch: `[0.03h:0.13h, 0.03w:0.30w]` po konwersji `skimage.color.rgb2lab`,
kanał 0) i porównaj z poziomem odniesienia oryginału = **1,29**. Skrypt
pomiarowy do odtworzenia: `quality.py` ze scratchpada (deltaE + sky std,
opisany w MEMORY.md → Aktywne TODO [2026-07-26] punkt ①).

Kontekst: mozaiki mają szum w niebie **6,3–9,9 vs 1,29 w oryginale (5–8×)** i
jest to jedyna wada **wspólna dla wszystkich 50 kształtów** — czyli tkwi w
dopasowaniu/blendzie, nie w geometrii. Jest to najtańsza dźwignia (zero zmian w
kodzie, metryka gotowa) i **gatuje galerię 16K**: nie ma sensu renderować 50
obrazów @16K przed ustaleniem właściwych blend/tint. Jeśli sweep nie da kolana
— następny podejrzany to `freq_penalty`.

⚠ Rekomendacja moja, **niezatwierdzona przez usera** — user wywołał /end zaraz
po jej przedstawieniu, bez wyboru punktu startowego.

---

## Co zrobiono w tej sesji

- ✓ **Selekcja finalna: rejestr 59 → 50 kształtów** (`077fec3`). Usunięte
  CAŁKOWICIE z projektu (generatory, `SHAPE_MODES`, goldeny, testy, schematy
  `assets/shape_schemes/`, wpisy w `src/tools/gen_*_schemes.py`, stare mozaiki):
  `rhombs_funnel`, `rhombs_nopole`, `rhombs_star`, `sierpinski_carpet`,
  `sierpinski_d`, `sunburst`, `sunflower_disc`, `sunflower_grande_xl`,
  `sunflower_grande_soft`.
- ✓ **−234 linie martwego kodu** — cała maszyneria log-spiralna
  (`_log_quads`/`_log_mesh`/`_bridge`/`_rosette`/`_emit_polys`/`_rh_*`) była
  wyłącznie pod `rhombs_*`; `_sierp4` osierocony po `sierpinski_d`.
- ✓ **`_sun_arc` PRZYWRÓCONY** — mimo nazwy od `sunburst` jest współdzielony
  przez `scales`/`nautilus`/`voderberg`/`truchet`; usunięcie go wywaliło
  25 testów w kształtach nietkniętych.
- ✓ **Kolejność `SHAPE_MODES` → ALFABETYCZNA**; `shape_names()` = 50 nazw.
- ✓ **Dropdown kształtów w GUI w 2 kolumnach** (25+25, bez przewijania) —
  `_spread_dropdown_columns()` w `gui.py`; CTk dropdown to `tkinter.Menu`,
  który wspiera per-wpis `columnbreak`. Zweryfikowane:
  `ammann_beenker..puzzle_classic` | `puzzle_hex..weave`.
- ✓ **`kites` — ząbkowanie krawędzi NAPRAWIONE** (`5f0e5cd`): filtr zmieniony
  z „centroid w kadrze" na „bbox przecina kadr". Pomiar: **2,349% → 0,000%**
  niepokrytego kadru (pasmo dolne 12,57% → 0). Formalny test partycji: suma
  pól przyciętych = **1 080 000,0 = dokładnie pole kadru**.
- ✓ **Zlikwidowane potrojenie przebiegu siatki kites** — jeden `_kite_lattice()`
  + modułowy `_kite_poly()`; konsumują go generator, gałąź `_do_render` i
  `_grout_cells_kites`. Goldeny `kites` zregenerowane, 4 nowe testy.
- ✓ **Sweep pokrycia po wszystkich 53 kształtach polygon** — `kites` był
  JEDYNYM z wadą (reszta 0,000%, `girih` 0,011% = znana otoczka).
- ✓ **Analiza krytyczna 50 mozaik** — 7 punktów z pomiarami (szum w niebie,
  niewidoczność kształtu przy oglądaniu całości, rozjazd ziarna, wielkie
  komórki `sierpinski`, `escher_lizard`, grout, `bloom`) + rekomendacja dla
  każdego. Wszystko w MEMORY.md → Aktywne TODO [2026-07-26].
- ✓ **MEMORY.md zaktualizowane** (`75cbf8b`) + naprawiony drift komentarza w
  `test_grout_engine.py`.
- ✓ **565 testów przechodzi**; oba commity kodu zweryfikowane jako zielone
  OSOBNO (nie tylko stan końcowy).
- ✓ **Push na origin/main** — 8 commitów.

## Co zostało (backlog sesji)

- ⚠ **`output/shapes/…_kites_….jpg` NIEAKTUALNY** — plik z 22.07 22:00,
  geometria zmieniona 26.07. Wymaga ponownego renderu @8K (świadomie odłożone).
- ⟳ **README EN+PL: tabela kształtów wymienia 9 pozycji, rejestr ma 50.**
  Było w backlogu, teraz na ścieżce krytycznej przed publikacją galerii.
- ⟳ **E8 krok 3: galeria 16K** — zablokowana do czasu rozstrzygnięcia blend/tint
  (patrz NASTĘPNY KROK).
- ⟳ **Driver renderu wciąż efemeryczny** — `render_all_shapes.py` odtwarzany już
  3× ze scratchpada. Rozważyć utrwalenie jako `src/tools/render_shapes_batch.py`.
- ⟳ Rekomendacje z analizy (kolejność wg mojej oceny): sweep blend/tint →
  usunąć `bloom` → rename `escher_lizard` → kalibracja `scale` dla 4 kształtów
  jednorodnych → A/B `sierpinski` → grout=off dla kształtów o dużym udziale tuszu.
- ⟳ medium=3px / thick=5px wciąż NIEzweryfikowane na realnym renderze.
- ⟳ Hero panorama: lokalna, NIE opublikowana (Wariant C odłożony).
- ⟳ (przeniesione) PLAN_FRACTAL F1a.

## Aktywne pliki

- `src/engine_smart.py` — rejestr 50 alfabetycznie, `_kite_lattice`/`_kite_poly`,
  usunięte generatory + log-spirale, `_sun_arc` przywrócony.
- `src/gui.py` — `_spread_dropdown_columns()`, `import tkinter`.
- `tests/test_grout_engine.py` — sekcja „kites: the frame edge", helpery
  `_shoelace`/`_clip_to_frame`, `_SIERP_GENS` = 1 wpis.
- `tests/test_golden_shapes.py` — goldeny `kites` zregenerowane, 18 wpisów usuniętych.
- `src/tools/gen_e7_schemes.py`, `gen_sunflower_schemes.py`,
  `gen_extra_shape_schemes.py` — listy SPEC przycięte.
- `MEMORY.md` — 3 nowe wpisy [2026-07-26].
- `output/shapes/` — 50 mozaik 8K (gitignored); **kites nieaktualny**.
- EFEMERYCZNE (scratchpad): `coverage_sweep.py`, `quality.py`, `grain.py`,
  `kites_cover.py`, `contact.py`, `crops2.py`, `make_thumbs.py`.

## Otwarte pytania

- **Od czego zacząć następną sesję** — przedstawiłem 6 rekomendacji z priorytetem,
  user wywołał /end bez wyboru. NASTĘPNY KROK to moja rekomendacja, nie decyzja.
- **`bloom`** — rekomenduję usunięcie (nierozróżnialny od `phyllotaxis` w mozaice:
  dE 11,47 vs 11,44); user go NIE wskazał do usunięcia, więc został.
- **`escher_lizard`** — rename czy prawdziwa sylwetka? Rekomenduję rename.
- **Kalibracja `base_s`** — przed jakąkolwiek zmianą przemierzyć średnią ważoną
  polem `Σa²/Σa`, nie medianą (mediana kłamie dla kształtów bimodalnych).
- **Publikacja hero panoramy** (Wariant C) — decyzja usera, wciąż otwarta.

## Do MEMORY.md (przeniesiono)

- **Rozwiązane problemy** [2026-07-26]: ząbkowanie `kites` + META-LEKCJA
  „golden nie drgnął po celowej zmianie pikseli = dowód, że dotknięty kod NIE
  jest ścieżką produkcyjną" + odruch „grep nazwy kształtu przed zmianą
  geometrii" + formalny test partycji jako instrument.
- **Odrzucone podejścia** [2026-07-26]: lista 9 usuniętych kształtów (nie
  proponować ponownie) + pułapki usuwania (`_sun_arc`, log-spirale, `_sierp4`,
  `gen_e7_schemes`) + kolejność alfabetyczna + dropdown 2 kolumny.
- **Aktywne TODO** [2026-07-26]: analiza krytyczna 50 mozaik — 7 punktów z
  liczbami i rekomendacjami, w tym uwaga metodologiczna o `Σa²/Σa` vs mediana.
- **Architektura**: lista geometrii zastąpiona wskazaniem na `SHAPE_MODES`
  jako jedyne źródło prawdy (poprzednia 9-pozycyjna była nieaktualna).

## ═══ Sesja zarchiwizowana 2026-07-26 21:52 ═══

# last_session.md

**Sesja:** 2026-07-22 · 21:12-21:50
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** b91d42a @ main

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**E8 krok 3 — selekcja finalna usera.** User wybrał tryb „oglądam sam pliki":
przegląda 59 mozaik w `output/shapes/` i wróci z listą kształtów **do
ODRZUCENIA**. Po jej otrzymaniu: odtwórz driver renderu (analogiczny do
efemerycznego `render_all_shapes.py`, ale `resolution="16K"` i TYLKO zatwierdzone
kształty) → `output/gallery_16K/`. Te same parametry co batch 8K
(scale=0.75, blend=0.10, tint=0.10, grout_preset="thin", grout_level=1,
grout_style="solid", grout_color="black", edge_aware=ON, mirror=OFF,
`PYTHONHASHSEED=1`).

Kontekst: E8 krok 2 (render 59 kształtów @8K) ZAMKNIĘTY w tej sesji — 54 OK,
5 SKIP, 0 FAIL, 59/59 plików zdrowych (22,8-36,8 MB). Selekcja to ostatnia bramka
przed galerią 16K. UWAGA do obejrzenia przy selekcji: `sierpinski_carpet`
(22,8 MB = najmniejszy, potwierdza degenerację przy dużym base_s) oraz para
`bloom`↔`phyllotaxis` (kandydat do odrzucenia — bardzo podobne).

---

## Co zrobiono w tej sesji

- ✓ **E8 krok 2 ZAMKNIĘTY: render 59 kształtów @8K** — odtworzono efemeryczny
  driver `render_all_shapes.py` (scratchpad) wg specyfikacji z last_session,
  uruchomiono w tle z `PYTHONHASHSEED=1`, log `logs/render_shapes.log`.
  Wynik: **54 OK, 5 SKIP, 0 FAIL**, 59/59 plików w `output/shapes/`.
- ✓ **Sanity rozmiarów:** wszystkie 22,8-36,8 MB (brak pustych/uszkodzonych).
  Najmniejszy `sierpinski_carpet` (22,8 MB), największe `koch_island` (36,8),
  `dragon` (35,9), `koch_snowflake` (34,9).
- ✓ **Weryfikacja fixów z poprzedniej sesji na pełnym batchu:** grout thin =
  uniform level-1 zadziałał („drawing hierarchical → uniform (level 1 = each
  tile)"); mean-fill krawędzi bez regresji.
- ✓ **Sanity startowy:** potwierdzono że przerwany batch poprzedniej sesji
  zostawił dokładnie 5 gotowych kształtów; restart poprawnie je pominął.

## Co zostało (backlog sesji)

- ⟳ **E8 krok 3:** selekcja finalna usera → galeria 16K (NASTĘPNY KROK).
- ⟳ **Driver renderu wciąż efemeryczny** — `render_all_shapes.py` odtwarzany
  już 2× ze scratchpada. Rozważyć zapisanie na stałe jako
  `src/tools/render_shapes_batch.py` (z argumentami: resolution, grout preset,
  output dir) — do decyzji usera.
- ⟳ **README EN+PL:** tabela 59 kształtów + dokumentacja
  `--grout-style`/`--grout-color`/`--grout`/`--grout-level`; panorama 4,0 GB
  osobno od 3,9 GB @16K.
- ⟳ Hero panorama: lokalna, NIE opublikowana (Wariant C odłożony).
- ⟳ (przeniesione) PLAN_FRACTAL F1a; escher_lizard sylwetka.
- ⟳ medium=3px / thick=5px wciąż NIEzweryfikowane na realnym renderze (batch
  używał tylko thin).

## Aktywne pliki

- `output/shapes/` — 59 mozaik 8K gotowych (gitignored).
- `logs/render_shapes.log` — pełny log batcha (gitignored).
- EFEMERYCZNE (scratchpad, do odtworzenia lub utrwalenia):
  `render_all_shapes.py`.
- (bez zmian w kodzie — HEAD niezmieniony od `b91d42a`).

## Otwarte pytania

- **`sierpinski_carpet` degeneracja** — obejrzeć w 100% zoom przy selekcji;
  jeśli kilka wielkich kwadratów → kandydat do odrzucenia lub fix base_s.
- **`bloom` vs `phyllotaxis`** — obejrzeć obok siebie; `bloom` kandydat do
  odrzucenia.
- **Rodziny wariantów** (`sunflower_*`×7, `rhomb*`, `sierpinski*`×3, `koch_*`) —
  czy trzymać wszystkie do galerii, czy przerzedzić.
- **Publikacja hero panoramy** (Wariant C) — decyzja usera.

## Do MEMORY.md (przeniesiono)

- Nic nowego — sesja czysto wykonawcza (batch renderu), bez decyzji
  architektonicznych ani rozwiązań trudnych problemów. Empiryczne potwierdzenie
  degeneracji `sierpinski_carpet` odnotowane w Otwartych pytaniach (do
  rozstrzygnięcia przy selekcji, nie utrwalane jako trwały fakt).

## ═══ Sesja zarchiwizowana [2026-07-22 21:45] ═══

# last_session.md

**Sesja:** 2026-07-21 · wieczór (~21:00-23:12)
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 0c67c71 @ main

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Dokończ render 59 kształtów @8K** — pozostało 56 (5 już gotowych w
`output/shapes/`: square, rectangle_3x1, brick_wall, hexagon, hexagon_romb).

UWAGA: driver `render_all_shapes.py` był w scratchpadzie (EFEMERYCZNY, zniknął).
Odtwórz go z tych parametrów (wspólne dla wszystkich 59, wybór usera):
- input `input/IMG_20220727_095216.jpg` → `output/shapes/`
- `SmartEngine(index_path="data/smart_index.pkl")`;
  `settings["edge_aware"]=True`, `settings["allow_mirror"]=False`
- `create_mosaic(inp, out, "8K", shape, tile_scale=0.75, blend_strength=0.10,`
  `tint_strength=0.10, grout_preset="thin", grout_level=1, grout_style="solid",`
  `grout_color="black")` dla każdego `shape` z `shape_names()`
- nazwa: `IMG_20220727_095216_smart_8K_{shape}_grout-thin.jpg`, skip-if-exists
- uruchom z `PYTHONHASHSEED=1`, w tle, log do `logs/render_shapes.log`
- grout thin = **1px** (poziom 1 = uniform po fixie); ~1-3 h (sierpinski_carpet
  najdłużej)

Kontekst: to E8 krok 2 (seria mozaik testowych). Po pełnym renderze → **selekcja
finalna usera** (E8 krok 3) → galeria 16K. Sesja zeszła na naprawę 4 wad groutu/
krawędzi wykrytych na pierwszych renderach, dlatego pełny batch niedokończony.

---

## Co zrobiono w tej sesji

- ✓ **E8 krok 1: `gen_shape_montage.py`** (`99a254f`) — montaż 8×8 wszystkich 59
  schematów (`assets/shape_montage.png`, 2258×2546), kolejność = `shape_names()`,
  bramka 59/59 PNG bez braków. Deliverable do selekcji.
- ✓ **Fix 1 — ciemne pół-kafle na offsetowych krawędziach** (`0c67c71`):
  czarny padding częściowego cropu zatruwał cechę LAB → dopasowanie ciemnego
  kafla (`brick_wall` lewa krawędź). Mean-fill średnią cropu + paste w prawdziwej
  pozycji (branch grid + hexagon_romb). Goldeny `square`+`hexagon_romb` regen.
- ✓ **Fix 2/3 — grout „each tile" pokazywał struktury wyższego rzędu**:
  `_apply_grout` przy `min_level==1` rysuje teraz UNIFORM (wszystkie szwy = L1),
  nie stopniowane L1<L2<L3. Gradacja tylko przy jawnym poziomie ≥2.
- ✓ **Fix 4 + presety grubości** (A/B na realnym 8K): thin/medium/thick =
  **1/3/5 px** @ base_s=75. `PRESETS` w `src/grout.py`.
- ✓ **329 testów zielonych**; goldeny zregenerowane (4 hashe, udokumentowane).
- ✓ 3 sample 8K zweryfikowane wizualnie (square/brick/hexagon) + narzędzie
  porównawcze szerokości 1-10px (`output/grout_width_compare.png`).

## Co zostało (backlog sesji)

- ⟳ **E8 krok 2:** dokończyć render 56 pozostałych kształtów (NASTĘPNY KROK).
- ⟳ **E8 krok 3:** selekcja finalna usera → galeria 16K.
- ⟳ **README EN+PL:** tabela 59 kształtów + dokumentacja
  `--grout-style`/`--grout-color`/`--grout`/`--grout-level`; panorama 4,0 GB
  osobno od 3,9 GB @16K.
- ⟳ Hero panorama: lokalna, NIE opublikowana (Wariant C odłożony).
- ⟳ (przeniesione) PLAN_FRACTAL F1a; escher_lizard sylwetka.

## Aktywne pliki

- `src/engine_smart.py` — `_apply_grout` (uniform level-1), branch grid +
  hexagon_romb (mean-fill krawędzi).
- `src/grout.py` — `PRESETS` = 1/3/5 px.
- `tests/test_golden_shapes.py` — 4 goldeny regen (square/hexagon_romb ×2).
- `src/tools/gen_shape_montage.py` — NOWE (zacommitowane).
- `output/shapes/` — 5 mozaik gotowych; `output/grout_width_compare.png`.
- EFEMERYCZNE (scratchpad, do odtworzenia): `render_all_shapes.py`,
  `grout_width_compare.py`.

## Otwarte pytania

- **medium=3px / thick=5px NIEzweryfikowane na realnym renderze** — wybrane tylko
  na porównaniu 1-10px; thin=1px potwierdzony na 3 samplach. Batch używa tylko
  thin, więc nie blokuje.
- **Selekcja finalna kształtów** (E8) — kandydat do odrzucenia: `bloom`
  (subtelny, blisko `phyllotaxis`).
- **`sierpinski_carpet` degeneruje się** przy dużym base_s (kilka wielkich
  kwadratów) — obejrzeć w docelowej rozdzielczości.
- **Publikacja hero panoramy** (Wariant C) — decyzja usera.

## Do MEMORY.md (przeniesiono)

- **repo MEMORY.md:** Rozwiązane problemy [2026-07-21] „Trzy wady wykryte dopiero
  na realnym renderze 8K" (mean-fill krawędzi + grout level-1 uniform + presety
  1/3/5px, base_s niezależne od rez).
- **auto-memory:** `project_grout_edge_uniform.md` (NOWY).

