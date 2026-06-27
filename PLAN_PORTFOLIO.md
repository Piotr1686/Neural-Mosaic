# PLAN PRAC — Portfolio „wow" + widoczność

> Utworzono: 2026-06-27. Faza po domknięciu A1+A2 (peak-RAM 16K + eksport DZI).
> Teza przewodnia: **na tym etapie rangę projektu podnosi prezentacja i widoczność, nie kolejna runda polerowania kodu.** Kod jest już mocny (173 testy, CI, dwujęzyczne docs, optymalizacja RAM z bit-w-bit golden testami). Brakuje *widoczności i narracji*.
> Zasada kolejności: **najwyższy ROI / najmniejszy wysiłek najpierw.** Każdy krok = osobny commit (conventional commits).

## Kontekst decyzji (z sesji 2026-06-27)

User pytał, czy puścić adwersarialnych agentów w CC dla efektu „wow". **Decyzja: NIE** — dla lokalnej appki desktop CPU-only (brak sieci/auth/danych w chmurze) to teatr o niskiej wartości marginalnej ponad jeden `/code-audit`. Jedyny sensowny wąski wariant: pojedynczy przebieg „atakujący twierdzenia README" przed publikacją (krok 6).
Podział narzędzi: **CC** = artefakty/repo/pomiary; **Claude.ai (web)** = narracja, case study, posty, pozycjonowanie.
Świadomie NIE dokładamy ML/AI (CLIP odrzucony — [[project_no_clip]]). „Wow" leży w: zoomowalnym artefakcie + nowości aperiodycznego monokafelka + prezentacji inżynierskiej.

## Kolejność wykonania

| # | Krok | Co dokładnie | Narzędzie | Wysiłek | ROI | Status |
|---|------|--------------|-----------|---------|-----|--------|
| 1 | **Live zoomable gallery jako HERO** | Wygeneruj 1–2 prawdziwe mozaiki **16K** → DZI (gotowy `make_dzi`/przycisk GUI); wrzuć do hostowanego viewera OpenSeadragon na GitHub Pages (dziś tylko „a handful of 8K" — README l. 560). Na samej górze README (EN+PL), nad badge'ami lub tuż pod hero-obrazem, wielki link „🔍 Open the live zoomable gallery". Reuse istniejącego `mosaic_zoom.gif`. | CC | średni | **najwyższy** | ☐ |
| 2 | **GitHub Social Preview** | Obraz 1280×640 px (min. 640×320) ustawiony w Settings → Social preview. Bohater: portret spectre 16K z fragmentem zoomu pokazującym, że kafelki to zdjęcia + nazwa/tagline. To obraz, który widać przy KAŻDYM linku do repo (LinkedIn, Slack, Discord, X). Tani, wysoka widoczność. Źródło: `spectre_full.jpg` + `spectre_zoom1/2.jpg`. | CC (kompozycja) / web (layout) | niski | wysoki | ☐ |
| 3 | **Sekcja „Performance Engineering"** | Zamień dzisiejszą robotę w narrację: `cdist` float64 → GEMM float32 in-place, peak RAM ~10→3.9 GB, leniwe maski, **bit-w-bit golden sha256** jako dowód braku regresji, `PeakRAMSampler` (stary pomiar gubił spike'i). To dokładnie „zmierzyłem→zdiagnozowałem→zoptymalizowałem→udowodniłem poprawność", którego brak w 95% portfolio. Krótka sekcja w README + ewentualny dłuższy post. | CC (fakty) + web (proza) | niski/średni | wysoki | ☐ |
| 4 | **Post „Photomosaics on an aperiodic monotile"** | Intelektualny wyróżnik: spectre/kite (odkrycie 2023) jako tiling mozaiki — praktycznie żadne inne narzędzie tego nie ma. Krótki write-up + GIF nieregularnej siatki. Materiał blog/HN/r/math. Podnosi z „ładnej appki" do „ktoś zrobił coś, czego nie ma nikt inny". | web (narracja) + CC (obrazy) | średni | wysoki (zasięg) | ☐ |
| 5 | **Zero-friction install (opcjonalne)** | PyInstaller / one-click `.exe` (wersja model-free) obniża próg wejścia. Więcej pracy na Windows, mniej „wow" niż 1–4. | CC | wysoki | średni | ☐ |
| 6 | **Adwersarialny audyt twierdzeń README** | PRZED publikacją: jeden przebieg (`/code-audit` lub subagent `Explore`) — „znajdź każdą liczbę/feature/flagę w README EN+PL, której nie potwierdza kod". Wyłapuje przechwalstwo, martwe linki, nieaktualne flagi. To jedyna sensowna forma „adwersarialności" tutaj. | CC | niski | średni (higiena) | ☐ |

**Rekomendowany start kolejnej sesji: krok 1** (live gallery jako hero) — infrastruktura DZI+Pages już istnieje, jest najbardziej niedoeksploatowana i daje najszybszy efekt „wow" bez instalacji u odbiorcy. Krok 2 (social preview) naturalnie łączy się z pracą wizualną kroku 1.

## Świadomie odłożone
Adwersarialny multi-agent framework (over-engineering dla tego profilu), kolejne modele ML/CLIP, Wariant C z A1/A2 ([[project_a1_memory_arch]], [[project_a2_dzi_export_arch]]), Docker/plugin system.

## Protokół
Po każdym kroku: weryfikacja → propozycja commitu → pytanie „kontynuować?". Aktualizuj kolumnę Status. Assety już dostępne w `assets/examples/`: `spectre_full.jpg`, `spectre_zoom1/2.jpg`, `res_16K.jpg`, `mosaic_zoom.gif`, `mosaic_portrait_*.jpg`, `detail_*.jpg`.
