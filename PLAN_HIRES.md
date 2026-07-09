# PLAN_HIRES.md — Punkt 4 planu jakości: biblioteka hi-res (nakładka + re-fetch per-źródło)

**Status:** ZATWIERDZONY do realizacji (2026-07-09, analiza Opus + rewizja Fable)
**Wykonawca:** Opus (HIGH) — plan jest samowystarczalny, nie powtarzaj eksploracji z sekcji „Fakty zweryfikowane".

---

## Fakty zweryfikowane (2026-07-09 — NIE sprawdzaj ponownie)

1. **Winowajcą miękkich kafli jest `src/optimizer.py`**, nie downloader:
   `TARGET_SHORT_SIDE = 250` (linia 24) + `img.save(file_path, quality=90)` in-place (linia 57).
   Przeskalował CAŁĄ bibliotekę do 250 px krótszego boku, nadpisując oryginały hi-res.
   Archiwa źródłowe i katalogi temp są SKASOWANE — oryginały nie istnieją lokalnie.
2. **Skład `data/library_public/tiles/` (421 296 plików):**
   | prefiks | liczba | % | odzysk hi-res |
   |---|---:|---:|---|
   | `coco_train_*` | 118 240 | 28% | per-plik HTTP: `http://images.cocodataset.org/train2017/{id}.jpg` |
   | `coco_*` (unlabeled) | 123 385 | 29% | per-plik HTTP: `http://images.cocodataset.org/unlabeled2017/{id}.jpg` |
   | `food_*` | 100 941 | 24% | TYLKO archiwum 5 GB (Food-101, natywne 512 px) — etap B |
   | `places_Places365_val_*` | 36 497 | 9% | TYLKO archiwum 2.3 GB — etap B |
   | `dog_n*` / `flower_image_*` | ~30 000 | 7% | TYLKO archiwa Stanford/Oxford — etap B |
   | `tile_*` (picsum) | 11 190 | 2.6% | per-plik: `https://picsum.photos/seed/{idx}/512` (seed = int z nazwy `tile_{idx:06d}.jpg`) |
   | keyword loremflickr (`abstract_*` itp.) | 418 | 0.1% | BRAK — zostawić; ESRGAN ODROCZONY |
   Przykłady nazw: `coco_train_000000000009.jpg`, `coco_000000000008.jpg`, `tile_000000.jpg` (na dysku 200×200).
3. **`used_counts` to zmienna LOKALNA** w `_do_render` (`src/engine_smart.py:1152`, użycia: 1233, 1240, 1247) — umiera po renderze. Nie ma żadnego eksportu listy użytych kafli. Trzeba go dobudować (Sprint 2).
4. **`curate_starter.py` kopiuje przez `shutil.copy2`** — kuracja NIE zmniejszała; to potwierdza pkt 1.
5. `data/tiles/` jest puste; realne biblioteki wg `src/library_dirs.py` (`LIBRARY_DIRS`).
6. `optimizer.py` iteruje po `LIBRARY_DIRS` i **usuwa plik przy dowolnym wyjątku otwarcia** (linie 59–64).

## Inwarianty globalne (obowiązują w KAŻDYM sprincie)

- **GEMM/dopasowanie NIETKNIĘTE** (inwariant A1: `_euclid_f32` prawdziwy euklides; zmiany tylko w warstwie otwierania plików / I/O).
- **Golden bit-w-bit przy pustej nakładce**: gdy `data/tiles_hires/` nie istnieje lub jest pusty, render musi być bitowo identyczny jak przed zmianą (istniejące goldeny `tests/test_golden_shapes.py` NIE mogą się zmienić).
- `data/tiles_hires/` **NIGDY nie trafia do `LIBRARY_DIRS`** (indexer by go zdublował, optimizer by go zmiażdżył do 250 px). Dodać komentarz-inwariant w `library_dirs.py` + test.
- `render_preview` pozostaje **bez I/O** (nie zapisuje used_tiles.json).
- Konwencje repo: `pathlib.Path`, `logging.getLogger(__name__)`, pełne pliki, PEP 8, ASCII-only w `print()` narzędzi (terminal CP1250).
- Testy: `C:/Users/plazo/miniconda3/envs/mosaic/python.exe -m pytest tests/` (env `mosaic`, NIE `conda run`). Stan wyjściowy: 231 zielonych.
- Pobrane pliki zapisywać **as-is (bajty, bez rekompresji)**, wzorcem atomowym `.part` → `os.replace` (wzorzec w `downloader.py:76-79`).

