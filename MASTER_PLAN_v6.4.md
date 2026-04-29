# MASTER_PLAN.md
# Neural-Mosaic — Skonsolidowany Plan Wdrożeń (v6.4)

> Jeden dokument. Optymalna kolejność. Każdy krok oznaczony:
> 🤖 Claude Code | 👤 Ręcznie.
> Zależności między fazami — nie przeskakuj.
>
> **Zmiany v6.4 vs v6.3 (punktowe):**
> - Krok 2.5b (NOWY) — bundle 120 fontów OFL/Apache w repo +
>   struktura licencji w `assets/fonts/licenses/`. Zero-friction
>   UX: `git clone` → `python -m src.gui` → Symbol Mosaic działa.
> - Krok 2.5 — `.gitignore` NIE wykluczy `assets/fonts/` (jawnie).
> - Faza 7.0 — sekcja "Font Library" w README + Known Limitations
>   update (repo size ~100 MB z powodu fontów).
> - gui.py guard rail — friendly error gdy fonts directory empty.
>
> **Zmiany v6.3 vs v6.2 (punktowe):**
> - Krok 1.8 — **PRZEPROJEKTOWANY**: Tile Tint używa pixel lerp zamiast
>   mean-shift. Stara logika `shift = (sector_mean - tile_mean) * t` była
>   bliska zeru dla zmatchowanych kafelków (matcher już dobrał dobry
>   kolor → tile_mean ≈ sector_mean → shift ≈ 0). Nowa logika:
>   `tile_arr = tile_arr * (1-t) + sector_mean * t` — widoczna różnica
>   niezależnie od jakości matcher'a.
> - Krok 1.12 — dodany test diagnostyczny: `"Tile Tint active: X%"`
>   MUSI się pojawić w konsoli przy tint > 0.
>
> **Zmiany v6.2 vs v6.1 (punktowe):**
> - Krok 1.5.0 (NOWY, przed 1.5.1) — diagnoza i przywrócenie brakującego
>   przycisku `RENDER SYMBOL MOSAIC`, który został usunięty podczas
>   implementacji Symbol Mosaic Enhancement (regresja z Kroku 4).
>   Musi być wykonany PRZED refaktorem layoutu (Krok 1.5.1).
>
> **Zmiany v6.1 vs v6 (punktowe):**
> - Krok 0.1 — `.gitignore` uwzględnia `last_session.md` (session system)
> - Krok 6.3 — merge CLAUDE.md chroni sekcję "Pliki stanu sesji"
>   przed wymazaniem przez GitNexus
>
> **Zmiany v6 vs v5:**
> - Nowa Faza 1.5 — **GUI layout fix** dla zakładki Symbol Mosaic
>   (przycisk RENDER wypadł poza viewport po dodaniu kontrolek z sesji
>   Symbol Mosaic Enhancement — patrz CLAUDE_CODE_PROMPT_symbol_mosaic_v2)
> - Rozszerzona Faza 3 — **4 showcase symbol mosaics** zamiast jednej,
>   demonstrujące różne tryby i grupy fontów
> - Rozszerzona Faza 4 — **drugi zoom GIF** (z symbol mosaic) + nowa
>   sekcja README "Symbol Mosaic Gallery" (2×2 grid trybów)
>
> **Zmiany v5 vs v4:**
> - Faza 6 (GitNexus) → wersja minimalna (opcja B): tylko 6.1–6.4 + 6.6–6.7
> - Commity git dodane po KAŻDEJ fazie
> - Email do rejestracji Openverse wpisany wprost: `p.lazowski.1986@gmail.com`
> - Code review: 8 dodatkowych ulepszeń z perspektywy PM/senior dev

---

## Nazewnictwo (obowiązuje WSZĘDZIE)

- Nazwa projektu: **Neural-Mosaic** (z myślnikiem)
- Nazwa repo: **neural-mosaic** (lowercase)
- URL repo: `github.com/Piotr1686/neural-mosaic`
- GitHub Pages: `piotr1686.github.io/neural-mosaic`

Claude Code przy każdym zadaniu weryfikuje brak starych wariantów
("NeuroMosaic", "neuromosaic", "neural_mosaic").

---

## Źródła zdjęć — finalna lista

| Źródło | API Key | Licencja | Rola |
|---|---|---|---|
| **Openverse** (800M+) | Darmowy (POST register) | CC0 filtr | **Główne źródło** |
| Metropolitan Museum of Art | Nie wymaga | CC0 | Malarstwo, portrety |
| Art Institute of Chicago | Nie wymaga | CC0 | Impresjonizm |
| NASA Image Library | Nie wymaga | US Gov PD | Kosmos, Ziemia |
| Cleveland Museum of Art | Nie wymaga | CC0 | Sztuka europejska/azjatycka |
| Wikimedia Commons | Nie wymaga | CC0/PD only | Encyklopedyczne |
| ~~Flickr~~ | ~~PRO only ($)~~ | — | ~~USUNIĘTY~~ |
| ~~Library of Congress~~ | — | — | ~~USUNIĘTY (brak fetchera)~~ |

**Tylko CC0/Public Domain.** Nigdy CC-BY/CC-BY-SA — ShareAlike jest
niekompatybilne z licencją MIT projektu.

---

## Szacunki czasowe (realistyczne)

| Faza | 🤖 Claude Code | 👤 Ręcznie | Czyste wykonanie | Z debuggingiem |
|---|---|---|---|---|
| 0. Git Init | 0 | 1 | 10 min | 10 min |
| 1. Quality Enhancements | 11 | 1 | 2-3h | 4-6h |
| 1.5. Symbol Mosaic GUI Fix | 2 | 1 | 30 min | 45-60 min |
| 2. Tile Library System | 6 | 3 | 3-4h | 8-12h + pobieranie |
| 3. Showcase Mosaics (rozszerzona) | 1 | 5 | 3-4h | 4-5h |
| 4. README Visual Assets (rozszerzona) | 3 | 2 | 2-3h | 3-4h |
| 5. Deep Zoom Viewer | 3 | 3 | 3-4h | 5-7h |
| 6. GitNexus (MIN — opcja B) | 3 | 2 | ~45 min | 1-1.5h |
| 7. Finalizacja (rozszerzona) | 1 | 4 | 2-3h | 3-4h |
| **Razem** | **29** | **22** | **~17-22h** | **~32-44h** |

---

## Mapa zależności

```
FAZA 0: Git Init (NOWA — wymagana przez Fazę 6)
    │
FAZA 1: Quality Enhancements (silnik)
    │
    ├─→ wymaga przebudowy indeksu (ręcznie)
    │
FAZA 1.5: Symbol Mosaic GUI Fix (NOWA w v6)
    │   └─→ niezależna od Fazy 1, można wykonać równolegle
    │
FAZA 2: Tile Library System (downloader + GUI)
    │
    ├─→ wymaga backupu istniejącej biblioteki (ręcznie)
    ├─→ wymaga klucza Openverse API (ręcznie, 1 min)
    │
FAZA 3: Showcase Mosaics (generowanie przykładów)
    │   ├─→ wymaga SANITY CHECK (nowy krok)
    │   ├─→ wymaga gotowego silnika (Faza 1) + biblioteki (Faza 2)
    │   └─→ 4 photo mosaics + 4 symbol mosaics (v6 — rozszerzone)
    │
    ├──→ FAZA 4: README Visual Assets (GIF×2 + tabela + Symbol Gallery)
    │
    └──→ FAZA 5: Deep Zoom Viewer (GitHub Pages) — max 2 mozaiki
    
FAZA 6: GitNexus Integration (MIN — opcja B, wymaga git history)
    │   └─→ scope: graf architektury + screenshot, BEZ pre-publish audit
    │
FAZA 7: Finalizacja + push
```

---

# ═══════════════════════════════════════
# FAZA 0: GIT INIT (NOWA)
# Czas: 10 minut
# Powód: GitNexus (Faza 6) wymaga repozytorium Git
# ═══════════════════════════════════════

### Krok 0.1 — Inicjalizacja repozytorium
👤 **Ręcznie**

```
Co zrobić:

cd D:\Programming_Projects\Neural-Mosaic

# 1. Minimalny .gitignore PRZED pierwszym commitem
#    (pełny zostanie dopisany w Kroku 2.5 — tu tylko żeby baseline nie zawierał śmieci)
echo __pycache__/ > .gitignore
echo *.pyc >> .gitignore
echo .venv/ >> .gitignore
echo venv/ >> .gitignore
echo .env >> .gitignore
echo data/library_starter/tiles/ >> .gitignore
echo data/library_public/tiles/ >> .gitignore
echo data/library_extended/tiles/ >> .gitignore
echo data/library_private/tiles/ >> .gitignore
echo data/library_public_BACKUP/ >> .gitignore
echo data/test_download/ >> .gitignore
echo data/smart_index.pkl >> .gitignore
echo data/download_state.json >> .gitignore
echo output/*.jpg >> .gitignore
echo output/*.png >> .gitignore
# Session system (jeśli używasz /start /save /end z Claude Code):
# last_session.md zmienia się co sesję — szumi historia gita.
# MEMORY.md CELOWO commitujemy (dokumentuje architekturę, wartość portfolio).
echo last_session.md >> .gitignore

# 2. Init + baseline
git init
git add .
git status            # KONTROLNIE: sprawdź co idzie do commita (brak kafelków? brak .env?)
git commit -m "Faza 0 complete — pre-refactor baseline (v5.x before quality enhancements)"

To daje GitNexus historię do analizy w Fazie 6.

KONWENCJA COMMITÓW (obowiązuje w całym planie):
- Po każdej zakończonej fazie:  git add . && git commit -m "Faza N complete — <opis>"
- Przed każdym commitem sprawdź:  git status  (co dokładnie idzie)
- Jeśli jesteś w trakcie dłuższej fazy i chcesz zachować postęp:
    git add . && git commit -m "Faza N WIP — <konkretny krok>"
- Pełny .gitignore zostanie dopisany w Kroku 2.5 przez Claude Code.
- Wszystkie commity lokalne; push dopiero w Fazie 7.2.

UWAGA — Windows PowerShell 5.1 (domyślny w Win11):
Operator `&&` NIE DZIAŁA w PowerShell 5.1 (dodany w PowerShell 7+).
Jeśli widzisz błąd: "The token '&&' is not a valid statement separator",
rozbij komendę na dwie linie:
    git add .
    git commit -m "Faza N complete - <opis>"
Alternatywnie zainstaluj PowerShell 7: winget install Microsoft.PowerShell
Em dash (—) w komunikatach też może sprawiać problemy z kodowaniem —
bezpieczniej użyć zwykłego myślnika (-) w komunikatach commitów.
```

---

# ═══════════════════════════════════════
# FAZA 1: QUALITY ENHANCEMENTS
# Czas: ~2-3h (czyste) / ~4-6h (z debuggingiem)
# ═══════════════════════════════════════

## Cel: Siatka cech 5×5 + Color Blend + Tile Tint

---

### Krok 1.1 — Siatka 5×5 w indekserze
🤖 **Claude Code**

```
Polecenie:

Otwórz src/indexer_smart.py. Znajdź wszystkie: .resize((3, 3), ...)
Zamień na: .resize((5, 5), ...)

Zmień hardcoded 27 → 75 w komentarzach/reshape/asercjach.

Dodaj na początku metody budowania indeksu:
    for lib_dir in LIBRARY_DIRS:
        lib_dir.mkdir(parents=True, exist_ok=True)

Dodaj wersję schematu do zapisywanego pickle:
    data = {
        "paths": self.paths,
        "features": self.features,
        "schema_version": "5x5",
        "feature_dim": 75,
    }

Normalizacja LAB bez zmian.
Zaktualizuj docstringi: "3×3" → "5×5", "27-dim" → "75-dim".

Po zmianach uruchom w terminalu (Windows):
    findstr /S /N "3, 3" src\*.py
    findstr /S /N "27" src\*.py
i potwierdź, że nie ma pozostałości siatki 3×3.
```

---

### Krok 1.2 — Siatka 5×5 w silniku (próbkowanie sektorów)
🤖 **Claude Code**

```
Polecenie:

W src/engine_smart.py, w create_mosaic(), znajdź WSZYSTKIE:
    mat = s_img.resize((3, 3), Image.Resampling.BOX)
Zamień na:
    mat = s_img.resize((5, 5), Image.Resampling.BOX)

Są 3 lokalizacje: kite tiling, hexagon_romb, standard grid.
```

---

### Krok 1.3 — Siatka 5×5 w mirroringu
🤖 **Claude Code**

```
Polecenie:

W src/engine_smart.py (~linia 422-426), zmień:

BYŁO:
    reshaped = self.features.reshape(-1, 3, 3, 3)
    flipped = reshaped[:, :, ::-1, :]
    features_flip = flipped.reshape(-1, 27)

JEST:
    reshaped = self.features.reshape(-1, 5, 5, 3)
    flipped = reshaped[:, :, ::-1, :]
    features_flip = flipped.reshape(-1, 75)
```

---

### Krok 1.4 — Blokada renderowania przy niezgodnym indeksie
🤖 **Claude Code**

