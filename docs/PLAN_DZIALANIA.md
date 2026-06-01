# PLAN DZIAŁANIA — SkillGap Monitor

**Autor:** Mateusz Elżbieciak (indeks: 233651), UEK
**Horyzont:** ~2 tygodnie | **Cel minimalny:** scraping (2 portale) → czysta baza → analityka w Streamlit

> Ten plan opisuje sekwencję i kamienie milowe. Hierarchiczny podział zadań → `WBS.md`. Specyfikacja techniczna → `PRD_SKILLGAP.md`.

---

## Stan obecny (punkt startu)

Faza fundamentów ukończona: środowisko (`uv` + Python 3.13), baza Supabase z czterema tabelami (`init_db.py` działa), trzy skille Claude Code, zaktualizowana dokumentacja (PRD, CLAUDE.md). Spider jeszcze nienapisany — to następny krok.

---

## Tydzień 1 — Inżynieria danych (scraping + pipeline)

### Dni 1-2: Szkielet Scrapy + spider NoFluff (krok 1)
- Utworzenie projektu Scrapy (`scraper/`), konfiguracja `settings.py` zgodnie z polityką Polite Scraping (DELAY 2.5, AutoThrottle, CONCURRENT 1).
- Definicja wspólnego `JobOfferItem` (pola docelowe niezależne od portalu).
- Pająk NoFluff — krok 1: lista ofert (`POST /api/search/posting`, paginacja, iteracja po technologiach).
- **Kamień milowy:** surowe oferty z 1 strony wypisane do konsoli/JSON.

### Dni 3-4: Spider NoFluff (krok 2) + pipeline zapisu
- Krok 2: pobranie szczegółów każdej oferty (`GET /api/posting/{id}`) → pełne `requirements` (musts + nices).
- `ValidationPipeline`: czyszczenie pól JSON z HTML, ekstrakcja `contract_type` (B2B/UoP) z `salary.type`, normalizacja nazw skilli.
- `PostgresPipeline`: zapis logiką UPSERT (`ON CONFLICT`), wstawianie skilli do `skill_taxonomy`, powiązania w `offer_skills` z `requirement_type`.
- **Kamień milowy:** oferty z 1 strony w bazie, bez duplikatów, ze skillami.

### Dzień 5: Bootstrap + walidacja danych
- `bootstrap_skills.py` — seed słownika `skill_taxonomy` (startowe technologie + kategorie).
- Próbny scrape kilku technologii; sanity-check (liczba rekordów, brak NULL w kluczowych polach, poprawność B2B/UoP).
- **Kamień milowy:** stabilny pipeline, dane gotowe do rozszerzenia.

---

## Tydzień 2 — Drugi portal, analityka, finalizacja

### Dni 6-7: Drugi portal (JustJoin.it)
- Weryfikacja API JustJoin.it w DevTools (endpoint, metoda, format, czy skille w liście czy w detalach).
- Pająk JustJoin mapujący do **wspólnego `JobOfferItem`** (logika specyficzna dla portalu zamknięta w pająku).
- **Kamień milowy:** oferty z dwóch portali w jednej bazie, deduplikacja działa.

### Dni 8-9: Pełny scrape próbki + analityka (silnik)
- Pełny scrape reprezentatywnej próbki (~700-2500 ofert łącznie). Może działać w tle.
- Implementacja trzech miar (zapytania SQL): Salary Explorer (mediana + P25/P75), Skill Premium, Skill Gap/Demand.
- **Kamień milowy:** zapytania analityczne zwracają sensowne wyniki na realnych danych.

### Dni 10-11: Dashboard Streamlit
- Trzy zakładki = trzy statystyki HR. Interaktywne filtry (poziom, miasto, typ umowy). Wizualizacje (wykresy widełkowe, słupkowe).
- Strona tytułowa z indeksem 233651.
- **Kamień milowy:** działający dashboard prezentujący analizę.

### Dni 12-14: Dokumentacja + bufor
- README (setup + uruchamianie), finalizacja Raportu, strona tytułowa.
- Porządek w historii Git (Conventional Commits), własny code review (PEP8, type hints, docstringi).
- Bufor na obsunięcia.
- **Kamień milowy:** projekt gotowy do oddania.

---

## Elementy opcjonalne (jeśli czas pozwoli)

- Trzeci portal (Bulldogjob) — kolejne źródło mapowane do wspólnego Itemu.
- Moduł AI Text-to-SQL (BYOK) na roli `ai_read_only` — zapytania w języku naturalnym.

---

## Zasady robocze (przez cały projekt)

- **Git:** commity w konwencji Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`), regularny `push`.
- **Praca z asystentem:** Claude Code do pisania/edycji kodu (skille pilnują standardów); czat do decyzji architektonicznych i weryfikacji API.
- **Bezpieczeństwo:** `.env` nigdy do repo; brak zahardkodowanych haseł.