---

## Sprint 1 — `_resolve_tile_path` (fundament nakładki)

**Cel:** każdy plik ręcznie/skryptowo wrzucony do `data/tiles_hires/` jest automatycznie używany w renderze zamiast wersji z biblioteki.

1. W `src/engine_smart.py`: stała/pole `HIRES_DIR = BASE_DIR / "data" / "tiles_hires"` (konfigurowalne na poziomie modułu lub settings — musi dać się podmienić w testach przez monkeypatch).
2. Funkcja `_resolve_tile_path(path: Path) -> Path`: jeśli `HIRES_DIR / path.name` istnieje → zwróć ją, inaczej oryginał. Cache'owanie: przy 100k+ otwarć w pętli renderu NIE rób `exists()` per kafel — jednorazowy `set(nazw)` z `HIRES_DIR` na starcie `_do_render` (odporny na brak katalogu).
3. Podmień KAŻDE miejsce otwierania kafla z biblioteki: `Image.open(self.paths[best_idx])` (~1240) i wszystkie analogiczne (sprawdź też ścieżkę preview / neighbors_map — grep `Image.open(self.paths`).
4. **Testy** (nowy `tests/test_hires_overlay.py`): (a) pusta/nieistniejąca nakładka → oryginalna ścieżka; (b) plik w nakładce → ścieżka hires; (c) render z tmp-nakładką (monkeypatch HIRES_DIR) faktycznie otwiera wersję hires (np. inny kolor kafla widoczny w wyniku); (d) test inwariantu: `tiles_hires` ∉ `LIBRARY_DIRS`.
5. Golden: uruchom `tests/test_golden_shapes.py` — musi przejść BEZ regeneracji.

**Commit:** `feat(engine): nakladka tiles_hires przez _resolve_tile_path + testy`

## Sprint 2 — eksport `used_tiles.json`

**Cel:** po pełnym renderze powstaje JSON z listą użytych kafli — wejście dla Sprintu 3.

1. `_do_render`: zbierz `used_counts` do zwrotki/atrybutu (np. `self.last_used_counts`) — decyzja implementacyjna wolna, ale **`render_preview` nie zapisuje niczego na dysk**.
2. Zapis w `create_mosaic` (warstwa I/O): `output/{stem}_used_tiles.json` — format: `{"generated": iso-date, "tiles": [{"path": str, "name": str, "count": int}, ...]}` tylko dla `count > 0`, posortowane malejąco po count.
3. Nazewnictwo zgodne z konwencją batch (`{stem}_...`, bez timestampa → idempotentne nadpisanie).
4. **Testy**: JSON powstaje po create_mosaic, suma countów == liczba komórek siatki (lub ≥ przy klinach krawędziowych — sprawdź empirycznie), preview NIE tworzy pliku.

**Commit:** `feat(engine): zrzut used_tiles.json po pelnym renderze`

## Sprint 3 — `src/tools/upgrade_tiles.py` etap A (COCO + picsum per-plik)

**Cel:** selektywny re-fetch hi-res do `data/tiles_hires/` dla kafli z `used_tiles.json`.

1. **Router jako czysta funkcja** `classify_tile(name: str) -> tuple[source, url | None]`:
   - `coco_train_{id}.jpg` → `("coco", "http://images.cocodataset.org/train2017/{id}.jpg")`
   - `coco_{id}.jpg` (id numeryczne!) → `("coco", ".../unlabeled2017/{id}.jpg")` — UWAGA: dopasowanie `coco_train_` PRZED `coco_`; `coco_` tylko gdy reszta to cyfry.
   - `tile_{idx}.jpg` → `("picsum", "https://picsum.photos/seed/{int(idx)}/{size}")` (size domyślnie 512)
   - `food_/places_/dog_/flower_` → `("archive", None)` — etap B, tylko raportuj liczność
   - inne → `("skip", None)` (loremflickr itd.)