```
Polecenie:

W SmartEngine.__init__(), po:
    self.features = data["features"]

Dodaj TWARDĄ walidację (nie WARNING — blokadę):

    expected_dim = 75
    if self.features.ndim == 2 and self.features.shape[1] != expected_dim:
        actual_dim = self.features.shape[1]
        print(f"ERROR: Index has {actual_dim}-dim features, "
              f"expected {expected_dim}. "
              f"Rendering DISABLED. Rebuild index: "
              f"GUI → 'Update / Create Index'")
        self.paths = []      # Wyłącz silnik
        self.features = []   # Wymuś przebudowę
        return

Opcjonalnie sprawdź schema_version:
    schema = data.get("schema_version", "unknown")
    if schema != "5x5":
        print(f"WARNING: Index schema '{schema}', expected '5x5'.")
```

---

### Krok 1.5 — Color Blend: GUI
🤖 **Claude Code**

```
Polecenie:

W src/gui.py, w _setup_photo_tab(), PRZED przyciskiem RENDER:

# --- POST-PROCESSING ---
ctk.CTkLabel(frame, text="POST-PROCESSING", 
             font=("Arial", 12, "bold")).pack(pady=(20, 5))

ctk.CTkLabel(frame, text="Color Blend").pack(pady=(10, 0))
self.seg_blend = ctk.CTkSegmentedButton(frame, values=["0%", "10%", "20%", "30%"])
self.seg_blend.set("0%")
self.seg_blend.pack(pady=5)
```

---

### Krok 1.6 — Color Blend: silnik
🤖 **Claude Code**

```
Polecenie:

W src/engine_smart.py, dodaj blend_strength=0.0 do sygnatury.

Zastąp końcowy zapis:
    mosaic_rgb = final_mosaic.convert("RGB")
    if blend_strength > 0.0:
        print(f"Applying Color Blend: {int(blend_strength * 100)}%...")
        original_resized = target.resize(mosaic_rgb.size, Image.Resampling.LANCZOS)
        mosaic_rgb = Image.blend(mosaic_rgb, original_resized, blend_strength)
    print(f"Saving to {output_path}...")
    mosaic_rgb.save(output_path, quality=95)
```

---

### Krok 1.7 — Tile Tint: GUI
🤖 **Claude Code**

```
Polecenie:

W _setup_photo_tab(), po Color Blend:

ctk.CTkLabel(frame, text="Tile Tint").pack(pady=(10, 0))
self.seg_tint = ctk.CTkSegmentedButton(frame, values=["0%", "10%", "20%", "30%", "40%"])
self.seg_tint.set("0%")
self.seg_tint.pack(pady=5)
```

---

### Krok 1.8 — Tile Tint: silnik (pixel lerp)
🤖 **Claude Code**

```
Polecenie:

Dodaj tint_strength=0.0 do sygnatury create_mosaic().

W pętli renderowania, MIĘDZY _smart_crop() a putalpha(), wstaw blok
pixel lerp (NIE mean-shift — mean-shift wychodzi ~0 dla zmatchowanego
kafelka bo matcher już dobrał podobny kolor):

    img = self._smart_crop(img, tw, th)

    if tint_strength > 0.0:
        sector_box = (
            max(0, px), max(0, py),
            min(target_w, px + tw), min(target_h, py + th)
        )
        if sector_box[2] > sector_box[0] and sector_box[3] > sector_box[1]:
            sector_crop = target.crop(sector_box)
            sector_mean = np.array(
                sector_crop.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0)),
                dtype=np.float32)[:3]
            tile_rgb = img.convert("RGB")
            tile_arr = np.array(tile_rgb, dtype=np.float32)
            # Pixel-wise lerp toward sector_mean.
            # tint=0.0 → full tile texture, 1.0 → solid sector colour.
            # Lerp (not mean-shift) guarantees visible effect regardless
            # of match quality.
            tile_arr = tile_arr * (1.0 - tint_strength) + sector_mean * tint_strength
            tile_arr = np.clip(tile_arr, 0, 255).astype(np.uint8)
            img = Image.fromarray(tile_arr).convert("RGBA")

    img.putalpha(mask)

DODAJ również diagnostic print PRZED główną pętlą matching/render
(obok istniejącego "Matching and generating final mosaic..."):

    print("Matching and generating final mosaic...")
    if tint_strength > 0.0:
        print(f"  Tile Tint active: {int(tint_strength * 100)}% (pixel lerp toward sector colour)")
    if blend_strength > 0.0:
        print(f"  Color Blend will be applied at save: {int(blend_strength * 100)}%")

UWAGA: numpy jest już importowany na górze engine_smart.py.
Zmienne target, target_w, target_h, px, py SĄ dostępne w tym scope
(wewnątrz create_mosaic()).
```

---

### Krok 1.9 — Połączenie GUI z silnikiem
🤖 **Claude Code**

```
Polecenie:

W gui.py run_photo(), po border_mode:
    blend_val = self.seg_blend.get()
    blend_strength = int(blend_val.replace("%", "")) / 100.0
    tint_val = self.seg_tint.get()
    tint_strength = int(tint_val.replace("%", "")) / 100.0

Przekaż do create_mosaic: blend_strength=blend_strength, tint_strength=tint_strength
```

---

### Krok 1.10 — Aktualizacja README + komentarzy
🤖 **Claude Code**

```
Polecenie:

1. README: "27-dimensional" → "75-dimensional", "3×3 grid" → "5×5 grid"
2. Tabela kontrolek: dodaj Color Blend i Tile Tint
3. Szukaj resztek (Windows):
   findstr /S /N "3, 3" src\*.py
   findstr /S /N "27-dim" src\*.py
   findstr /S /N "27 dim" src\*.py
   Zmień tylko te dotyczące siatki cech.
```

---

### Krok 1.11 — RAM warning w GUI
🤖 **Claude Code**

```
Polecenie:

W gui.py run_photo(), przed uruchomieniem wątku renderowania,
dodaj ostrzeżenie dla rozdzielczości > 8K:

    if res in ("8K", "16K"):
        self.log(f"NOTE: {res} rendering requires ~2-4 GB free RAM. "
                 f"Close other applications for best performance.")
```

---

### Krok 1.12 — Przebudowa indeksu + test
👤 **Ręcznie**

```
Co zrobić:

1. python -m src.gui
2. "Update / Create Index" → poczekaj na "Indexing Complete!"
3. "Load Smart Index" → sprawdź: BRAK komunikatu ERROR o wymiarach
4. Mozaika 2K, Blend 0%, Tint 0% → czy wygląda poprawnie?
5. Mozaika 2K, Blend 20%, Tint 0% → widoczna różnica?
   W konsoli MUSI pojawić się: "Applying Color Blend: 20%..."
6. Mozaika 2K, Blend 0%, Tint 20% → widoczna różnica?
   W konsoli MUSI pojawić się PRZED pętlą rendering:
   "  Tile Tint active: 20% (pixel lerp toward sector colour)"
   
   Jeśli TA LINIA SIĘ NIE POJAWI — Tint jest nieaktywny i trzeba
   sprawdzić Krok 1.8 (silnik) + 1.9 (GUI → silnik).

7. SANITY CHECK WIZUALNY tintu: porównaj mozaikę Tint 0% vs Tint 20%
   W Tint 20% kafelki powinny być SUBTELNIE stonowane w stronę
   dominującego koloru sektora:
   - partie nieba → wszystkie hexagony delikatnie bardziej niebieskie
   - roślinność → bardziej zielono-brązowa
   - twarze → bardziej różowo-beżowe
   Tekstury kafelków nadal widoczne — to nie solid fill.
   
   Jeśli obie mozaiki wyglądają IDENTYCZNIE — fix tintu nie
   zadziałał lub seg_tint nie jest podłączony do GUI.
   
8. git add .
   git commit -m "Faza 1 complete - 5x5 grid, blend, tint"
   (PowerShell 5.1: użyj dwóch osobnych linii zamiast &&)
```

---

# ═══════════════════════════════════════
# FAZA 1.5: SYMBOL MOSAIC GUI FIX (NOWA w v6)
# Czas: ~30 minut (v6.2: +10 min na naprawę regresji w Kroku 1.5.0)
# Powód: Po Symbol Mosaic Enhancement (patrz CLAUDE_CODE_PROMPT_symbol_mosaic_v2)
#        przycisk "RENDER SYMBOL MOSAIC" ZNIKNĄŁ z gui.py (regresja)
#        + pozostałe kontrolki nie mieszczą się w 900px wysokości okna.
# ═══════════════════════════════════════

## Cel: Przeorganizować zakładkę Symbol Mosaic (Typo) tak, żeby wszystkie
## kontrolki — w szczególności przycisk RENDER — były widoczne bez scrollowania.

## UWAGA — REGRESJA WYKRYTA 2026-04-18:
## Podczas implementacji Symbol Mosaic Enhancement przycisk RENDER SYMBOL
## MOSAIC został usunięty z `_setup_typo_tab()`. Krok 1.5.0 przywraca go
## PRZED refaktorem layoutu.

---

### Krok 1.5.0 — Przywrócenie brakującego przycisku RENDER (NAPRAWA REGRESJI)
🤖 **Claude Code**

```
Polecenie:

1. DIAGNOZA — zweryfikuj stan kodu:

   findstr /N "btn_run_t" src\gui.py
   findstr /N "RENDER SYMBOL MOSAIC" src\gui.py

   Jeśli OBA polecenia zwracają pustą listę (żadnych trafień) —
   przycisk RENDER faktycznie został usunięty podczas Symbol Mosaic
   Enhancement. Przejdź do punktu 2.

   Jeśli findstr pokazuje `btn_run_t` w kodzie — przycisk istnieje,
   ale nie mieści się w viewport. Pomiń Krok 1.5.0 i przejdź od razu
   do Kroku 1.5.1 (refaktor layoutu).

2. PRZYWRÓCENIE — w src/gui.py, na KOŃCU metody _setup_typo_tab(),
   PRZED ewentualnym `return` i PO ostatniej istniejącej kontrolce
   (prawdopodobnie Variation SegmentedButton), dodaj:

       # RENDER button (restored after Symbol Mosaic Enhancement regression)
       self.btn_run_t = ctk.CTkButton(
           frame,
           text="RENDER SYMBOL MOSAIC",
           fg_color="purple",
           height=50,
           font=ctk.CTkFont(size=14, weight="bold"),
           command=self.run_typo,
       )
       self.btn_run_t.pack(pady=30)

   UWAGA: używamy TYMCZASOWO pack() (nie grid) — identycznie jak
   w oryginalnym gui.py sprzed Symbol Mosaic Enhancement. W Kroku
   1.5.1 przebudujemy całą metodę na CTkScrollableFrame + grid.
   Tymczasowy pack() ZAPEWNIA że przycisk jest klikalny od razu —
   nie musisz czekać na Krok 1.5.1 żeby renderować mozaiki.

3. WERYFIKACJA — uruchom GUI i sprawdź:

       python -m src.gui

   a. Zakładka "Symbol Mosaic (Typo)":
      [ ] Scroll w dół (lub rozszerz okno) → widzisz fioletowy przycisk 
          "RENDER SYMBOL MOSAIC"?
      [ ] Kliknięcie RENDER bez wybranego obrazu → odpowiedni błąd 
          w konsoli?
   
   b. Szybki smoke test renderowania (wymaga Typo Index):
      1. Load Typo Index (Fast) → Status: Ready (XXXX sym)
      2. Wybierz grupę fontów (np. Latin Clean)
      3. Select Input Image → dowolne zdjęcie
      4. Set Output Folder → dowolny katalog
      5. Kliknij RENDER SYMBOL MOSAIC
      6. Czy mozaika się generuje poprawnie?

4. COMMIT NAPRAWCZY (przed Krokiem 1.5.1):

   git add src/gui.py
   git commit -m "fix(gui): restore missing RENDER SYMBOL MOSAIC button (regression fix)"

   Ten commit ma być OSOBNY od commita Fazy 1.5. Po 6 miesiącach 
   git log będzie czytelny: "aha, tu przywróciliśmy przycisk po 
   regresji, potem refaktor layoutu".
```

---

### Krok 1.5.1 — Refaktor layoutu zakładki Typo (2 kolumny + scroll fallback)
🤖 **Claude Code**

