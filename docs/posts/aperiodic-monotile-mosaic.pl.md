# Fotomozaiki na aperiodycznym monokafelku

[English](aperiodic-monotile-mosaic.md) · **Polski**

> Niemal każda fotomozaika w historii leży na kwadratowej siatce. [Neural-Mosaic](https://github.com/Piotr1686/Neural-Mosaic) potrafi ułożyć ją na **spectre** — chiralnym aperiodycznym monokafelku odkrytym w 2023 — pojedynczym kształcie, który pokrywa płaszczyznę i *nigdy się nie powtarza*.

![Kafelkowanie spectre, kafle pokolorowane wg orientacji](img/aperiodic_grid.png)
*Jeden kształt kafelka, każda orientacja, brak powtarzalnej siatki. Kolor koduje tu obrót każdego kafla.*

## Kształt

W 2023 czteroosobowy zespół — David Smith, Joseph Myers, Craig Kaplan i Chaim Goodman-Strauss — rozwiązał problem otwarty od lat 60.: czy istnieje *pojedynczy* kafelek pokrywający płaszczyznę wyłącznie **aperiodycznie**, bez powtarzalnej jednostki? Pierwsza odpowiedź, **„hat"** ([arXiv:2303.10798](https://arxiv.org/abs/2303.10798)), była „einsteinem" (niem. *ein Stein*, „jeden kamień"), ale wymagała kopii odbitych lustrzanie. Kilka tygodni później ten sam zespół opublikował **„spectre"** ([arXiv:2305.17743](https://arxiv.org/abs/2305.17743)): 14-bok, który jest *ściśle chiralny* — kafelkuje aperiodycznie używając tylko obrotów i przesunięć jednej skrętności, bez odbić lustrzanych. Prawdziwy jednokafelkowy einstein.

![Pojedynczy kafelek spectre — 14 wierzchołków](img/spectre_tile.png)
*Spectre: 14 krawędzi równej długości. Neural-Mosaic używa wyłącznie spectre (hat, wymagający odbić, został usunięty).*

## Po co kłaść na nim mozaikę

Kwadratowa siatka narzuca okresowy rytm. Oko zaczepia się o wiersze i kolumny, a z dystansu sama krata staje się teksturą konkurującą z obrazem. Kafelkowanie aperiodyczne ma mnóstwo struktury *lokalnej*, ale **żadnego globalnego powtórzenia**, więc siatka nigdy nie układa się we własny wzór — czyta się organicznie. Dodaj czarną fugę, a geometria staje się czytelna: podejdź bliżej, a każda nieregularna komórka okazuje się osobną fotografią.

To także po prostu prawdziwy obiekt matematyczny z przełomowego wyniku — nie filtr. Na tym polega różnica między „ładną appką" a „czymś, co robi to, czego nie robi nikt inny".

![Stopniowe odsłanianie kafelkowania](img/aperiodic_grid.gif)
*Kafelkowanie rośnie od środka na zewnątrz. Zauważ brak symetrii translacyjnej — żadne przesunięcie nie nakłada wzoru na samego siebie.*

## Jak się renderuje

Geometria żyje w [`src/spectre_tiling.py`](https://github.com/Piotr1686/Neural-Mosaic/blob/main/src/spectre_tiling.py). `generate_spectre_tiling(width, height, tile_size)` produkuje **dokładne** chiralne kafelkowanie spectre przez opublikowany system podstawień:

- **Deterministyczne** — identyczne argumenty dają identyczne kafelkowanie.
- **Niezależne od rozdzielczości** — pokrywa dowolny prostokąt; pole każdego spectre ≈ `tile_size²`, więc render spectre ma z grubsza tyle samo kafli co render kwadratowy przy tym samym ustawieniu (uczciwe porównanie).
- **Ściśle chiralne** — każde umieszczenie ma jedną skrętność; kafle brzegowe wystają i są przycinane przez wywołującego.

Każdy 14-bok staje się następnie *gniazdem* kafla, wypełnianym tą samą maszynerią co silnik kwadratowy: dopasowanie koloru 5×5 LAB do biblioteki plus kara antypowtórzeniowa, by żadne zdjęcie nie dominowało. Wydajne renderowanie każdej nieprostokątnej komórki to osobny problem — maski przechowywane są jako wielokąty i rasteryzowane leniwie przy kompozycie (`_LazyMask`), z 4× supersamplingiem i LANCZOS dla czystych krawędzi, przypięte złotymi testami bit-w-bit. Ta robota jest opisana w sekcji [Performance Engineering](https://github.com/Piotr1686/Neural-Mosaic#performance).

## Zobacz / wypróbuj

- **Na żywo, z zoomem:** [interaktywna galeria](https://piotr1686.github.io/Neural-Mosaic/) hostuje pełną mozaikę spectre **16K** — przybliż od całego portretu aż do jednego zdjęcia w pojedynczej nieregularnej komórce.
- **Wyrenderuj własną:**
  ```bash
  python -m src.cli render input/portrait.jpg --engine smart --shape spectre --res 16K
  ```

---

*Odkrycie kafelkowania: Smith, Myers, Kaplan i Goodman-Strauss, „A chiral aperiodic monotile" (2023), [arXiv:2305.17743](https://arxiv.org/abs/2305.17743). Implementacja i obrazy: [Neural-Mosaic](https://github.com/Piotr1686/Neural-Mosaic).*