2. CLI (argparse): `--used-json <plik>` (repeatable), `--dest data/tiles_hires`, `--limit N`, `--concurrency 16`, `--dry-run` (tylko raport: ile per źródło), `--size 512`.
3. Async fetch (aiohttp, wzorce z `downloader.py`): semafor, timeout 20 s, 1 retry, skip-if-exists (idempotentny), `.part` → `os.replace`, odpowiedź < 1000 B = odrzuć.
4. **Bezpiecznik tożsamości:** po pobraniu policz 5×5 LAB (funkcja jak `curate_starter.extract_lab_feature`) dla hires i dla pliku bibliotecznego o tej samej nazwie; jeśli średnie deltaE > próg (start: 8.0, kalibruj na 20 próbkach) → usuń pobrany plik, zaloguj `REJECTED`. Chroni przed złym id i kolizją nazw między katalogami bibliotek.
5. Raport końcowy ASCII: fetched/skipped/rejected/failed per źródło + liczność `archive` (dane do decyzji o etapie B).
6. **Testy** (`tests/test_upgrade_tiles.py`, bez sieci): router — wszystkie prefiksy + edge case'y (`coco_train_` vs `coco_`, `coco_abc.jpg` → skip); weryfikator LAB na parach syntetycznych (ten sam obraz w 2 rozdzielczościach → akceptacja; różne obrazy → odrzucenie); skip-if-exists.
7. **Weryfikacja empiryczna** (wzorzec sesji 2026-07-08): mały render → used_tiles.json → upgrade z `--limit 50` → ponowny render → porównanie wizualne crop 1:1 + różnica ostrości; pomiar deltaE bez zmian (dopasowanie nietknięte).

**Commit:** `feat(tools): upgrade_tiles.py — selektywny re-fetch hi-res (COCO+picsum) do tiles_hires`

## Sprint 4 — config-fixy zapobiegawcze

**Cel:** nowi użytkownicy dostają hi-res od początku; optimizer przestaje być miną.

1. `src/optimizer.py`: `TARGET_SHORT_SIDE = int(os.getenv("OPTIMIZER_SHORT_SIDE", 512))`; usuwanie uszkodzonych plików TYLKO za flagą `--delete-corrupt` (domyślnie: log + pomiń); jawny guard `assert` że żaden target-dir nie jest `tiles_hires`; ostrzeżenie w docstringu że operacja jest in-place i destrukcyjna.
2. `src/config.py`: nowe pole `DOWNLOAD_SIZE: int = int(os.getenv("DOWNLOAD_SIZE", 512))`.
3. `src/downloader.py`: oba URL-e używają `settings.DOWNLOAD_SIZE` zamiast `settings.TILE_SIZE` (linie 60, 64).
4. `src/library_dirs.py`: komentarz-inwariant o `tiles_hires` (test już ze Sprintu 1).
5. `.env.example` / README: dopisać `DOWNLOAD_SIZE`, `OPTIMIZER_SHORT_SIDE`, opis nakładki `tiles_hires/` i `upgrade_tiles.py`.
6. **Testy**: config czyta env; router-testy z Sprintu 3 zielone; całość `pytest tests/`.

**Commit:** `feat(config): DOWNLOAD_SIZE + optimizer 512 z guardami (koniec destrukcyjnych domyslnych)`

## Sprint 5 — ODROCZONY (decyzja po realnym used_tiles.json)

- **Etap B archiwa** (food/places/dogs/flowers, ~40% biblioteki): pobranie archiwum → ekstrakcja TYLKO plików z listy used → `tiles_hires/`. Uruchamiać dopiero, gdy raport `--dry-run` pokaże istotny udział tych prefiksów w realnych renderach usera.
- **ESRGAN dla loremflickr (418 szt., 0.1%)**: ODROCZONY bezterminowo — koszt zależności nieproporcjonalny; fallback `_resolve_tile_path` załatwia sprawę (kafle zostają 250 px).
- **Ewentualnie**: podbicie `top_k` dla `wmask != None` (otwarte pytanie z 2026-07-08 — recall przy mocno maskowanych kształtach).

---

## Kryteria ukończenia całości

1. 231 + nowe testy zielone; goldeny bez regeneracji (pusta nakładka = bit-w-bit).
2. Render z wypełnioną nakładką: widoczna poprawa ostrości przy `tile_scale > 2.5` (porównanie wizualne crop 1:1, wzorzec z sesji 2026-07-08).
3. `upgrade_tiles.py --dry-run` działa na realnym `used_tiles.json` i raportuje rozkład źródeł.
4. Świeża instalacja (koncepcyjnie): downloader 512 px + optimizer 512 px → nowi użytkownicy nie potrzebują nakładki.
5. Po każdym sprincie: commit (conventional), po całości: aktualizacja MEMORY.md repo + auto-memory `project_tile_quality_plan`.