```
Polecenie:

UWAGA: zakłada że Krok 1.5.0 został wykonany i przycisk RENDER istnieje
w `_setup_typo_tab()` używając .pack().

W src/gui.py, w metodzie _setup_typo_tab(), obecnie używasz prostego pack() 
z pionowym dodawaniem kontrolek. Po dodaniu 7 checkboxów Font Groups 
+ Palette Size + Variation + przywróconego przycisku RENDER, 
całość wychodzi poza widoczny obszar — przycisk RENDER niewidoczny 
bez scrollowania.

PRZEBUDOWA na layout z RENDER pinned na dole:

1. Zamień na górze metody:
       frame = self.tab_typo
   na:
       # Outer container — allows RENDER button to pin to bottom
       outer = self.tab_typo
       outer.grid_columnconfigure(0, weight=1)
       outer.grid_rowconfigure(0, weight=1)   # scrollable content area
       outer.grid_rowconfigure(1, weight=0)   # fixed RENDER button row

       # Scrollable frame for all controls — guarantees RENDER button 
       # stays visible even on smaller screens
       frame = ctk.CTkScrollableFrame(outer, fg_color="transparent")
       frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 0))

2. W CAŁEJ dalszej części metody zostawiam .pack() — to działa wewnątrz 
   CTkScrollableFrame. Nie zmieniaj kontrolek, tylko kontener.

3. ZMIEŃ przycisk RENDER (przywrócony w Kroku 1.5.0). 
   ZAMIEŃ:
       self.btn_run_t = ctk.CTkButton(
           frame,                              # ← stary parent: frame
           text="RENDER SYMBOL MOSAIC",
           fg_color="purple",
           height=50,
           font=ctk.CTkFont(size=14, weight="bold"),
           command=self.run_typo,
       )
       self.btn_run_t.pack(pady=30)            # ← stary: pack()

   NA:
       # RENDER button pinned outside the scroll area — always visible
       self.btn_run_t = ctk.CTkButton(
           outer,                              # ← nowy parent: outer
           text="RENDER SYMBOL MOSAIC",
           fg_color="purple",
           height=50,
           font=ctk.CTkFont(size=14, weight="bold"),
           command=self.run_typo,
       )
       self.btn_run_t.grid(row=1, column=0,    # ← nowy: grid
                           sticky="ew", padx=20, pady=(10, 15))

Efekt: wszystkie kontrolki w scrollable frame (jeśli nie mieszczą się 
— user scrolluje), a przycisk RENDER ZAWSZE widoczny na dole zakładki.
```

---

### Krok 1.5.2 — Analogiczna poprawka zakładki Photo (spójność + future-proof)
🤖 **Claude Code**

```
Polecenie:

W src/gui.py, w metodzie _setup_photo_tab(), zastosuj IDENTYCZNY wzorzec 
jak w _setup_typo_tab():
- CTkScrollableFrame dla kontrolek
- Przycisk "RENDER SMART MOSAIC" pinned na dole przez grid

Powód: zakładka Photo ma obecnie 4 mniej kontrolek niż Typo, więc 
problem tam jeszcze nie występuje. ALE gdy dodasz w przyszłości np. 
kontrolkę na variation photomosaic lub nowy tile shape — problem się 
pojawi. Lepiej zrobić raz, porządnie.

Struktura identyczna:
- outer = self.tab_photo z grid_columnconfigure/rowconfigure
- frame = CTkScrollableFrame(outer, fg_color="transparent") z grid row=0
- btn_run_p z grid row=1, sticky="ew"

Zachowaj identyczne paddings jak w Typo dla spójności wizualnej.
```

---

### Krok 1.5.3 — Test obu zakładek
👤 **Ręcznie**

```
Co zrobić:

1. python -m src.gui

2. Zakładka "Smart Photo Mosaic":
   [ ] "RENDER SMART MOSAIC" widoczny bez scrollowania
   [ ] Scroll działa (jeśli okno mniejsze niż zawartość)
   [ ] Kliknięcie RENDER działa (lub zwraca odpowiedni error jeśli brak input)

3. Zakładka "Symbol Mosaic (Typo)":
   [ ] "RENDER SYMBOL MOSAIC" widoczny bez scrollowania
   [ ] Wszystkie 7 checkboxów Font Groups widoczne (scroll jeśli trzeba)
   [ ] Palette Size i Variation widoczne
   [ ] Style Mode combo widoczne
   [ ] Render działa po wyborze grup i obrazu

4. Test zmiany rozmiaru okna:
   - Zmniejsz okno do 1000×700 (mniej niż default 1250×900)
   - [ ] Przycisk RENDER nadal widoczny na dole
   - [ ] Scroll w kontrolkach działa
   - Przywróć do 1250×900

5. git add . && git commit -m "Faza 1.5 complete — scrollable tabs, pinned RENDER buttons"

Po Fazie 1.5 git log --oneline powinien pokazywać DWA commity z tej fazy:
- fix(gui): restore missing RENDER SYMBOL MOSAIC button (regression fix)
- Faza 1.5 complete — scrollable tabs, pinned RENDER buttons
```

---

# ═══════════════════════════════════════
# FAZA 2: TILE LIBRARY SYSTEM
# Czas: ~3-4h (kod) + godziny pobierania
# ═══════════════════════════════════════

## Cel: Multi-source downloader + GUI + Openverse + deduplikacja

---

### Krok 2.0 — Backup istniejącej biblioteki
👤 **Ręcznie**

```
⚠️ KRYTYCZNE — PRZED jakimkolwiek testem downloadera!

1. Sprawdź pliki: dir data\library_public\tiles\ /B | find /C ":"
2. Jeśli masz zdjęcia → backup:
   xcopy /E /I data\library_public\tiles data\library_public_BACKUP\tiles
3. Po Fazie 2 i potwierdzeniu → możesz usunąć backup.
```

---

### Krok 2.1 — Core downloader z Openverse + deduplikacją
🤖 **Claude Code**

```
Polecenie:

Stwórz src/downloader_v2.py z klasą PoliteDownloader.

FETCHERY:
- _fetch_openverse_ids (GŁÓWNY)
- _fetch_met_ids, _fetch_artic_ids, _fetch_nasa_ids, 
  _fetch_cleveland_ids, _fetch_wikimedia_ids
- BEZ _fetch_loc_ids (Library of Congress usunięty — brak implementacji)
- BEZ _fetch_flickr_ids (klucz API wymaga płatnego konta)

PLANY POBIERANIA:
  starter: openverse:200 + met:100 + artic:80 + nasa:60 + cleveland:30 + wikimedia:30
  public:  openverse:2000 + met:1000 + artic:700 + nasa:500 + cleveland:400 + wikimedia:400
  extended: openverse:14000 + met:5000 + artic:4000 + nasa:3000 + cleveland:2000 + wikimedia:2000

OPENVERSE FETCHER:
- API: https://api.openverse.org/v1/images/
- OAuth2 client_credentials: POST /v1/auth_tokens/token/
  z client_id + client_secret → access_token
- Env vars: OPENVERSE_CLIENT_ID, OPENVERSE_CLIENT_SECRET
- Bez tokena: 100 req/dzień (wystarczy na test + starter)
- Z tokenem: 10000 req/dzień
- TOKEN REFRESH: jeśli response.status_code == 401:
  → automatycznie pobierz nowy token → ponów request
- Filtruj: license=cc0,pdm
- source= to FILTR (nie sortowanie)
- 30 tagów tematycznych, round-robin
- Respektuj header Retry-After przy 429:
  retry_after = int(resp.headers.get('Retry-After', 60))
  time.sleep(retry_after)

WIKIMEDIA FETCHER:
- User-Agent: "Neural-Mosaic/1.0 (https://github.com/Piotr1686/neural-mosaic; p.lazowski.1986@gmail.com)"
- TYLKO CC0/PD — ODRZUCA CC-BY, CC-BY-SA
- Thumbnails 800px

POLITE DOWNLOADING:
- Delay 2-3 sek z ±30% jitterem
- Micro-pauza 10-20 sek co 50 requestów
- Długa pauza 60-120 sek co 200 requestów
- Rotacja User-Agent (5 przeglądarek)
- Retry z backoff na 429/500/502/503/504

SKALOWANIE I ZAPIS:
- Najkrótszy bok >= 400px, za duże skalowane w dół
- Za małe (< 200px) → odrzucane
- ZAWSZE img.convert("RGB") przed zapisem JPEG
  (zabezpieczenie przed RGBA/PNG z Wikimedia)
- JPEG quality 85

DEDUPLIKACJA (perceptual hash):
- pip install imagehash
- from imagehash import phash
- Przed zapisem: oblicz phash nowego obrazu
- Jeśli hamming distance < 5 od istniejącego → duplikat, pomiń
- Przechowuj listę hashy w pamięci (i w download_state.json)

FILTR JAKOŚCI:
- Odrzuć rozmyte zdjęcia: 
  gray = img.convert("L")
  edges = gray.filter(ImageFilter.FIND_EDGES)
  variance = np.var(np.array(edges))
  if variance < 50: return False  # Zbyt rozmyte
- Odrzuć jednolite zdjęcia:
  colors = np.array(img.resize((1,1))).flatten()
  if max(colors) - min(colors) < 30: return False

SPRAWDZENIE MIEJSCA NA DYSKU:
- Przed rozpoczęciem Extended:
  import shutil
  free_gb = shutil.disk_usage(".").free / (1024**3)
  if free_gb < 5:
      print(f"WARNING: Only {free_gb:.1f} GB free. Extended needs ~2.5 GB.")

RESUME: download_state.json z listą pobranych ID + hashy phash
TEST: metoda test_download() pobiera 10 zdjęć do data/test_download/

Stwórz src/tools/__init__.py jeśli nie istnieje.
```

---

### Krok 2.2 — GUI: przyciski pobierania i import
🤖 **Claude Code**

```
Polecenie:

W src/gui.py, dodaj sekcję TILE LIBRARY w sidebarze:

- Label "TILE LIBRARY"
- Label statusu (lbl_library_status) — zlicza pliki ze WSZYSTKICH 
  katalogów LIBRARY_DIRS (starter + public + extended + private)
- "Download Starter (500 · ~25 MB)"
- "Download Gallery (5000 · ~250 MB)"
- "Download Extended (30K · ~2.5 GB)" ← zaktualizowany szacunek
- "Import Your Photos..."
- Progress bar (ukryty domyślnie)

WALIDACJA KLUCZA przed Gallery/Extended:
  W download_public() i download_extended(), przed startem:
    import os
    if not os.environ.get("OPENVERSE_CLIENT_ID"):
        self.log("⚠ OPENVERSE_CLIENT_ID not set!")
        self.log("Gallery/Extended requires Openverse API key.")
        self.log("Register: see .env.example for instructions.")
        self.log("Starter (500 images) works without key.")
        return

_check_library_status: zlicza ze WSZYSTKICH LIBRARY_DIRS.
  0 → red "EMPTY", <500 → orange, <5000 → yellow, >=5000 → green

Pobieranie w osobnym wątku z self.after(0, _update) dla GUI.
```

---

### Krok 2.3 — Aktualizacja indeksera (multi-dir + mkdir)
🤖 **Claude Code**

```
Polecenie:

W src/indexer_smart.py:

LIBRARY_DIRS = [
    Path("data/library_starter/tiles"),
    Path("data/library_public/tiles"),
    Path("data/library_extended/tiles"),
    Path("data/library_private/tiles"),
]

Na początku indeksowania:
    for lib_dir in LIBRARY_DIRS:
        lib_dir.mkdir(parents=True, exist_ok=True)
        count = len(list(lib_dir.glob("*.jpg")))
        print(f"  {lib_dir}: {count} images")
```

---

### Krok 2.4 — Skrypt curacji starter packa
🤖 **Claude Code**

```
Polecenie:

Stwórz src/tools/curate_starter.py:

Farthest-point sampling w LAB do 500 zdjęć.
WAŻNE: NIE usuwaj odrzuconych — przenieś do data/library_starter/rejected/
    rejected_dir = Path("data/library_starter/rejected")
    rejected_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(f), str(rejected_dir / f.name))

Działa na data/library_starter/tiles/ PO zakończeniu pobierania.
```

---

### Krok 2.5 — .env.example i .gitignore
🤖 **Claude Code**

```
Polecenie:

1. .env.example:

   # === IMAGE SOURCES ===
   
   # Openverse API (główne źródło CC0). Rejestracja (jednorazowo):
   # python -c "import requests; r=requests.post('https://api.openverse.org/v1/auth_tokens/register/', json={'name':'Neural-Mosaic','description':'Photomosaic tile downloader','email':'p.lazowski.1986@gmail.com'}); print(r.json())"
   # Bez klucza: 100 req/dzień. Z kluczem: 10000 req/dzień.
   OPENVERSE_CLIENT_ID=
   OPENVERSE_CLIENT_SECRET=
   
   # Poniższe źródła są przygotowane na przyszłość — OBECNIE NIEUŻYWANE:
   # RIJKS_API_KEY=
   # EUROPEANA_API_KEY=

2. .gitignore (rozszerz istniejący z Kroku 0.1, zachowaj wpisy):
   data/library_starter/tiles/
   data/library_starter/rejected/
   data/library_public/tiles/
   data/library_extended/tiles/
   data/library_private/tiles/
   data/library_public_BACKUP/
   data/test_download/
   data/download_state.json
   data/smart_index.pkl
   # Session system (Claude Code /start /save /end):
   last_session.md

3. data/LICENSES.md z tabelą źródeł (BEZ Flickr, BEZ LoC)

4. README sekcja "Building the Tile Library" — tabela źródeł
```

---

### Krok 2.5b — Font library bundle + licencje (dystrybucja przez repo)
🤖 **Claude Code** + 👤 **Ręcznie**

## Cel: Dystrybucja 120 fontów Symbol Mosaic przez GitHub repo z pełną
## zgodnością z SIL OFL 1.1 i Apache License 2.0.

