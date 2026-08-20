# last_session.md

**Sesja:** 2026-08-20 · ~21:20-23:05
**Status:** ✓ Zakończona poprawnie
**Punkt odniesienia (git):** 68c8b33 @ main (zsynchronizowane z origin/main — push wykonany)

---

## ▸ NASTĘPNY KROK (zacznij tutaj)

**Dosypać zdjęcia do biblioteki, przebudować indeks (`python -m src.indexer_smart`),
a POTEM przemierzyć `freq_tolerance_de` sondą przy nowej bibliotece.**

Konkretnie, w tej kolejności:
1. User dokłada zdjęcia do `data/library_public/tiles/` (dziś 421 296 + 32 370 private).
2. `python -m src.indexer_smart` → nowy `data/smart_index.pkl` (bez tego silnik
   nowych kafli NIE widzi).
3. Sweep: sonda `freqtol_probe.py` (scratchpad, patrz niżej) na `--res 8K`,
   wartości `freq_tolerance_de ∈ {0.5, 1.0, 2.0, 4.0, 8.0}`, `freq_penalty=30`,
   `grout_preset=None`, bez blend/tint.
4. Ustawić `DEFAULT_FREQ_TOLERANCE_DE` w `src/engine_smart.py:63` na wybraną
   wartość. **Goldenów NIE trzeba regenerować** — fixture przypina 2.0 jawnie
   (`tests/test_golden_shapes.py:309`).

Kontekst: kalibracja z tej sesji oparła się o granicę BIBLIOTEKI, nie scoringu —
żeby zejść poniżej ~118 powtórzeń przy zachowaniu czystego nieba, brakowało kafli
w wąskim ΔE od koloru nieba. Dosypanie zdjęć przesuwa całą krzywą kompromisu,
więc kalibracja zrobiona PRZED reindeksem byłaby wyrzucona.

⚠ User zdecydował, że **NIE renderuje 50 kształtów** — zrobi własne rendery do
galerii README z nowych zdjęć. `output/shapes/` to materiał audytowy z lipca,
nigdzie niepodpięty; nie odtwarzać go i nie pisać drivera batcha.

---

## Co zrobiono w tej sesji

### 1. Kara antypowtórzeniowa ograniczona pasmem ΔE (commit `4b675cc`, 574 testy)

- ✓ **Wdrożone `freq_tolerance_de`** — budżet koloru (ΔE na komórkę cechy,
  domyślnie 2,0) wokół najlepszego dopasowania w sektorze. Kara przestawia
  kandydatów WEWNĄTRZ pasma, nigdy nie wypromuje kandydata spoza.
- ✓ **Plan z 15.08 skorygowany pomiarem: pasmo jest ABSOLUTNE, nie względne.**
  Względne zawodzi po obu stronach — zapada się przy dopasowaniu niemal
  dokładnym (zmierzone: pasmo 10% objęło 2 kafle z 41) i rozdyma się tam, gdzie
  dopasowanie jest słabe, dając karze najwięcej swobody w obszarach, które ma
  chronić.
- ✓ **Przelicznik ΔE→dystans wyprowadzony**, nie dobrany: `sqrt(25)·ΔE/100 = ΔE·0,05`.
  Kontrola: ciemny kafel `d=3,91` przy `ΔL≈65` → `5×0,65=3,25` + chroma ✓.
- ✓ **Nasycenie miękkie `w·p/(p+w)`** zamiast twardego `min(p,w)` — twarde
  obcięcie parkuje nadużywanych na tym samym wyniku, a remis po indeksie karmi
  wtedy w kółko jeden kafel.
- ✓ **Sonda z poprzedniej sesji odzyskana ze scratchpada** i użyta jako
  instrument — odtworzyła zapisane liczby z 15.08 co do cyfry (10,933 / 10,758 /
  3,958; max 5 / 7 / 218), więc pomiary są wprost porównywalne.
