# CLAUDE.md — Neural-Mosaic

## Kontekst projektu
- **Projekt:** Neural-Mosaic — aplikacja desktopowa generująca fotomozaiki do rozdzielczości 16K z tysięcy obrazów lub glifów typograficznych
- **Typ:** Desktop App + AI/ML
- **Stack:** Python 3.10 (conda), torch 2.5.1, customtkinter 5.2.2, transformers 4.57.3, opencv-python 4.12, pillow 11.1.0, scikit-learn 1.7.2, scipy 1.15.3, numpy 2.0.1
- **Środowisko:** Windows 11, Miniconda (Python 3.10), VS Code
- **Cel bieżący:** Implementacja CLIP-based semantic tile matching w SmartEngine (branch `feature/semantic-clip`) — zamiana 3×3 LAB color features na CLIP embeddings dla semantycznego dopasowania kafelków; typo engine enhancements (font groups, color modes) zostały ukończone w poprzednich commitach

## Zasady pracy
- Zawsze sprawdzaj MEMORY.md przed podjęciem decyzji architektonicznej
- Nie duplikuj rozwiązań już opisanych w MEMORY.md
- Przy każdej nowej sesji: zacznij od /start
- Przy zakończeniu sesji: zawsze wywołaj /end
- W trakcie dłuższej pracy rób checkpointy przez /save
- Język komunikacji: polski (chyba że user napisze po angielsku)

## Konwencje projektu
- **Zawsze pisz pełne pliki** — nigdy nie używaj `# rest unchanged` ani częściowych edycji
- `pathlib.Path` wszędzie — bez raw string paths
- `logging.getLogger(__name__)` we wszystkich modułach; `logging.basicConfig` tylko w entry points
- `os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"` musi być ustawione przed importami torch w entry points
- Nazewnictwo plików: snake_case
- Styl commitów: conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`)
- Brak dedykowanego lintera — stosuj styl PEP 8

## Architektura

**Entry point:** `src/gui.py` — customtkinter GUI z dwoma zakładkami:
- **Smart Photo Mosaic** — używa `SmartEngine`, wymaga `data/smart_index.pkl`
- **Symbol Mosaic (Typo)** — używa `TypoEngine`, wymaga `data/typo_index.pkl`

**Silniki:**
- `src/engine_smart.py` — color photo mosaic; dopasowanie przez siatkę 3x3 LAB + `cKDTree`; ładuje `data/smart_index.pkl`
- `src/engine_typo.py` — font/symbol mosaic; renderuje glify jako kafelki; ładuje `data/typo_index.pkl`
- `src/ai_core.py` — Singleton dla MiDaS DPT_Hybrid (depth estimation), lazy-loaded

**Indeksery** (uruchom przed pierwszym użyciem lub przez przyciski GUI):
```bash
python -m src.indexer_smart   # produkuje data/smart_index.pkl  (3x3 LAB features)
python -m src.indexer_typo    # produkuje data/typo_index.pkl   (font glyph analysis)
```

**Przepływ danych:**
- `Config` (`src/config.py`) — `@dataclass`, instancja `settings`, czyta z `.env`. Kluczowe pola: `TILE_SIZE=75`, `TARGET_SHORT_SIDE=18000`, `USE_CUDA=True`
- Biblioteka kafelków: `data/library_public/tiles/` lub `data/library_private/tiles/`
- Fonty: `assets/fonts/`

## Komendy

```bash
# Uruchom GUI (customtkinter) — jedyny entry point
python -m src.gui

# Zbuduj dataset kafelków (async downloader)
python -m src.fast_downloader

# Uruchom testy
pytest tests/

# Pojedynczy test
pytest tests/test_processor.py::test_cuda_availability
```

## Pliki stanu sesji
- **MEMORY.md**       — długoterminowa pamięć projektu (czytaj na /start)
- **last_session.md** — stan ostatniej sesji (czytaj na /start, pisz na /end)

## Komendy dostępne w tym projekcie
| Komenda    | Kiedy używać                      | Co robi                                    |
|------------|-----------------------------------|--------------------------------------------|
| `/start`   | Na początku każdej sesji          | Czyta MEMORY.md + last_session.md          |
| `/save`    | Checkpoint w trakcie pracy        | Aktualizuje last_session.md (sesja trwa)   |
| `/end`     | Na końcu sesji                    | Nadpisuje last_session.md + update MEMORY  |
| `/status`  | Szybki podgląd (bez modyfikacji)  | Wyświetla aktualny stan z last_session.md  |

## Sprzęt / Ograniczenia
- **GPU:** RTX 3050 Laptop 4GB VRAM — nie ładuj modeli >3.5GB w FP16
- **CPU:** i5-12500H
- **RAM:** 32GB DDR4
- **Preferencje AI:** kwantyzacja GGUF Q4_K_M dla LLM, CPU offload dla zbyt dużych warstw

## Struktura katalogów (wykryta)
```
Neural-Mosaic/
├── assets/          # przykłady, fonty
├── data/            # biblioteki kafelków, indeksy .pkl
├── input/           # obrazy wejściowe
├── logs/            # pliki logów
├── output/          # wygenerowane mozaiki
├── src/             # cały kod źródłowy
│   ├── gui.py
│   ├── engine_smart.py
│   ├── engine_typo.py
│   ├── ai_core.py
│   ├── config.py
│   ├── indexer_smart.py
│   ├── indexer_typo.py
│   └── fast_downloader.py
└── tests/           # pytest
```