## Uzasadnienie decyzji architektonicznej:
## Wszystkie 120 fontów to Google Fonts pod licencjami OFL (~95%) lub
## Apache 2.0 (~5% — tylko rodzina IBM Plex Mono). Obie licencje POZWALAJĄ
## na redystrybucję fontów pod warunkiem dołączenia oryginalnego pliku
## licencji. Opcja bundle w repo była wybrana nad (a) setup script, 
## (b) GitHub Release ZIP, (c) Git LFS — z powodu priorytetu zero-friction
## UX: git clone → python -m src.gui → Symbol Mosaic działa od razu.
## Rozmiar repo wzrośnie o ~80-120 MB (w normie dla GitHub).

---

### Krok 2.5b.1 — Pliki licencji
🤖 **Claude Code**

```
Polecenie:

1. Stwórz katalog assets/fonts/licenses/

2. Stwórz assets/fonts/licenses/OFL.txt z pełną treścią
   SIL Open Font License 1.1 (oficjalne źródło: 
   https://openfontlicense.org/open-font-license-official-text/).
   Ten plik jest wymagany OBOK fontów OFL, jako condition #2 licencji:
   "Original or Modified Versions of the Font Software may be bundled,
    redistributed and/or sold with any software, provided that each 
    copy contains the above copyright notice and this license."

3. Stwórz assets/fonts/licenses/Apache-2.0.txt z pełną treścią
   Apache License 2.0 (oficjalne źródło:
   https://www.apache.org/licenses/LICENSE-2.0.txt).
   Wymagany dla rodziny IBM Plex Mono (14 wariantów).

4. Stwórz assets/fonts/licenses/README.md z tabelą mapowania
   font → licencja. Struktura:
   
   # Font Library — Licenses
   
   Neural-Mosaic bundles 120 open-source fonts for Symbol Mosaic 
   rendering. All fonts are licensed under either SIL Open Font 
   License 1.1 (OFL) or Apache License 2.0.
   
   ## License mapping
   
   | Font family | Files count | License | Source |
   |---|---|---|---|
   | IBM Plex Mono | 14 (Thin–Bold + Italics) | Apache-2.0 | [github.com/IBM/plex](https://github.com/IBM/plex) |
   | Noto Sans family (JP/SC/KR/TC/Regular/Condensed) | 7 | OFL-1.1 | [Google Fonts](https://fonts.google.com/noto) |
   | Noto Sans Ancient Scripts (Egyptian, Cuneiform, Runic, etc.) | 24 | OFL-1.1 | [Google Fonts](https://fonts.google.com/noto) |
   | Noto Sans Symbols, Math, Music, Emoji | 5 | OFL-1.1 | [Google Fonts](https://fonts.google.com/noto) |
   | Noto Serif (JP/KR/SC/TC/Sinhala) | 8 | OFL-1.1 | [Google Fonts](https://fonts.google.com/noto) |
   | Noto Sans Regional (Arabic, Bengali) | 8 | OFL-1.1 | [Google Fonts](https://fonts.google.com/noto) |
   | JetBrains Mono | 1 (variable) | OFL-1.1 | [jetbrains.com/lp/mono](https://www.jetbrains.com/lp/mono/) |
   | Inconsolata | 1 (variable) | OFL-1.1 | [Google Fonts](https://fonts.google.com/specimen/Inconsolata) |
   | Space Mono | 1 | OFL-1.1 | [Google Fonts](https://fonts.google.com/specimen/Space+Mono) |
   | Yarndings (12, 20, 20Charted) | 3 | OFL-1.1 | [Google Fonts](https://fonts.google.com) |
   | Decorative (Creepster, Eater, Monoton, Matemasie, etc.) | 14 | OFL-1.1 | [Google Fonts](https://fonts.google.com) |
   | Handwriting (Sacramento, Tangerine, DancingScript, etc.) | 15 | OFL-1.1 | [Google Fonts](https://fonts.google.com) |
   | Latin Clean (NotoSans, Krub, Itim, Niramit, etc.) | 13 | OFL-1.1 | [Google Fonts](https://fonts.google.com) |
   | CJK Japanese (MPLUS1p, SawarabiMincho, Chokokutai, etc.) | 5 | OFL-1.1 | [Google Fonts](https://fonts.google.com) |
   | Other (Sinhala variants, Tajawal, ReemKufi, Almarai, Amiri) | 6 | OFL-1.1 | [Google Fonts](https://fonts.google.com) |
   
   ## Full license texts
   
   - [OFL.txt](./OFL.txt) — SIL Open Font License 1.1
   - [Apache-2.0.txt](./Apache-2.0.txt) — Apache License 2.0
   
   ## Copyright holders
   
   Individual fonts carry their own copyright notices embedded in the
   font metadata. To view per-font copyright:
   
   ```python
   from PIL import ImageFont
   font = ImageFont.truetype("assets/fonts/NotoSansJP-Regular.ttf", 12)
   print(font.font.family, font.font.style)
   ```
   
   For canonical copyright attribution, see each font's page on
   Google Fonts or the source repository linked above.
   
   ## No attribution required in rendered output
   
   Per OFL 1.1 FAQ 1.1 and Apache 2.0: attribution is NOT required
   when using fonts in rendered output (mosaics). Attribution IS 
   required only when redistributing the font files themselves —
   which is why these license files exist in this directory.
   
   ## Reporting issues
   
   If you believe a font is misattributed or missing its license,
   please open an issue on the Neural-Mosaic repository.
```

---

### Krok 2.5b.2 — .gitattributes dla fontów
🤖 **Claude Code**

```
Polecenie:

Stwórz LUB zaktualizuj plik .gitattributes w root projektu:

# Binary fonts — prevent line-ending conversions, git diff noise
assets/fonts/*.ttf binary
assets/fonts/*.otf binary
assets/fonts/*.ttc binary

# License text files — normal text handling (CRLF on Windows OK)
assets/fonts/licenses/*.txt text
assets/fonts/licenses/*.md text

Powód:
- .ttf/.otf są binarne — bez "binary" Git próbuje wykonać 
  line-ending conversion i pokazuje "binary files differ" przy 
  każdym check'u. Flaga binary rozwiązuje to raz na zawsze.
- Licencje to zwykły tekst — niech Git normalizuje jak zwykle.
```

---

### Krok 2.5b.3 — Guard rail w GUI (empty fonts directory)
🤖 **Claude Code**

```
Polecenie:

W src/gui.py, w metodzie load_typo_index() (lub analogicznie
w scan_fonts() — wybierz tę która robi initial load), 
dodaj SPRAWDZENIE czy assets/fonts/ nie jest pusty:

    def load_typo_index(self):
        def _load():
            # Guard rail: empty fonts directory means broken clone
            fonts_dir = Path("assets/fonts")
            ttf_count = len(list(fonts_dir.glob("*.ttf"))) if fonts_dir.exists() else 0
            
            if ttf_count == 0:
                self.log("ERROR: assets/fonts/ is empty or missing.")
                self.log("Neural-Mosaic ships with 120 fonts bundled in the repo.")
                self.log("If you see this error, your clone is incomplete.")
                self.log("Check: https://github.com/Piotr1686/neural-mosaic/tree/main/assets/fonts")
                self.log("Fix: git pull OR re-clone with 'git clone --depth 1'")
                self.lbl_typo_status.configure(
                    text="Status: Fonts missing!", text_color="red"
                )
                return
            
            # ... istniejąca logika ładowania Typo Index
            self.log(f"Loading Font Index from disk... ({ttf_count} TTF files in assets/fonts/)")
            # ... reszta bez zmian
        threading.Thread(target=_load).start()

Powód: edge case — ktoś sklonuje repo na slow connection i clone 
się przerwie, albo dostawca git (np. GitHub mirror) ma problem. 
Zamiast cichego błędu "Symbol Mosaic doesn't work" — jasny komunikat
co jest nie tak i jak to naprawić.
```

---

### Krok 2.5b.4 — Sanity check + commit fontów
👤 **Ręcznie**

```
Co zrobić:

1. Sprawdź rozmiar zawartości assets/fonts/ PRZED commitem:

   PowerShell:
   (Get-ChildItem assets\fonts -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB

   Oczekiwane: ~80-120 MB. Jeśli > 200 MB — niepokojąco dużo, 
   sprawdź czy nie ma przypadkowych bloatów (np. .otc, .woff2).

2. Sprawdź czy żaden POJEDYNCZY plik nie przekracza 100 MB 
   (GitHub hard limit):

   Get-ChildItem assets\fonts\*.ttf | Sort-Object Length -Descending | Select-Object -First 3 Name, Length

   Typowy największy: NotoSerifJP-Regular.ttf ~8-10 MB. 
   Jeśli coś > 100 MB — zgłoś, bo to anomalia.

3. Sprawdź że .gitignore NIE wyklucza assets/fonts/:

   findstr /I "assets.fonts\|fonts/" .gitignore

   Powinno zwrócić PUSTO. Jeśli zwróci linię — usuń ją z .gitignore.

4. Commit fontów:

   git add assets/fonts/
   git status | findstr "fonts"       # potwierdź że ~120+ plików + licenses/
   git commit -m "feat(fonts): bundle 120 OFL/Apache fonts for Symbol Mosaic (+ licenses)"

   UWAGA: Ten commit będzie DUŻY (~80-120 MB, jednorazowy).
   Po nim fonty się nie zmieniają, więc nie obciążają przyszłej 
   historii. Kolejne commity będą normalne.

5. Sprawdź wynik:

   git log --stat -1 | findstr "fonts"
   
   Powinno pokazać: "assets/fonts/... | XXX +++++++..."
   z liczbą plików w setkach.
```

---

### Krok 2.6 — Rejestracja klucza Openverse API
👤 **Ręcznie**

```
Co zrobić:

Preferowana metoda (Python — działa na Windows bez problemów).
Email już wpisany — wystarczy uruchomić:

python -c "import requests; r=requests.post('https://api.openverse.org/v1/auth_tokens/register/', json={'name':'Neural-Mosaic','description':'Photomosaic tile downloader','email':'p.lazowski.1986@gmail.com'}); print(r.json())"

Alternatywa (curl — uwaga: w PowerShell `curl` to alias
Invoke-WebRequest, użyj cmd.exe lub Git Bash):

curl -X POST https://api.openverse.org/v1/auth_tokens/register/ ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Neural-Mosaic\",\"description\":\"Photomosaic tile downloader\",\"email\":\"p.lazowski.1986@gmail.com\"}"

Wynik: JSON z client_id i client_secret.
Wpisz oba do .env (który utwórz jako kopię .env.example):
  OPENVERSE_CLIENT_ID=abc123...
  OPENVERSE_CLIENT_SECRET=xyz789...

WAŻNE: .env jest w .gitignore — NIE commituj go.
Na email p.lazowski.1986@gmail.com może przyjść verification link —
kliknij go, inaczej klucz po kilku dniach przestanie działać.
```

---

### Krok 2.7 — Test downloadera (osobny katalog!)
👤 **Ręcznie**

```
⚠️ NAJPIERW test, POTEM właściwe pobieranie!

KROK A — Test (10 zdjęć):

python -c "
from src.downloader_v2 import PoliteDownloader
d = PoliteDownloader('data/test_download')
d.download('starter')
"
→ Przerwij po ~10 pobranych (Ctrl+C)
→ Sprawdź data/test_download/: pliki .jpg, 30-80 KB, otwierają się
→ Usuń: rmdir /S /Q data\test_download

KROK B — Właściwe pobieranie (GUI):

1. python -m src.gui
2. "Download Starter (500 · ~25 MB)" → ~15-30 min
3. "Update / Create Index" → "Indexing Complete!"
4. "Load Smart Index" → mozaika testowa 2K → sprawdź
5. git add . && git commit -m "Faza 2 complete — tile library system"
```

---

# ═══════════════════════════════════════
# FAZA 3: SHOWCASE MOSAICS
# Czas: ~2-3 godziny
# ═══════════════════════════════════════

## Cel: Wygenerowanie najlepszych mozaik + sanity check

---

### Krok 3.0 — Sanity check przed renderowaniem
🤖 **Claude Code**

