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