- ✓ **Kalibracja @8K** (freq_penalty=30, bez groutu, oryginał sky_std 1,346):

  | `freq_tolerance_de` | sky_std | ciemne% | dE | max powtórzeń |
  |---|---|---|---|---|
  | stare (bez ograniczeń) | 10,933 | 6,52 | 17,34 | 5 |
  | 0,5 | 3,951 | 0,72 | 13,48 | 164 |
  | 1,0 | 3,971 | 0,73 | 13,68 | 150 |
  | **2,0 (domyślne)** | **5,227** | **1,30** | **14,21** | **118** |
  | 4,0 | 7,925 | 3,44 | 15,10 | 70 |
  | 8,0 | 9,581 | 4,57 | 16,51 | 18 |

- ✓ **Uczciwy wynik: cel z planu (szum na poziomie fp=0 PRZY max≲10) jest
  NIEOSIĄGALNY tym pokrętłem** — to granica biblioteki. Zdobycz jakościowa:
  `freq_penalty` działał binarnie (5 vs 218 użyć), teraz jest ciągłe pokrętło.
- ✓ **Refaktor scoringu na jeden przebieg** (zamknięcie per sektor dokładało
  ~14 mln wywołań przy 16K) — zweryfikowany **bit-w-bit** na renderze 8K.
- ✓ Domyślna wyciągnięta do `DEFAULT_FREQ_TOLERANCE_DE` (była w dwóch miejscach).
- ✓ **7 nowych testów** (`tests/test_freq_tolerance.py`), w tym test kontrolny
  dowodzący, że fixture nadal odtwarza starą wadę przy `tol=1e9`.
- ✓ **90 goldenów zregenerowanych**; fixture przypina wartość jawnie.
- ✓ README EN+PL: wzór scoringu w linii 312 był nieaktualny.

### 2. Cull `bloom` + rename `escher_hex` (commit `68c8b33`, 568 testów)

- ✓ **`bloom` USUNIĘTY**, rejestr 50 → **49**. Przechodził bramkę odrębności na
  GEOMETRII (kąt Lucasa), a mimo to był duplikatem pod zdjęciami (dE 11,47 vs
  11,44). **Kryterium przyjęte na stałe: kształt zasługuje na slot, jeśli różni
  się w MOZAICE, nie na diagramie.**
- ✓ **`escher_lizard` → `escher_hex`** (wybór usera) — sama nazwa, geometria
  nietknięta.
- ✓ **Audyt kolateralny: 88/88 goldenów BIT-W-BIT** ⇒ regeneracja zbędna.
- ✓ **`src/tools/regen_goldens.py` utrwalony** — czyta bibliotekę, target
  i słownik ustawień wprost z testu, więc nie może się z nim rozjechać.
- ✓ Liczniki zweryfikowane **skryptem przeciw `SHAPE_MODES`**, nie okiem:
  README EN/PL (tabela 5 rodzin sumuje się do 49), `docs/index.html` (title,
  meta, OG, twitter, JSON-LD, lista alfabetyczna), `PLAN_SHAPES`,
  `PLAN_SHAPES_EXTRA`, `MODEL_ROUTING`.
- ✓ Zero sierot w narzędziach propozycji (wg precedensu `kepler_ty`).

### 3. Push zaległości

- ✓ **3 commity z 15.08 wypchnięte** (`7ac8d9c..fb9fe87`) — strona `docs/` jest
  live, ścieżka do weryfikacji GSC odblokowana.

## Co zostało (backlog sesji)

- ⟳ **Tag GSC** — czeka na usera; po otrzymaniu: wstawić do `docs/index.html`,
  commit, push, dać znać kiedy klikać „Zweryfikuj".
- ⟳ **Backlinki (punkt 4 SEO)** — teksty gotowe w `PLAN_SEO.md`, publikacja pod
  nazwiskiem usera, świadomie nietknięte.
- ⟳ **Wybór domyślnej `freq_tolerance_de`** — po obejrzeniu renderu; jedna stała.
- ⟳ **`assets/examples/*.jpg` nieaktualne** (28.04–12.06) — starsze nie tylko od
  zmiany silnika, ale od upgrade'u hi-res (9.07, ostrość +48,7%), naprawy
  czarnego paddingu krawędzi (21.07) i poprawek groutu. User zrobi je sam.