```
Polecenie:

Stwórz src/tools/sanity_check.py:

"""
Walidacja przed generowaniem kosztownych mozaik 16K.
Uruchom: python -m src.tools.sanity_check
"""
import pickle
import numpy as np
from pathlib import Path

def check():
    # 1. Indeks istnieje i ma poprawne wymiary
    idx_path = Path("data/smart_index.pkl")
    assert idx_path.exists(), "ERROR: smart_index.pkl not found!"
    
    with open(idx_path, "rb") as f:
        data = pickle.load(f)
    
    features = data["features"]
    paths = data["paths"]
    schema = data.get("schema_version", "unknown")
    
    assert features.shape[1] == 75, f"ERROR: Expected 75-dim, got {features.shape[1]}"
    print(f"✓ Index schema: {schema}, dimensions: {features.shape[1]}")
    
    # 2. Minimum 500 kafelków
    assert len(paths) >= 500, f"ERROR: Only {len(paths)} tiles (need ≥500)"
    print(f"✓ Tile count: {len(paths)}")
    
    # 3. Wartości LAB w sensownym zakresie (0-1 po normalizacji)
    sample = features[:100]
    assert sample.min() >= -0.1, f"ERROR: Feature values below -0.1"
    assert sample.max() <= 1.5, f"ERROR: Feature values above 1.5"
    print(f"✓ Feature range: [{sample.min():.3f}, {sample.max():.3f}]")
    
    # 4. Pliki kafelków istnieją na dysku
    missing = sum(1 for p in paths[:100] if not Path(p).exists())
    assert missing == 0, f"ERROR: {missing}/100 sampled tiles missing from disk!"
    print(f"✓ Tile files: spot check passed (100/100 exist)")
    
    # 5. RAM check
    import shutil
    free_gb = shutil.disk_usage(".").free / (1024**3)
    print(f"✓ Free disk: {free_gb:.1f} GB")
    
    import psutil
    ram_gb = psutil.virtual_memory().available / (1024**3)
    print(f"✓ Free RAM: {ram_gb:.1f} GB")
    if ram_gb < 3:
        print("⚠ WARNING: <3 GB free RAM. 16K rendering may fail.")
    
    print("\n✅ ALL CHECKS PASSED — safe to render showcase mosaics.")

if __name__ == "__main__":
    check()

Dodaj psutil do requirements.txt (lub zamień na try/except jeśli 
nie chcesz dodatkowej zależności).
```

---

### Krok 3.1 — Sanity check + wybór źródła
👤 **Ręcznie**

```
Co zrobić:

1. python -m src.tools.sanity_check
   → Wszystkie ✓ muszą przejść. Jeśli ERROR → wróć do Fazy 1 lub 2.

2. Wybierz zdjęcie źródłowe: public domain lub własne, 
   silny kontrast, różnorodne kolory.
```

---

### Krok 3.2 — Generowanie mozaik 16K (photo)
👤 **Ręcznie**

```
NOTE: 16K wymaga ~2-4 GB wolnego RAM. Zamknij inne aplikacje.

PHOTO MOSAICS (zakładka Smart Photo Mosaic):
1. Shape: square, 16K → showcase_square_16k.jpg
2. Shape: hexagon, 16K → showcase_hexagon_16k.jpg
3. Shape: kite, 16K → showcase_kite_16k.jpg
4. Przeskaluj dla README (1600px) + detail crops (800×800)

Cel: 3 photo mosaics demonstrujące różne tile shapes.
```

---

### Krok 3.2b — Generowanie mozaik symbolowych 8K (v6 — ROZSZERZONE)
👤 **Ręcznie**

```
NOTE: 8K dla symbol mosaic to dobra równowaga czas/jakość.
Mozaiki z symboli mają ogromną liczbę glifów (np. 400 cols × 250 rows = 100K
symboli) — 16K jest zbędne i zwiększa czas renderowania do 30+ minut.

Użyj TEGO SAMEGO zdjęcia źródłowego co Photo Mosaics dla spójności galerii.

SYMBOL MOSAICS (zakładka Symbol Mosaic (Typo)):

1. Latin Clean + black_on_white + Palette 16 + Variation 20, 8K
   → showcase_symbol_latin_bw_8k.png
   Rationale: "editorial" aesthetic — czytelne, profesjonalne.

2. CJK + black_on_white + Palette 16 + Variation 20, 8K
   → showcase_symbol_cjk_bw_8k.png
   Rationale: "manuscript" aesthetic — gęsta, rytmiczna tekstura.

3. Ancient & Exotic Scripts + color_on_black + Palette 16 + Variation 20, 8K
   → showcase_symbol_ancient_color_8k.png
   Rationale: pokazuje NOWY tryb color_on_black (z v5) + NOWĄ grupę 
   fontów historycznych. Killer feature dla portfolio.

4. Symbols & Geometric + white_on_black + Palette Full + Variation 5, 8K
   → showcase_symbol_geometric_wb_8k.png
   Rationale: abstract poster aesthetic — piktogramy, symbole matematyczne,
   Yarndings. Najbardziej "wow" wizualnie.

Po wygenerowaniu:
- Przeskaluj każdą do 1600px szerokości dla README
- Zrób detail crops 800×800 (4 crops — jeden per symbol mosaic) 
  pokazujące czytelność glifów z bliska
- Zapisz w assets/examples/:
    symbol_latin_bw_1600.png + symbol_latin_bw_detail.png
    symbol_cjk_bw_1600.png   + symbol_cjk_bw_detail.png
    symbol_ancient_color_1600.png + symbol_ancient_color_detail.png
    symbol_geometric_wb_1600.png  + symbol_geometric_wb_detail.png
```

---

### Krok 3.3 — Nagranie GIF z GUI (photo tab)
👤 **Ręcznie**

```
ScreenToGif, 800px, 12-15 FPS, < 5 MB → assets/demo.gif

Zawartość GIF:
- Uruchomienie aplikacji
- Załadowanie obrazu (Photo tab)
- Zmiana tile shape (widoczna zmiana w preview)
- Kliknięcie Render
- Pojawienie się wyniku
```

---

### Krok 3.4 — Nagranie GIF z Symbol Mosaic GUI (v6 — NOWY)
👤 **Ręcznie**

```
Drugi GIF pokazujący flow Symbol Mosaic — demonstruje bogactwo kontrolek.
ScreenToGif, 800px, 12-15 FPS, < 5 MB → assets/demo_symbol.gif

Zawartość GIF (~20 sek):
- Przełączenie na zakładkę "Symbol Mosaic (Typo)"
- Load Typo Index → "Status: Ready (32124 sym)"
- Wybór checkboxów Font Groups (np. Latin Clean OFF → Ancient ON)
- Zmiana Style Mode: black_on_white → color_on_black
- Zmiana Palette Size: 16 → Full
- Kliknięcie RENDER SYMBOL MOSAIC
- (opcjonalnie) końcowa klatka z wygenerowanym wynikiem

Cel: pokazać że Symbol Mosaic to NIE jest "ASCII art converter",
tylko zaawansowane narzędzie z wieloma wymiarami ekspresji.

git add . && git commit -m "Faza 3 complete — showcase mosaics (photo + symbol) + demo GIFs"
```

---

# ═══════════════════════════════════════
# FAZA 4: README VISUAL ASSETS
# Czas: ~2-3 godziny
# v6: rozszerzona o drugi zoom GIF + sekcję README dla Symbol Mosaic
# ═══════════════════════════════════════

### Krok 4.1 — Skrypt zoom GIF (z optymalizacją crop-first)
🤖 **Claude Code**

```
Polecenie:

Stwórz src/tools/make_zoom_gif.py:

KRYTYCZNE — optymalizacja dla obrazów 16K:
Algorytm MUSI najpierw obliczyć bounding box (ROI) dla danej klatki,
użyć img.crop() do wycięcia TYLKO tego fragmentu z obrazu 16K,
a dopiero potem resize() do 800×450.
NIE WOLNO robić resize() całego obrazu 16K w każdej klatce.

Easing sinusoidal, 40 klatek, 70ms/frame, pauza 800ms.
Usage: python -m src.tools.make_zoom_gif <input> <output.gif>

Skrypt ma być GENERYCZNY — działa zarówno na JPG (photo mosaic) 
jak i PNG (symbol mosaic). Nie hardkoduj formatu wejścia/wyjścia.
```

---

### Krok 4.2 — Generowanie obu GIF-ów zoom + sekcja Photo w README
👤 **Ręcznie** + 🤖 **Claude Code**

```
Ręcznie:

1. Photo mosaic zoom:
   python -m src.tools.make_zoom_gif output/showcase_hexagon_16k.jpg assets/examples/mosaic_zoom.gif

2. Symbol mosaic zoom (v6 — NOWY):
   python -m src.tools.make_zoom_gif output/showcase_symbol_cjk_bw_8k.png assets/examples/symbol_zoom.gif
   
   Uwaga: dla symbol mosaic zoom faktycznie DOBRZE wygląda — widzisz
   jak z daleka glify zlewają się w obraz, a z bliska są rozpoznawalne.
   To jest killer feature Symbol Mosaic — zoom GIF to perfekcyjnie 
   demonstruje.

Claude Code:
W README dodaj zoom GIF dla photo mosaic, tabelę rozmiarów wydruku, 
i sekcję Troubleshooting:

### ❓ Troubleshooting
**Q: Downloader zwraca 429 Too Many Requests**
A: Poczekaj 1 godzinę. Dla Starter — działa bez klucza API.
   Dla Gallery/Extended — zarejestruj klucz (patrz .env.example).

**Q: Mozaika 16K się nie generuje / crash**
A: Zamknij inne aplikacje. Wymagane ~3 GB wolnego RAM.
   Alternatywnie: generuj w 8K.

**Q: WARNING o niezgodnym indeksie**
A: Kliknij "Update / Create Index" w GUI aby przebudować.

**Q: Przycisk RENDER SYMBOL MOSAIC nie widoczny**
A: Przewiń zawartość zakładki w dół (scroll). Okno ma layout 2-kolumnowy 
   od v5.8 — wszystkie kontrolki są scrollowalne, przycisk RENDER jest 
   przypięty do dolnej krawędzi zakładki i zawsze widoczny.
```

---

### Krok 4.3 — Sekcja "Symbol Mosaic Gallery" w README (v6 — NOWY)
🤖 **Claude Code**

```
Polecenie:

W README.md dodaj nową sekcję "Symbol Mosaic Gallery" ZARAZ PO sekcji 
"Gallery" (photo mosaics). Kolejność sekcji:

  1. # Neural-Mosaic (tytuł + badges)
  2. ## Gallery (photo mosaics — 3 shapes × before/after)
  3. ## Symbol Mosaic Gallery (NOWA — 4 trybów symbolicznych)
  4. ## Quick Start
  5. ...

Treść sekcji "Symbol Mosaic Gallery":

---

## Symbol Mosaic Gallery

Neural-Mosaic includes a **typographic rendering engine** that replaces 
pixels with glyphs from 120 fonts spanning 7 thematic groups — from 
Latin monospace to CJK scripts, Ancient hieroglyphs, mathematical 
symbols and more. Each mode produces a visually distinct aesthetic.

### Four modes, four aesthetics

<table>
  <tr>
    <td align="center">
      <b>Latin Clean — Black on White</b><br>
      <img src="assets/examples/symbol_latin_bw_1600.png" width="400"><br>
      <i>Editorial aesthetic — readable, professional.</i><br>
      <img src="assets/examples/symbol_latin_bw_detail.png" width="200">
    </td>
    <td align="center">
      <b>CJK Scripts — Black on White</b><br>
      <img src="assets/examples/symbol_cjk_bw_1600.png" width="400"><br>
      <i>Manuscript aesthetic — dense, rhythmic texture.</i><br>
      <img src="assets/examples/symbol_cjk_bw_detail.png" width="200">
    </td>
  </tr>
  <tr>
    <td align="center">
      <b>Ancient Scripts — Color on Black</b><br>
      <img src="assets/examples/symbol_ancient_color_1600.png" width="400"><br>
      <i>Egyptian hieroglyphs, cuneiform, runes on dark canvas.</i><br>
      <img src="assets/examples/symbol_ancient_color_detail.png" width="200">
    </td>
    <td align="center">
      <b>Symbols & Geometric — White on Black</b><br>
      <img src="assets/examples/symbol_geometric_wb_1600.png" width="400"><br>
      <i>Math, arrows, piktograms — abstract poster.</i><br>
      <img src="assets/examples/symbol_geometric_wb_detail.png" width="200">
    </td>
  </tr>
</table>

### Zoom animation

![Symbol Mosaic Zoom](assets/examples/symbol_zoom.gif)

*Watch glyphs resolve into recognizable characters as you zoom in —
32,124 indexed symbols from 120 fonts.*

### Controls

| Parameter      | Options                                         | Effect |
|---------------|--------------------------------------------------|--------|
| Font Groups   | CJK · Ancient · Symbols · Latin · Decorative · Handwriting · Other | Visual aesthetic family |
| Style Mode    | `black_on_white` · `white_on_black` · `color_on_white` · `color_on_black` | Background + glyph fill strategy |
| Palette Size  | 8 · 16 · 32 · Full                               | Color quantization (posterization) |
| Variation     | 5 · 20 · 50                                      | Glyph selection randomness (lower = sharper) |
| Symbol Size   | 0.5× · 0.75× · 1.0× · 1.75× · 2.0×               | Glyph grid density |

See [How It Works — Symbol Mosaic](#how-it-works) for technical details 
on density matching and font grouping.

### Font Library (bundled with the repo)

All 120 fonts are included in `assets/fonts/`. No separate download 
required — fonts are distributed under SIL Open Font License 1.1 or 
Apache License 2.0, which permit redistribution. Full license texts 
and attribution are in `assets/fonts/licenses/`.

Font groups breakdown:
- **CJK** (13 fonts): NotoSans/Serif JP/SC/KR/TC, Sawarabi Mincho, 
  Chokokutai, MPLUS1p, and more
- **Ancient & Exotic Scripts** (24 fonts): Egyptian Hieroglyphs, 
  Cuneiform, Runic, Linear A/B, Phoenician, Ogham, Deseret, Shavian, etc.
- **Symbols & Geometric** (9 fonts): NotoSansMath, NotoMusic, 
  NotoEmoji, Yarndings 12/20
- **Latin Clean** (19 fonts): NotoSans family + IBM Plex Mono 
  (14 weights incl. italics) + JetBrains Mono + Inconsolata + Space Mono
- **Decorative / Display** (14 fonts): Creepster, Monoton, Matemasie, 
  BitcountPropDouble variants, Danfo, Splash, and more
- **Handwriting / Script** (15 fonts): DancingScript, Sacramento, 
  Tangerine, Allura, PinyonScript, and more
- **Other** (12 fonts): Arabic, Bengali, Sinhala, Amiri, Tajawal

---

KONIEC sekcji.

Uwaga dot. czcionek: sekcja wymienia 120 fontów z 7 grup tematycznych. 
Jeśli liczby nie zgadzają się z faktycznym stanem po Fazie 1.5 
(może się okazać że część fontów nie ma glifów w indeksie), 
zaktualizuj liczby do faktycznych (sprawdź `Status: Ready (XXXXX sym)`
w GUI po załadowaniu Typo Index).

Po dodaniu sekcji:
git add . && git commit -m "Faza 4 complete — zoom GIFs, Symbol Mosaic Gallery, print table, troubleshooting"
```

