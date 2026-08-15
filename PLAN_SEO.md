# PLAN_SEO.md — widoczność Neural-Mosaic w wyszukiwarkach

**Utworzony:** 2026-08-15
**Diagnoza wyjściowa:** zapytanie `"Neural-Mosaic" Piotr1686 github photomosaic` nie zwraca
repozytorium. Repo publiczne od 2026-05-01, 1 gwiazdka, dobry opis i 10 topiców.

**Podział pracy:** punkty ✅ są zrobione w repo. Punkty 🔑 wymagają Twojego konta
(Google, Reddit, HN) — są rozpisane co do kliknięcia, ale **nikt ich za Ciebie nie
wykonał i nic nie zostało nigdzie opublikowane**.

---

## Dlaczego repo nie wychodzi (w kolejności wagi)

1. **Zero linków przychodzących.** Google odkrywa i priorytetyzuje strony przez linki.
   Repo bez backlinków i z 1 gwiazdką ma najniższy priorytet crawlowania. To ~80%
   problemu — żaden meta-tag tego nie zastąpi.
2. **Strona Pages nie miała czego zaindeksować.** `index.html` był aplikacją
   OpenSeadragon: jeden `<h1>`, reszta rysowana w canvasie przez JS.
3. **`docs/posts/*.md` były osierocone** — nic do nich nie linkowało, a przez `.nojekyll`
   serwowane były jako surowy markdown, nie HTML.
4. **Brak sitemapy i zgłoszenia w Search Console.**
5. **Kolizja nazwy** — „neural mosaic" to fraza generyczna; konkurencja to prace naukowe
   i inne projekty photomosaic.

---

## ✅ Zrobione w repo (2026-08-15)

- **`docs/index.html` przebudowany na stronę lądowania** z realną treścią do
  zaindeksowania: czym to jest, jak działa dopasowanie CIELAB, 50 kafelkowań (pełna
  lista), silnik typograficzny, instrukcja uruchomienia. Pełny head: `description`,
  `canonical`, OpenGraph + Twitter card, JSON-LD `SoftwareApplication`.