- ⟳ **Galeria live `docs/tiles/` (DZI)** — również sprzed zmiany silnika.
- ⟳ Rekomendacje ②③④⑥ z 2026-07-26 (kształt niewidoczny w całości → crop 1:1
  w galerii; kalibracja `scale`; A/B `sierpinski`; grout=off dla kształtów
  o dużym udziale tuszu). Mierzyć `Σa²/Σa`, NIE medianą pola.
- ⟳ `medium=3px` / `thick=5px` niezweryfikowane na realnym renderze.
- ⟳ Hero panorama — lokalna, nieopublikowana (Wariant C).
- ⟳ (przeniesione) PLAN_FRACTAL F1a.
- ✗ **SKREŚLONE decyzją usera:** batch 50 kształtów + driver
  `render_shapes_batch.py`. `output/shapes/` nie jest nigdzie podpięte.

## Aktywne pliki

- `src/engine_smart.py` — `DEFAULT_FREQ_TOLERANCE_DE` (l. 63), pasmo i scoring
  w `_do_render` (~l. 4210-4290); usunięte `_gen_bloom`/`_LUCAS_ANGLE`.
- `tests/test_freq_tolerance.py` — NOWY (7 testów).
- `src/tools/regen_goldens.py` — NOWY (utrwalona sonda regeneracji).
- `tests/test_golden_shapes.py` — 88 hashy, fixture przypina `freq_tolerance_de`.
- `tests/test_grout_engine.py` — bloom usunięty z `_VORONOI_FAMILY` i bramek.
- `README.md`, `README.pl.md`, `docs/index.html` — 49 kształtów, opis pasma.
- `assets/shape_schemes/escher_hex.png` (był `escher_lizard.png`).
- EFEMERYCZNE (scratchpad): `freqtol_probe.py --res 8K` (sweep ΔE, ta sama
  metryka co `freqpen_probe.py` z 15.08 — **do skopiowania przy kroku 3**),
  `sweep/` z renderami 8K baseline (fp30/fp10/fp00) i tol de005…de080.

## Otwarte pytania

- **Jaka wartość `freq_tolerance_de` po dosypaniu zdjęć?** Tabela wyżej jest dla
  obecnej biblioteki; nowa przesunie krzywą.
- **`forbidden_indices` (+1e6) — drugi, nieograniczony mechanizm.** Pasmo go nie
  dotyczy; daje resztkowe 0,72% ciemnych przy karze całkiem wyłączonej. Czy
  ograniczać go analogicznie? Nie badane.
- **Ścieżka maskowana liczy KWADRATY odległości**, a GEMM prawdziwe euklidesowe —
  próg to uwzględnia, ale sam `freq_penalty` jest w tej ścieżce dodawany do
  wielkości w innych jednostkach (wada sprzed tej sesji, nietknięta).
- **Prawdziwa sylwetka jaszczurki dla `escher_hex`** — możliwa, przestała być
  długiem po rename.

## Do MEMORY.md (przeniesiono)

- **`MEMORY.md` → Rozwiązane problemy, wpis [2026-08-20]** „Szum w niebie
  NAPRAWIONY — pasmo wierności koloru": pasmo absolutne vs względne, wyprowadzenie
  ΔE·0,05, nasycenie miękkie, kwadraty w ścieżce maskowanej, tabela @8K, granica
  biblioteki, `forbidden_indices` jako drugie źródło.
- **`MEMORY.md` → Rozwiązane problemy, wpis [2026-08-20]** „Cull `bloom` + rename
  `escher_hex`": kryterium „różni się w MOZAICE, nie na diagramie", goldeny jako
  instrument audytu kolateralnego, PNG schematu idzie z nazwą, zero sierot,
  lista liczników do aktualizacji.
- **Domknięte w miejscu:** rekomendacje ①, ⑤, ⑦ z 2026-07-26 oznaczone ✓;
  lista odrzuconych kształtów 9 → 10.
- **Pamięć długoterminowa:** `project_freq_penalty_sky_noise.md` (rozszerzony
  o wdrożenie i kalibrację), `project_shape_registry_50.md` (rejestr 49,
  kryterium mozaiki, goldeny jako instrument).