---

# ═══════════════════════════════════════
# FAZA 5: DEEP ZOOM VIEWER
# Czas: ~3-4 godziny
# Ograniczenie: max 2 mozaiki (limit GitHub Pages)
# ═══════════════════════════════════════

### Krok 5.1 — Generator DZI
🤖 **Claude Code**

```
Polecenie:

Stwórz src/tools/make_dzi.py — generator piramidy DZI.
TileSize=256, Overlap=1, JPEG quality 70 (zoptymalizowane dla Pages).
Generuje plik .dzi XML + katalog _files/ z poziomami.

OGRANICZENIE: generuj max 2 mozaiki (np. hexagon + symbol)
aby nie przekroczyć rozmiaru repo.
Opcja --max-level 13 obcina do 8K jeśli rozmiar za duży.

Stwórz też src/tools/make_all_tiles.py (batch, 2 mozaiki).
```

---

### Krok 5.2 — Generowanie + strona viewera
👤 **Ręcznie** + 🤖 **Claude Code**

```
Ręcznie: python -m src.tools.make_all_tiles
Sprawdź: docs/tiles/ < 150 MB (2 mozaiki × ~60-75 MB)

Claude Code: docs/index.html, docs/css/viewer.css, docs/js/viewer.js
Dark theme, OpenSeadragon CDN, przełączanie z savedBounds,
keyboard 1-2/H/F, .nojekyll, robots.txt

Claude Code: src/tools/make_og_preview.py (1200×630)
Claude Code: link w README
```

---

### Krok 5.3 — Test i deploy
👤 **Ręcznie**

```
1. python -m src.tools.make_og_preview output/best.jpg docs/img/og_preview.jpg
2. cd docs && python -m http.server 8000 → test
3. git add . && git commit -m "Faza 5 complete — Deep Zoom viewer"
4. git push
5. GitHub Settings → Pages → main → /docs → Save
6. Sprawdź: piotr1686.github.io/neural-mosaic/
```

---

# ═══════════════════════════════════════
# FAZA 6: GITNEXUS INTEGRATION (MIN — OPCJA B)
# Czas: ~45 minut
# Wymaga: git history (Faza 0)
# Scope: graf architektury + screenshot w README
# POMINIĘTO: Krok 6.5 (pre-publish audit detect_changes)
# ═══════════════════════════════════════

## Uzasadnienie wyboru opcji B

Wersja minimalna daje portfolio-grade artefakt (graf architektury w `docs/ARCHITECTURE.md` + screenshot w README) przy niewielkim koszcie czasowym. Pre-publish audit z `detect_changes` pomijamy — na świeżo publikowanym repo nie ma jeszcze historii refactoringów, więc analiza zmian nie miałaby czego porównywać. Wróci naturalnie przy v5.1/v6.0, kiedy będą pierwsze PR-y i bugfixy.

---

### Krok 6.1 — Backup CLAUDE.md
🤖 **Claude Code**

```
Polecenie:

Przed uruchomieniem GitNexus skopiuj istniejący CLAUDE.md:
    cp CLAUDE.md CLAUDE.md.backup

To krytyczne — `gitnexus analyze` nadpisuje CLAUDE.md własną wersją.
```

---

### Krok 6.2 — Indeksowanie projektu
👤 **Ręcznie**

```
Co zrobić:

cd D:\Programming_Projects\Neural-Mosaic
npx gitnexus analyze --skills --verbose

Oczekiwany output:
- .gitnexus/           (grafowa baza LadybugDB)
- .claude/skills/generated/   (opisy klastrów)
- CLAUDE.md            (nadpisany — dlatego backup w 6.1)
- AGENTS.md            (auto-wygenerowany)

UWAGA: komenda WYMAGA repozytorium git z commitami (Faza 0 + commity 
po każdej fazie załatwiają to wymaganie).
```

---

### Krok 6.3 — Merge CLAUDE.md
🤖 **Claude Code**

```
Polecenie:

Zmerguj dwa pliki CLAUDE.md:

1. Odczytaj CLAUDE.md.backup (oryginalny — moje konwencje, hardware,
   tech stack, VRAM budget, @vram_safe decorator).
2. Odczytaj CLAUDE.md (wygenerowany przez GitNexus — zawiera strukturę
   kodu, klastry, ścieżki wykonania).
3. Stwórz zmergowaną wersję:
   - Zachowaj WSZYSTKIE sekcje z backupu (to są moje ręczne konwencje).
   - Dołącz z GitNexus tylko sekcje o strukturze projektu i klastrach.
   - Unikaj duplikacji — jeśli coś jest w obu wersjach, wybierz tę
     z backupu (bardziej dopracowaną).
4. Po merge'u usuń CLAUDE.md.backup.

KRYTYCZNE — OCHRONA SEKCJI SESSION SYSTEM:
Jeśli CLAUDE.md.backup zawiera sekcję dotyczącą session state management
(charakterystyczne frazy: "Pliki stanu sesji", "MEMORY.md", 
"last_session.md", "/start", "/save", "/end", ".claude/commands/"),
MUSISZ ją zachować w merge'u W NIETKNIĘTEJ FORMIE.

GitNexus nie wie o systemie sesji i potencjalnie może uznać te sekcje
za "nieistotne do struktury kodu". Nie ufaj heurystyce GitNexus w tym
zakresie — sekcja session system to workflow developerski, musi przetrwać.

Jeśli nie jesteś pewien czy sekcja dotyczy session system — ZAPYTAJ
zamiast usuwać.

Format finalny: zachowaj nagłówki markdown, czytelną strukturę.
```

---

### Krok 6.4 — .gitignore + docs/ARCHITECTURE.md
🤖 **Claude Code**

```
Polecenie:

1. Dodaj do .gitignore (jeśli jeszcze nie ma):
   .gitnexus/
   .claude/skills/generated/
   
   (te katalogi zawierają lokalny indeks — nie commitujemy ich)

2. Stwórz docs/ARCHITECTURE.md z diagramem Mermaid pokazującym
   główne moduły projektu i ich zależności. Struktura:
   
   # Architecture
   
   Krótkie wprowadzenie (2-3 zdania) co to za projekt i jakie ma
   główne komponenty.
   
   ## Module Dependency Graph
   
   ```mermaid
   graph TD
       GUI[gui.py — CustomTkinter]
       Engine[engine_smart.py — SmartEngine]
       Indexer[indexer_smart.py — FeatureIndexer]
       Downloader[downloader_v2.py — PoliteDownloader]
       Tools[tools/ — curate, sanity_check, make_dzi, make_zoom_gif]
       
       GUI --> Engine
       GUI --> Indexer
       GUI --> Downloader
       Engine --> Indexer
       Tools --> Indexer
   ```
   
   ## Key Modules
   
   Krótki opis (2-3 zdania) każdego głównego modułu i jego roli.
   
   ## Data Flow
   
   1. Pobieranie: Downloader → library_*/tiles/
   2. Indeksowanie: Indexer → smart_index.pkl (75-dim LAB features)
   3. Renderowanie: Engine → output/*.jpg
   
   Użyj kontekstu z GitNexus (klastry, ścieżki wykonania) do wypełnienia
   szczegółów — ale diagram ma być PROSTY i czytelny, max 10-12 węzłów.
```

---

### Krok 6.5 — [POMINIĘTO w opcji B]

```
Krok 6.5 (pre-publish audit z detect_changes) został POMINIĘTY.

Uzasadnienie:
- Na świeżo publikowanym repo brak historii refactoringów do porównania.
- detect_changes i blast radius mają sens przy v5.1+ (bugfixy, nowe PR-y).
- Dodać w przyszłości: gdy pojawi się ~10 commitów zmian merytorycznych
  po publikacji, uruchom `npx gitnexus detect-changes` przed większym 
  refactoringiem i zaktualizuj docs/ARCHITECTURE.md.
```

---

### Krok 6.6 — Screenshot grafu zależności
👤 **Ręcznie**

```
Co zrobić:

1. Wejdź na https://gitnexus.vercel.app
2. Spakuj projekt do ZIP (bez data/, __pycache__/, .venv/, .gitnexus/):
   
   PowerShell:
   Compress-Archive -Path src,docs,README.md,*.py,*.toml,*.txt,LICENSE,.env.example `
                    -DestinationPath neural-mosaic-graph.zip
   
3. Wrzuć ZIP na stronę, poczekaj na zaindeksowanie (~1-2 min).
4. Zrób screenshot grafu zależności (pełny widok, ciemne tło jeśli dostępne).
5. Zapisz jako assets/architecture_graph.png (max 1200px szerokości, 
   < 500 KB po optymalizacji np. TinyPNG).
```

---

### Krok 6.7 — Screenshot w README + commit
🤖 **Claude Code**

```
Polecenie:

W README.md, w sekcji "How It Works" (lub nowej "Architecture"),
dodaj po tekstowym opisie:

## Architecture

Neural-Mosaic follows a modular pipeline: a polite multi-source 
downloader builds the tile library, a feature indexer encodes each 
tile into a 75-dimensional LAB descriptor, and the rendering engine 
matches sectors of the target image to the closest tiles using 
cKDTree nearest-neighbour search.

![Architecture Graph](assets/architecture_graph.png)

*Module dependency graph generated with [GitNexus](https://github.com/gitnexus/gitnexus).
Full details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)*

Następnie wykonaj (ręcznie w terminalu):
    git add . 
    git commit -m "Faza 6 complete — GitNexus integration (minimal: architecture graph)"
```

---

# ═══════════════════════════════════════
# FAZA 7: FINALIZACJA
# Czas: ~1-2h
# Zawiera artefakty, które NIE powstały wcześniej w planie
# (LICENSE, requirements.txt, CI, CONTRIBUTING, CHANGELOG)
# ═══════════════════════════════════════

### Krok 7.0 — Artefakty portfolio-grade (brakujące pliki)
🤖 **Claude Code**

```
Polecenie:

Stwórz poniższe pliki. Każdy to osobny plik w root (lub w .github/).

1. LICENSE (MIT):
   Standardowy tekst MIT License, Copyright (c) 2026 Piotr Łazowski.
   Pełny tekst dostępny na https://choosealicense.com/licenses/mit/

2. requirements.txt — zaktualizuj z pinowaniem wersji:
   
   # Core
   customtkinter==5.2.2
   Pillow==10.4.0
   numpy==1.26.4
   scipy==1.13.1
   scikit-image==0.24.0
   
   # AI (opcjonalne — ai_core.py legacy)
   torch==2.3.1
   torchvision==0.18.1
   open-clip-torch==2.26.1
   
   # Downloader (Faza 2)
   requests==2.32.3
   imagehash==4.3.1
   
   # Sanity check (Faza 3)
   psutil==6.0.0
   
   # Deep Zoom (Faza 5, opcjonalne)
   # deepzoom==1.2.0   # odkomentuj jeśli korzystasz z src/tools/make_dzi.py
   
   # Dev (opcjonalne)
   # pytest==8.3.2
   # ruff==0.6.9
   
   Jeśli któraś wersja powoduje konflikt na Win11 + Py3.10,
   poinformuj użytkownika zamiast automatycznie downgrade'ować.