- **Przeglądarka OpenSeadragon przeniesiona do `docs/viewer.html`** (zachowana 1:1,
  plus przycisk „Home" i własne meta). Linki w README EN+PL przestawione na
  `/viewer.html`.
- **`docs/style.css`** — wspólny arkusz dla strony i wpisów, bez zewnętrznych fontów.
- **`docs/img/`** — `og-cover.jpg` (1200×630), `hero.jpg` i 5 przykładów, przeskalowane
  i skompresowane (razem ~1,2 MB zamiast ~7 MB oryginałów).
- **Wpisy jako HTML:** `docs/posts/aperiodic-monotile-mosaic.html` + `.pl.html` —
  z `hreflang` en/pl/x-default, canonical, OG i JSON-LD `BlogPosting`. Pliki `.md`
  zostają (README linkuje do nich, GitHub ładnie je renderuje).
- **`docs/sitemap.xml`** — 4 URL-e z `lastmod` i alternatywami językowymi.
- **README EN+PL:** tabela kształtów wymieniała 9 pozycji przy rejestrze 50 — zastąpiona
  sekcją „Tile shapes" / „Kształty kafelków" z podziałem na 5 rodzin (12 krat + 15
  klasycznych teselacji + 6 aperiodycznych + 6 fraktalnych + 11 promienistych = 50).
- **Weryfikacja:** 0 złamanych odnośników lokalnych, wszystkie 4 URL-e z sitemapy
  istnieją, strona sprawdzona wizualnie w Chrome (landing, wpis, przeglądarka).

### ⚠ Ograniczenie, o którym trzeba wiedzieć

`docs/robots.txt` leży pod `/Neural-Mosaic/robots.txt`, a roboty czytają **wyłącznie**
`https://piotr1686.github.io/robots.txt` (należący do repo user-site `piotr1686.github.io`,
jeśli takie istnieje). Ten plik dokumentuje intencję, ale **nie jest egzekwowany**.
Nic na tym nie tracimy: domyślnie i tak wszystko jest dozwolone, a sitemapę zgłasza się
bezpośrednio w Search Console.

---

## 🔑 Punkt 1 — Google Search Console, krok po kroku

### Czym to jest (i czym nie jest)

Search Console to darmowe narzędzie Google dla właścicieli stron. Robi dwie rzeczy:
**mówi Google, że strona istnieje** (i pozwala poprosić o jej odwiedzenie), oraz
**pokazuje raporty** — na jakie zapytania strona się wyświetla i ile ma kliknięć.

Czego **nie** robi: nie podnosi pozycji w wynikach. Zgłoszenie strony to nie to samo
co bycie wysoko — to tylko wejście do indeksu. Pozycję buduje punkt 4 (backlinki).

Cała zabawa zajmuje ~15 minut, z czego połowa to czekanie.

---

### Krok 1 — wejście

Otwórz <https://search.google.com/search-console> i zaloguj się swoim kontem Google
(to samo, co Gmail). Konta się nie zakłada osobno — Search Console działa na koncie
Google, które już masz.

Za pierwszym razem zobaczysz ekran powitalny z prośbą o dodanie „usługi" (*property*).
„Usługa" w żargonie Google = jedna strona, którą chcesz obserwować.

### Krok 2 — dodanie usługi (uwaga: właściwy typ)

Zobaczysz dwa kafelki do wyboru:

| Kafelek | Wybrać? |
|---|---|
| **Domena** | ❌ **NIE.** Wymaga wpisu w DNS domeny. Domena `github.io` należy do GitHuba, nie do Ciebie — nie masz jak tego zrobić. |
| **Prefiks adresu URL** | ✅ **TAK.** |

W polu pod „Prefiks adresu URL" wpisz dokładnie, **z ukośnikiem na końcu**:

```
https://piotr1686.github.io/Neural-Mosaic/
```

Ukośnik ma znaczenie: bez niego Google potraktuje to jako inny adres i raporty będą
puste. Kliknij **Dalej**.

### Krok 3 — weryfikacja (udowodnienie, że strona jest Twoja)

Google pokaże listę metod. **Wybierz „Tag HTML"** — jest najprostsza w naszym
przypadku, bo pliki strony i tak mam pod ręką.

Po rozwinięciu tej opcji zobaczysz linijkę mniej więcej taką:

```html
<meta name="google-site-verification" content="AbCdEf123456_przykladowy-ciag" />
```

**Skopiuj ją w całości i wklej mi w czacie.** Ja:
1. wstawię ją do `docs/index.html` (musi być na stronie głównej usługi),
2. zrobię commit i push,
3. powiem Ci, kiedy GitHub Pages skończy przebudowę (~1-2 minuty).

Dopiero wtedy wróć do Search Console i kliknij **Zweryfikuj**. Jeśli klikniesz za
wcześnie, dostaniesz błąd „nie znaleziono tagu" — to nie awaria, po prostu poczekaj
minutę i kliknij ponownie.

> **Nie zamykaj karty Search Console** między krokami. Jeśli ją zamkniesz, tag zostaje
> ważny — wracasz przez **Ustawienia → Weryfikacja własności** i klikasz Zweryfikuj.

<details>
<summary>Alternatywa: metoda „Plik HTML" (jeśli wolisz zrobić wszystko sam)</summary>

Google da Ci do pobrania plik o nazwie w rodzaju `google1a2b3c4d5e6f.html`.
Skopiuj go do katalogu `docs/` w repo, potem:

```bash
git add docs/google*.html
git commit -m "chore(seo): plik weryfikacyjny Google Search Console"
git push
```

Poczekaj 1-2 minuty i sprawdź w przeglądarce, czy plik otwiera się pod
`https://piotr1686.github.io/Neural-Mosaic/google1a2b3c4d5e6f.html`. Jeśli widzisz
jego treść — klikaj Zweryfikuj. Jeśli 404 — Pages jeszcze się nie przebudowało.

**Nigdy nie usuwaj tego pliku ani tagu po weryfikacji** — Google sprawdza je okresowo
i przy braku odbiera dostęp do usługi.
</details>

### Krok 4 — zgłoszenie mapy witryny

Po udanej weryfikacji jesteś w panelu usługi. W menu po lewej znajdź
**„Mapy witryn"** (*Sitemaps*).

Zobaczysz pole „Dodaj nową mapę witryny", a przed nim wyszarzony, niezmienialny
prefiks `https://piotr1686.github.io/Neural-Mosaic/`. W pole wpisujesz **tylko końcówkę**:

```
sitemap.xml
```

Kliknij **Prześlij**. Poniżej pojawi się wiersz ze statusem. Docelowo ma być
**„Powodzenie"** i „Wykryte adresy URL: 4". Jeśli przez chwilę widzisz „Nie udało się
pobrać" — odśwież po kilku minutach; Google czasem sprawdza mapę z opóźnieniem.

### Krok 5 — poproszenie o odwiedziny (najważniejszy krok)

Na samej górze panelu jest pasek wyszukiwania z podpowiedzią
**„Sprawdź dowolny URL w usłudze…"**. To narzędzie „Sprawdzanie adresu URL".

Wklej tam pierwszy adres i naciśnij Enter:

```
https://piotr1686.github.io/Neural-Mosaic/
```

Google przez ~30 sekund pokaże „Pobieranie danych z indeksu Google", a potem werdykt.
Na starcie będzie to **„Adres URL nie jest w Google"** — i to jest normalne, po to tu
jesteś. Kliknij **„Poproś o zindeksowanie"**. Google zrobi krótki test na żywo
(1-2 minuty) i potwierdzi: „Adres URL dodany do kolejki priorytetowego indeksowania".

Powtórz dokładnie to samo dla pozostałych trzech adresów:

```
https://piotr1686.github.io/Neural-Mosaic/viewer.html
https://piotr1686.github.io/Neural-Mosaic/posts/aperiodic-monotile-mosaic.html
https://piotr1686.github.io/Neural-Mosaic/posts/aperiodic-monotile-mosaic.pl.html
```

Limit to około 10 takich próśb dziennie — cztery zmieścisz bez problemu.
**Nie zgłaszaj tego samego adresu wielokrotnie** — nie przyspiesza, a bywa traktowane
jako nadużycie.

---

### Czego się spodziewać (żeby nie panikować)

- **Pierwsze 2-3 dni:** w raportach pustka. Search Console pokazuje dane z opóźnieniem
  i dopiero od momentu weryfikacji — historii wstecz nie dostaniesz.
- **Status „Wykryto — obecnie nie zindeksowano"** przy którymś adresie to nie błąd.
  Znaczy: Google wie o stronie, ale jeszcze nie uznał jej za wartą miejsca w indeksie.
  Lekarstwem są linki przychodzące (punkt 4), nie kolejne zgłoszenia.
- **Po ~2 tygodniach:** wejdź w **„Skuteczność"** (*Performance*). Jeśli są jakiekolwiek
  wyświetlenia — jesteś w indeksie i działa.
- **Po ~6 tygodniach:** w „Skuteczność" → zakładka **Zapytania** zobaczysz, na jakie
  frazy ludzie Cię widzą. Realistycznie najpierw pojawią się długie, konkretne frazy
  (`spectre monotile photomosaic`), nie samo `photomosaic`.

### Czego NIE da się zrobić

Strony `github.com/Piotr1686/Neural-Mosaic` **nie zgłosisz** — nie jesteś właścicielem
domeny github.com, więc nie przejdziesz weryfikacji. Repo wejdzie do wyników Google
wyłącznie przez linki przychodzące. To jest dokładnie to, po co jest punkt 4.

---

## 🔑 Punkt 4 — backlinki (to, co realnie rusza ranking)

Poniżej gotowe teksty do wklejenia. **Nic z tego nie zostało opublikowane** — publikacja
pod Twoim nazwiskiem to Twoja decyzja. Kolejność ma znaczenie: zacznij od jednego kanału,
zobacz odzew, potem kolejny (równoległy zalew wygląda jak spam).

### A. Hacker News — „Show HN"

> **Tytuł:** Show HN: Neural-Mosaic – photomosaics on the spectre aperiodic monotile
>
> **URL:** https://piotr1686.github.io/Neural-Mosaic/
>
> **Pierwszy komentarz (wklej zaraz po opublikowaniu):**
>
> Author here. This started as a plain photomosaic tool and turned into a study of tilings.
> The cell geometry is a first-class setting: 50 tilings, including Penrose P2/P3,
> Ammann–Beenker, girih, and the spectre — the chiral aperiodic monotile published in 2023.
> Every tiling partitions the frame exactly and is pinned by pixel-exact golden tests, so
> renders are reproducible.
>
> Matching is deliberately not neural despite the name: each library image is reduced to a
> 5×5 grid of CIELAB means (75 dims), and a cell is a nearest-neighbour query over a k-d
> tree. A 5×5 fingerprint rather than one average colour is what keeps edges inside a cell
> from flattening out. I tried CLIP-style semantic matching and dropped it — for colour
> fidelity it was strictly worse.
>
> The interesting engineering was 16K output on a laptop: lazy polygon-to-raster masks and
> a single float32 GEMM for the distance matrix took peak RAM from ~10 GB to under 4 GB.
> There is a zoomable 133 MP render in the browser if you want to see tiles resolve into
> individual photographs.
>
> Happy to talk about the tiling implementations — the aperiodic ones were by far the
> hardest to get gap-free.

*Wskazówka: publikuj w dzień roboczy, 8:00–10:00 czasu wschodniego USA (14:00–16:00
w Polsce). Nie proś nigdzie o głosy — HN to wykrywa i karze.*

### B. Reddit — r/generative

> **Tytuł:** I built a photomosaic engine with 50 tilings — including the spectre aperiodic monotile
>
> **Treść:**
>
> Almost every photomosaic sits on a square grid, and at a distance that lattice becomes a
> texture competing with the picture. So I made the tiling a first-class setting: 50 of them,
> from ordinary lattices through Cairo pentagonal and Penrose to the spectre — the single
> 14-sided tile from the 2023 aperiodic monotile result, which covers the plane and never
> repeats.
>
> Output goes up to 16K (133 MP) and there is a browser viewer where you can zoom until each
> irregular cell resolves into a separate photograph.
>
> Python, MIT-licensed, runs on a laptop: https://github.com/Piotr1686/Neural-Mosaic
>
> Gallery and write-up: https://piotr1686.github.io/Neural-Mosaic/

### C. Reddit — r/Python (inny akcent: inżynieria, nie sztuka)

> **Tytuł:** Neural-Mosaic: 16K photomosaics in pure Python — how I got peak RAM from 10 GB to under 4
>
> **Treść:**
>
> A 16K photomosaic is ~133 MP and hundreds of thousands of tile placements, which naive code
> turns into a swap-thrashing mess. Two changes did most of the work: storing cell masks as
> polygons and rasterising them lazily at composite time instead of materialising a PIL mask
> per cell up front, and replacing the pairwise distance loop with one float32 matrix product.
> Peak RAM went from ~10 GB to under 4 GB with a bit-for-bit identical render — which is
> pinned by golden SHA-256 tests, so the invariant is actually enforced rather than hoped for.
>
> Tile matching is a 75-dim CIELAB fingerprint (5×5 grid of colour means) queried through a
> k-d tree. Stack is numpy/scipy/Pillow/CustomTkinter; 567 tests.
>
> https://github.com/Piotr1686/Neural-Mosaic

### D. dev.to / Medium — przedruk wpisu o monokafelku

Wpis `docs/posts/aperiodic-monotile-mosaic.html` jest gotowym artykułem. Przedrukuj go
z **linkiem kanonicznym** do wersji na Twojej stronie (dev.to ma pole „Canonical URL" —
bez tego przedruk konkuruje z oryginałem w wynikach):
`https://piotr1686.github.io/Neural-Mosaic/posts/aperiodic-monotile-mosaic.html`
Tagi: `python`, `generativeart`, `mathematics`, `showdev`.

### E. Pozostałe kanały (tanie, warte zrobienia)

- **r/proceduralgeneration** — jak r/generative, ale akcent na system podstawień.
- **Profil GitHub** — dodaj repo jako przypięte (pinned) i wspomnij w README profilu.
- **Listy „awesome"** — PR do `awesome-generative-art`, `awesome-python` (sekcja obrazy).
- **Hugging Face Space** — demo online byłoby silnym linkiem, ale wymaga przycięcia
  biblioteki kafli do rozmiaru, który wejdzie w darmowy Space. Osobny projekt.

---

## Czego się spodziewać

- **Dni:** po zgłoszeniu w GSC strona lądowania i wpisy wchodzą do indeksu.
- **2-8 tygodni:** zapytanie o dokładną nazwę („Neural-Mosaic photomosaic") zaczyna
  zwracać repo/stronę, o ile pojawi się choć kilka realnych linków.
- **Długi ogon** — realistycznie najłatwiejsze do wygrania frazy to nie „photomosaic"
  (silna konkurencja), tylko `spectre monotile photomosaic`, `aperiodic tiling mosaic
  generator`, `16K photomosaic python`. Cała treść strony jest pod nie napisana.

**Jak mierzyć:** GSC → Wyniki wyszukiwania → wyświetlenia/kliknięcia per zapytanie.
Sprawdzaj po 2 i po 6 tygodniach; wcześniej dane są zbyt rzadkie, żeby cokolwiek znaczyły.