3. CHANGELOG.md:
   
   # Changelog
   
   All notable changes to Neural-Mosaic are documented in this file.
   Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
   
   ## [5.0.0] — 2026-04 — Initial public release
   
   ### Added
   - 5×5 feature grid (75-dim LAB descriptors) replaces 3×3 (27-dim)
   - Color Blend post-processing (0–30%)
   - Tile Tint post-processing (0–40%)
   - Multi-source tile downloader (Openverse + Met + Art Institute + 
     NASA + Cleveland + Wikimedia) with polite rate-limiting
   - Perceptual-hash deduplication (imagehash.phash, Hamming < 5)
   - Quality filter (blur detection + uniform-color rejection)
   - Sanity check tool (src/tools/sanity_check.py)
   - Deep Zoom viewer on GitHub Pages (2 mosaics, OpenSeadragon)
   - Architecture diagram (GitNexus + Mermaid)
   - Showcase mosaics at 16K (photo) and 8K (symbol)
   
   ### Added — Symbol Mosaic
   - Thematic font grouping: 7 groups (CJK, Ancient, Symbols, 
     Latin Clean/Mono, Decorative, Handwriting, Other) covering 120 fonts
   - New `color_on_black` mode with HLS lightness boost
   - HLS clamping for `color_on_white` — readable dark colors on white bg
   - Palette size control (8/16/32/Full) for color quantization
   - Variation control (5/20/50) — glyph selection randomness
   - `--full-cjk` flag for indexer (complete CJK Unified Ideographs block)
   - Scrollable tab layout — RENDER button always pinned and visible
   - Full IBM Plex Mono family (14 weights + italics) for fine density matching
   
   ### Changed
   - Hard blocks rendering on index schema mismatch (was WARNING)
   - Library count aggregates all LIBRARY_DIRS
   - Color saturation enhance reduced from 2.5 → 1.3 (was too aggressive)
   
   ### Removed
   - Flickr integration (API key now requires paid account)
   - Library of Congress fetcher (not implemented)

4. CONTRIBUTING.md — skrócona wersja (~30 linii):
   sekcje: Reporting bugs, Feature requests, Development setup
   (python -m venv, pip install -r requirements.txt, 
    python -m src.gui), Code style (PEP 8, docstrings).

5. .github/workflows/ci.yml — minimalny CI:
   
   name: CI
   on: [push, pull_request]
   jobs:
     lint:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with:
             python-version: '3.10'
         - name: Install dependencies
           run: |
             pip install --upgrade pip
             pip install ruff
             # pełne requirements.txt zawiera torch/CUDA — za ciężkie na CI
             # zainstaluj tylko lekkie zależności potrzebne do import check
             pip install customtkinter Pillow numpy scipy scikit-image requests imagehash psutil
         - name: Lint
           run: ruff check src/ --select=E9,F63,F7,F82 --ignore=F401
         - name: Import check
           run: python -c "import src.indexer_smart; import src.engine_smart; import src.downloader_v2; print('OK')"
   
   Uwaga: pełny test runtime GUI nie działa w headless CI
   (CustomTkinter wymaga display). Sprawdzamy tylko importy + składnię.

6. README badges — na samej górze README, zaraz pod tytułem:
   
   ![Python](https://img.shields.io/badge/python-3.10-blue.svg)
   ![License](https://img.shields.io/badge/license-MIT-green.svg)
   ![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey.svg)
   ![CI](https://github.com/Piotr1686/neural-mosaic/actions/workflows/ci.yml/badge.svg)

7. README sekcja "Known Limitations" (PRZED Troubleshooting):
   
   ## Known Limitations
   
   - 16K rendering requires ~3 GB free RAM (not chunked yet).
   - GUI is Windows-focused (CustomTkinter works on Linux/macOS but 
     font stack assumes Windows).
   - Tile Tint uses pixel-wise lerp in RGB space. LAB-space variant
     is on the roadmap but current RGB implementation produces 
     visible, predictable results.
   - Deep Zoom viewer hosts only 2 mosaics due to GitHub Pages size.
   - CC0/PD license filter trusts source metadata — rare false 
     positives on user-uploaded Flickr content reported upstream.
   - Repository size is ~100 MB due to bundled font library 
     (120 OFL/Apache fonts). Initial clone takes ~30-60 seconds.
     Fonts are mandatory for Symbol Mosaic feature — included 
     directly rather than downloaded separately to guarantee 
     zero-friction setup.
```

---

### Krok 7.1 — Smoke test na czystym środowisku (KRYTYCZNE)
👤 **Ręcznie**

```
Co zrobić:

Najważniejszy test — symuluje kogoś, kto klonuje Twoje repo po raz 
pierwszy. Bez tego kroku ryzyko "u mnie działa" rośnie dramatycznie.

1. Stwórz czyste virtualenv:
   cd %TEMP%
   python -m venv neural_mosaic_smoke
   neural_mosaic_smoke\Scripts\activate

2. Klonuj lokalnie (nie push jeszcze — pracuj na kopii):
   git clone D:\Programming_Projects\Neural-Mosaic test_clone
   cd test_clone

3. Instalacja:
   pip install -r requirements.txt
   → czas: ~5-10 min, rozmiar: ~3-5 GB (torch)
   → jeśli fail: poprawka w requirements.txt, nie ignoruj

4. Utwórz .env z zerowymi kluczami (test bez Openverse key):
   copy .env.example .env

5. Uruchomienie bez biblioteki kafelków:
   python -m src.gui
   → GUI startuje? TAK / NIE
   → Kliknięcie Render bez indexu — jasny komunikat błędu?

5.5. WERYFIKACJA FONT LIBRARY (v6.4):
   → Zakładka Symbol Mosaic (Typo) → "Load Typo Index (Fast)"
   → Czy Status pokazuje: "Status: Ready (XXXXX sym)" z liczbą > 30000?
   → Jeśli "Status: Fonts missing!" → fonty nie zostały poprawnie 
     sklonowane (sprawdź assets/fonts/*.ttf count)
   → Wybierz grupę Latin Clean → wybierz input image → RENDER
   → Mozaika 4K w ~1-2 min → otwiera się poprawnie?
   Symbol Mosaic MUSI działać na fresh clone bez dodatkowego setup'u.

6. Pobierz starter (100 req/dzień limit starczy):
   Download Starter → ~15-30 min
   → Pobrało ≥400 zdjęć z 500? (100% = niemożliwe przez dedup/filters)

7. Index + render 2K:
   Update Index → Load → Render 2K
   → Mozaika wygenerowana poprawnie?

8. Sprzątanie:
   cd .. && rmdir /S /Q test_clone neural_mosaic_smoke

Jeśli którykolwiek krok zawiedzie — NAPRAW przed publikacją.
```

---

### Krok 7.2 — Końcowa weryfikacja (checklist)
👤 **Ręcznie**

```
Checklist przed tagowaniem v5.0.0:

PLIKI I STRUKTURA
[ ] LICENSE (MIT) w root
[ ] README.md z badges, Gallery (photo), Symbol Mosaic Gallery, Troubleshooting, Known Limitations
[ ] CHANGELOG.md z v5.0.0
[ ] CONTRIBUTING.md
[ ] .github/workflows/ci.yml
[ ] requirements.txt z pinowanymi wersjami
[ ] .gitignore kompletny (data/library_*/tiles, .env, __pycache__)
[ ] .env.example (bez kluczy) — z instrukcją rejestracji
[ ] docs/ARCHITECTURE.md z Mermaid + screenshot

SHOWCASE ASSETS
[ ] 3 photo mosaics 16K (square, hexagon, kite) w assets/examples/
[ ] 4 symbol mosaics 8K (Latin, CJK, Ancient, Symbols) w assets/examples/
[ ] 2 zoom GIF-y (photo + symbol), każdy < 5 MB
[ ] Detail crops (800×800) dla każdej mozaiki

FONT LIBRARY (v6.4)
[ ] assets/fonts/ zawiera ~120 plików .ttf
[ ] assets/fonts/licenses/OFL.txt obecny (SIL OFL 1.1 official text)
[ ] assets/fonts/licenses/Apache-2.0.txt obecny
[ ] assets/fonts/licenses/README.md z tabelą font → licencja
[ ] .gitattributes zawiera "assets/fonts/*.ttf binary"
[ ] assets/fonts/ NIE jest w .gitignore (findstr assets.fonts .gitignore → 0 trafień)
[ ] Rozmiar assets/fonts/ ~80-120 MB (nie > 200 MB)
[ ] Żaden pojedynczy font > 100 MB (GitHub hard limit)
[ ] GUI: guard rail pokazuje error gdy assets/fonts/ empty
[ ] GitHub: assets/fonts/ widoczne w web UI po pushu

NAZEWNICTWO
[ ] "Neural-Mosaic" wszędzie (findstr /S /I "NeuroMosaic" *.py *.md → 0 trafień)
[ ] "neural-mosaic" w URLach (findstr /S /I "neuromosaic" *.py *.md → 0 trafień)

FUNKCJONALNOŚĆ — PHOTO MOSAIC
[ ] python -m src.gui uruchamia się bez błędów
[ ] Istniejąca biblioteka nienaruszona (porównaj z backupem)
[ ] data/test_download/ usunięty
[ ] Download Starter działa (Openverse + muzea + Wikimedia)
[ ] Indeks: 75-dim, schema "5x5" (sanity_check.py przechodzi)
[ ] Mozaika 4K renderuje się poprawnie
[ ] Blend 20% / Tint 20% widoczna różnica
[ ] Niezgodny indeks BLOKUJE rendering (nie WARNING)
[ ] Import własnych zdjęć działa

FUNKCJONALNOŚĆ — SYMBOL MOSAIC (v6)
[ ] Zakładka Symbol Mosaic: przycisk RENDER WIDOCZNY bez scrollowania
[ ] 7 checkboxów Font Groups widoczne i działające
[ ] 4 Style Mode dostępne (black_on_white, white_on_black, color_on_white, color_on_black)
[ ] Palette Size 8/16/32/Full — widoczna różnica w outputach color_on_*
[ ] Variation 5/20/50 — widoczna różnica (ostrość vs organika)
[ ] Rendering z wybraną pojedynczą grupą działa (np. tylko Ancient)
[ ] Rendering z wieloma grupami działa

OGÓLNE
[ ] README renderuje się poprawnie (lokalne grip lub preview)
[ ] GIF z zoomem photo mosaic < 5 MB
[ ] GIF z Symbol Mosaic GUI flow < 5 MB
[ ] Deep Zoom Viewer działa lokalnie

BEZPIECZEŃSTWO
[ ] .env NIE jest w git (git log --all -- .env → pusto)
[ ] Brak hardcoded D:\... (findstr /S /N "D:\\" src\*.py → 0 trafień)
[ ] Brak FLICKR_API_KEY w kodzie
[ ] Brak hardcoded maili/kluczy w src/*.py (tylko w .env.example jako template)

GITHUB READINESS
[ ] Smoke test (Krok 7.1) przechodzi
[ ] CI badge renderuje się w README po push
[ ] Screenshot architektury (assets/architecture_graph.png < 500 KB)
```

---

### Krok 7.3 — Tagowanie + finalny push
👤 **Ręcznie**

```
cd D:\Programming_Projects\Neural-Mosaic

# Upewnij się że wszystko jest zacommitowane
git status   # powinno być "nothing to commit, working tree clean"

# Jeśli coś zostało — ostatni commit
git add .
git commit -m "v5.0 release — final polish"

# Tag semver
git tag -a v5.0.0 -m "Neural-Mosaic v5.0 — initial public release"

# Remote (jednorazowo)
git remote add origin https://github.com/Piotr1686/neural-mosaic.git
git branch -M main

# Push + tagi
git push -u origin main
git push --tags

Po pushu:
1. Sprawdź README na GitHubie — wszystkie obrazy się wczytują
2. Sprawdź CI badge (zielony po ~2 min)
3. GitHub Settings → Pages → main → /docs → Save
4. Sprawdź piotr1686.github.io/neural-mosaic/ (~5 min propagacja)
5. GitHub Releases → Draft new release → tag v5.0.0 → 
   Release notes: wklej CHANGELOG.md sekcję [5.0.0]
6. OG preview: wklej link na LinkedIn (dry run — nie publikuj) 
   i sprawdź czy pokazuje się mozaika
```

---

### Krok 7.4 — Rollback plan (na wypadek problemów)
👤 **Ręcznie** — do zastosowania TYLKO w razie awarii

```
Jeśli po pushu coś pójdzie źle (broken README, niedziałająca mozaika):

MIĘKKI ROLLBACK (preferowany):
  git revert <hash_problematycznego_commita>
  git push

TWARDY ROLLBACK (tylko przed pierwszymi gwiazdkami/forkami):
  git reset --hard <hash_działającego_commita>
  git push --force-with-lease
  UWAGA: force-push niszczy historię widzianą przez innych.
  Nie rób tego jeśli ktoś już sforkował repo.

COFNIĘCIE DO BASELINE (faza po fazie zepsuła silnik):
  git log --oneline | grep "Faza"
  git checkout <hash_commita_"Faza 0 complete">
  git checkout -b recovery
  # teraz jesteś na baseline i możesz zacząć od nowa

USUNIĘCIE PRZYPADKOWO PUSHNIĘTEGO .env:
  git rm --cached .env
  git commit -m "SECURITY: remove accidentally committed .env"
  git push
  # NATYCHMIAST zregeneruj klucz Openverse (poprzedni uznaj za wyciekły):
  # powtórz Krok 2.6 z nowym wywołaniem register endpoint
  # stary klucz musisz revoke'ować ręcznie kontaktem do Openverse
```

---

## Roadmap (po publikacji)

Elementy do rozważenia w przyszłych wersjach:
- `logging` moduł zamiast `print` w całym projekcie
- Testy jednostkowe (pytest) dla indeksera i matchingu
- Benchmark 3×3 vs 5×5 (skrypt SSIM do obiektywnego porównania)
- Tile Tint w przestrzeni LAB (zamiast RGB) — nice-to-have, pixel lerp
  w RGB jest wystarczający; LAB dałby bardziej "percepcyjnie naturalne"
  przejścia ale value marginalna
- Chunked rendering dla maszyn z < 16 GB RAM
- Architektura pluginowa dla tile shapes (BaseTiler)
- config.yaml zamiast rozproszone parametry

---

## Code Review — zmiany v6.4 (font library distribution)

**v6.4-1. Fonty bundled w repo + licensing.** Decyzja architektoniczna:
120 fontów OFL/Apache rozprowadzanych przez repo zamiast downloadera.
Uzasadnienie: priorytet UX (zero-friction clone → run) nad rozmiarem repo
(80-120 MB to w normie dla GitHub). Alternatywy (setup script, GitHub 
Release ZIP, Git LFS) odrzucone z powodu fragile dependencies lub overkill.

**v6.4-2. Licensing compliance.** Zgodność z SIL OFL 1.1 i Apache 2.0 
zapewniona przez `assets/fonts/licenses/` (OFL.txt, Apache-2.0.txt, 
README.md z mapowaniem font → licencja). OFL condition #2 ("must contain
copyright notice and this license") spełniony przez dołączenie pełnych
tekstów licencji. Brak wymagania atrybucji w rendered output (per OFL
FAQ 1.1) — tylko w redystrybucji plików fontów, co robimy.

**v6.4-3. Guard rail w GUI.** Edge case "empty fonts directory" 
(niekompletny clone, corrupt download) obsłużony przez explicit error
w `load_typo_index()`. Użytkownik dostaje actionable message zamiast
niezrozumiałego failure'a Symbol Mosaic.

**v6.4-4. .gitattributes dla fontów.** `assets/fonts/*.ttf binary` 
zapobiega line-ending conversions i fałszywym git diffom ("binary files
differ" przy każdym pull'u). Drobiazg, ale psucie historii bez niego.

**v6.4-5. Smoke test rozszerzony.** Krok 7.1 ma nowy punkt 5.5 
weryfikujący że Symbol Mosaic działa natychmiast po fresh clone, 
bez żadnego dodatkowego setupu. To główny argument za tą decyzją 
architektoniczną — więc powinien być wprost testowany.

---

**v6.3-1. Tile Tint — pixel lerp zamiast mean-shift.** Odkryte podczas
Kroku 1.12 weryfikacji: mozaiki Tint 0% i Tint 20% były wizualnie
identyczne. Diagnoza: stara logika `shift = (sector_mean - tile_mean) *
tint_strength` wychodziła ~0 dla zmatchowanego kafelka, bo matcher
(cKDTree na 75-dim LAB) już dobierał kafelek podobny kolorystycznie do
sektora. `tile_mean ≈ sector_mean → shift ≈ 0`. Nowa logika:
`tile_arr * (1-t) + sector_mean * t` — pixel-wise lerp w stronę
koloru sektora. Zawsze widoczny efekt, niezależnie od matcher'a.
Potwierdzone numerycznie: 60% pikseli różnych > 5 punktów między
Tint 0% a Tint 20% (poprzednio: 0 różnic).

**v6.3-2. Diagnostyczny print dla Tint.** Dodany `Tile Tint active: X%`
PRZED pętlą rendering, analogicznie do `Applying Color Blend`.
Bez tego print'a 3 godziny tropiłem dlaczego tint nie działa —
poprawa debugowalności krytyczna.

**v6.3-3. PowerShell 5.1 compatibility note.** Dodana do Kroku 0.1.
Win11 domyślnie ma PS 5.1 bez operatora `&&`. Reszta planu używa
`&&` w komendach git — bez explicit informacji użytkownik stanie
się co 100 linii.

**Roadmap update:** pozycja "Tile Tint w przestrzeni LAB (zamiast RGB)"
w roadmapie może pozostać jako nice-to-have, ale nie jest krytyczna —
pixel lerp w RGB daje wystarczająco dobry efekt dla tego use case'u.
Ewentualnie w przyszłości: lerp w przestrzeni LAB mógłby dać bardziej
"percepcyjnie naturalne" przejście, ale to już wysoka wartość marginalna.

---

## Code Review — zmiany v5 vs v4 (audyt PM/senior dev)

### ✅ WDROŻONE w v6 (dodane w iteracji po Symbol Mosaic Enhancement)

**v6-1. Faza 1.5 — GUI Layout Fix.** Bug wykryty na screenshocie po 
sesji Symbol Mosaic Enhancement: przycisk RENDER SYMBOL MOSAIC 
wypadł poza viewport zakładki (+250px kontrolek, 900px okno). 
Rozwiązanie: `CTkScrollableFrame` dla zawartości + `btn_run_t` 
pinned przez `grid` na dole zakładki. Analogicznie dla Photo tab 
(future-proof). Wolniejsze stawianie — zakładka w gridzie z row=0 
(scroll) i row=1 (fixed button).

**v6-2. Showcase dla Symbol Mosaic — z 1 mozaiki do 4.** 
Krok 3.2b (nowy): cztery 8K mozaiki demonstrujące różne kombinacje
Font Group × Style Mode:
  - Latin Clean + black_on_white (editorial)
  - CJK + black_on_white (manuscript)
  - Ancient + color_on_black (portfolio killer feature)
  - Symbols & Geometric + white_on_black (abstract poster)

**v6-3. Drugi zoom GIF — z Symbol Mosaic GUI flow.** Krok 3.4 (nowy):
20-sek GIF pokazujący przełączanie checkboxów Font Groups, zmianę 
Style Mode na color_on_black, Palette Size, klik RENDER. 
Sprzedaje Symbol Mosaic jako zaawansowane narzędzie, nie ASCII toy.

**v6-4. Sekcja README "Symbol Mosaic Gallery".** Krok 4.3 (nowy):
tabela HTML 2×2 z czterema mozaikami, detail crops, zoom GIF, 
tabela kontrolek (Font Groups × Style Mode × Palette × Variation × 
Symbol Size). Sekcja ZARAZ PO photo Gallery — pokazuje że 
Symbol Mosaic to równoprawna cecha, nie dodatek.

**v6-5. CHANGELOG dodatki dla Symbol Mosaic.** Sekcja 
"Added — Symbol Mosaic" w release notes dokumentuje wszystkie 
zmiany z sesji enhancement.

**v6-6. FAQ troubleshooting o braku przycisku RENDER.** Zabezpieczenie 
na wypadek gdyby ktoś używał projektu na niższej rozdzielczości.

---

## Code Review — zmiany v5 vs v4 (audyt PM/senior dev)

Poniżej transparentne zestawienie zmian wprowadzonych w v5 w roli profesjonalnego code reviewera / project managera. Nie wszystko co zidentyfikowałem zostało wdrożone — rzeczy poniżej progu ROI zostawiam jako świadomy trade-off.

### ✅ WDROŻONE w v5 (wysokie P1)

**1. Faza 6 w wersji minimalnej (opcja B).** Kroki 6.1–6.4 + 6.6–6.7. Krok 6.5 (pre-publish audit) pominięty ze świadomym uzasadnieniem w samym planie. ~45 min zamiast 1-2h.

**2. Commity git po każdej fazie** — wcześniej były tylko w fazach 1, 2, 4, 5. Teraz też w Fazie 0 (baseline), Fazie 3 (showcase), Fazie 6 (GitNexus) i sformalizowane jako konwencja projektowa w Kroku 0.1.

**3. Email `p.lazowski.1986@gmail.com`** wpisany w trzech miejscach: `.env.example` (Krok 2.5), instrukcja rejestracji Openverse (Krok 2.6), User-Agent Wikimedia fetcher (Krok 2.1).

**4. Minimalny `.gitignore` PRZED pierwszym commitem** (Krok 0.1). To był realny bug v4: `git add .` w Fazie 0 wrzucał potencjalnie `__pycache__/`, `.venv/`, istniejące `smart_index.pkl` do baseline. Pełny `.gitignore` z Kroku 2.5 pojawiał się ZA późno.

**5. Krok 7.0 — artefakty portfolio-grade** które nie powstawały nigdzie wcześniej:
   - `LICENSE` (MIT)
   - `requirements.txt` z pinowanymi wersjami (plan dodawał `imagehash`, `psutil`, `scipy` ale nie aktualizował pliku)
   - `CHANGELOG.md` (v5.0.0 release notes)
   - `CONTRIBUTING.md`
   - `.github/workflows/ci.yml` (lint + import check)
   - Badges w README (Python, License, Platform, CI)
   - Sekcja "Known Limitations" (uczciwość intelektualna — recruiterzy to widzą)

**6. Krok 7.1 — smoke test na czystym venv.** Najczęstszy problem portfolio projektów: "u mnie działa". Klonowanie repo do `%TEMP%`, świeży venv, fresh install, dry run bez kluczy API. Ten krok lapie 80% błędów typu missing import, niepinowana wersja, hardcoded ścieżka.

**7. Krok 7.3 — tagowanie semver (v5.0.0) + GitHub Release.** Plan v4 robił tylko `git push`, bez tagów. Dla repo v5.0 bez tagu `v5.0.0` historia wygląda nieprofesjonalnie.

**8. Krok 7.4 — Rollback plan.** Explicit procedury: soft revert, hard reset, recovery branch, SECURITY: co robić jeśli `.env` wypłynął na GitHub (regeneracja klucza Openverse to MUST, nie "nice to have").

### ⚠️ ZIDENTYFIKOWANE ale NIE wdrożone (świadomy trade-off)

**9. `pre-commit` hook z detect-secrets.** Zapobiega commitowaniu `.env` automatycznie. Nie wdrożone bo: (a) wymaga dodatkowej instalacji `pre-commit`, (b) Krok 7.4 dokumentuje procedurę ratowania nawet bez niego, (c) sam `.gitignore` z Kroku 0.1 blokuje najczęstszy path. **Rozważ przy v5.1**.

**10. `CODE_OF_CONDUCT.md`.** Dla solo projektu bez kontrybutorów jest teatrem. Dodaj gdy projekt zacznie przyciągać external PR-y.

**11. GitHub Issue templates + PR template.** Nie ma sensu bez ruchu na issue tracker. Dodaj reaktywnie — po pierwszym issue od użytkownika.

**12. Automated release workflow (GitHub Actions).** Overkill dla desktop app bez builda/dystrybucji binarek. Jeśli kiedyś będzie PyInstaller → dodaj wtedy.

**13. Dependabot / Renovate.** Sensowne dla projektu z CVE-sensitive deps. Tutaj: `torch`, `Pillow`, `requests` — warte dodania jako `.github/dependabot.yml` w wolnej chwili, ale nie blokuje publikacji.

### 🟢 OBSERWACJE (bez zmian, tylko do wiadomości)

**14. Szacunek pobierania Extended.** Plan mówi "godziny pobierania". Realnie: 30K zdjęć × ~3 sek polite delay + pauzy = ~25-30h ciągłego pobierania, lub 3-4 dni w sesjach po 8h. Dla Kroku 2.7 warto mentalnie przygotować się, że to nie jest "odpal i idź spać".

**15. 16K renderowanie a RAM.** Plan dobrze ostrzega (Krok 1.11 + sanity_check). Na sprzęcie Piotra (32 GB DDR4) zero problemów. Warto pamiętać: jeden recruiter może mieć 8 GB — jeśli spróbuje 16K na swoim laptopie, crash. Stąd Known Limitations w Kroku 7.0.

**16. Deep Zoom Viewer — tylko 2 mozaiki.** To już w planie, ale warto mentalnie: GitHub Pages ma soft limit 1 GB repo, hard limit 10 GB, zalecenie < 1 GB na site. Każda mozaika 16K w DZI tiles ~60-75 MB. 2 mozaiki × 75 MB = 150 MB — w normie, ale 3 mozaiki już zaczynają balansować. Plan jest tu trafnie konserwatywny.

**17. `ai_core.py` legacy.** Plan go nie wspomina explicit. Jeśli zostaje w repo — oznacz w docstringu „LEGACY v3-v4, not used in v5.0, kept for reference". Inaczej recruiter zobaczy MiDaS i się zdziwi, że nie ma w README.

---

**Rekomendowana kolejność wdrażania v6:**

Faza 0 (10 min) → Faza 1 (~4h) → **Faza 1.5 (~20 min — GUI fix)** → 
Faza 2 (~8-12h + pobieranie) → Faza 3 (~4h — photo + symbol showcase) → 
Faza 4 (~3h — dwa GIF-y + Symbol Gallery) → Faza 5 (~5h) → 
Faza 6 (~45 min) → Faza 7 (~3h, w tym smoke test!) → tag + push.

**Realistyczny wall-clock:** 4-6 sesji po 4-6h, rozłożone na 1.5-2 tygodnie. 
NIE jeden weekend. Pobieranie Extended to +2-3 dni w tle.
