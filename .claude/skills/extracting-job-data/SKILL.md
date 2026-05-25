---
name: extracting-job-data
description: Reviews and guides Scrapy spider code that extracts job offers from hidden JSON APIs (NoFluffJobs, JustJoin.it, and other portals) for the SkillGap Monitor project. Enforces polite scraping policy, correct request construction for POST/JSON-API endpoints, multi-portal mapping to a shared item, memory-safe streaming to the database, and cleaning of JSON-embedded HTML fields. Use this skill whenever the user writes, reviews, debugs, or extends any Scrapy spider, settings.py, Item, or scraping-related code in this project — even if they don't explicitly mention "scraping" or "Scrapy".
---

# Ekstrakcja danych o ofertach pracy (Scrapy)

Skill nadzoruje jakość i bezpieczeństwo kodu ekstrahującego dane z ukrytych API JSON portali pracy w projekcie SkillGap Monitor. Architektura projektu opiera się na pobieraniu **czystego JSON z ukrytych endpointów API**, a nie na parsowaniu HTML/DOM. To fundamentalne założenie — wszystkie reguły poniżej z niego wynikają.

## Kiedy stosować

- Pisanie lub przegląd dowolnego pająka Scrapy (`*_spider.py`)
- Zmiany w `settings.py` dotyczące polityki pobierania
- Definicja lub modyfikacja klasy `JobOfferItem` / loaderów
- Dodawanie obsługi kolejnego portalu (multi-portal)
- Debugowanie blokad (403, 429) lub niekompletnych danych

## Reguła 1: Polite Scraping (twarda, nienegocjowalna)

Żaden pająk nie ma prawa działać bez opóźnień między żądaniami. **Konkretna wartość `DOWNLOAD_DELAY` i pozostałych parametrów jest zdefiniowana w PRD projektu (`PRD_SKILLGAP.md`, sekcja Założenia Biznesowe) — to jest jedyne źródło prawdy.** Nie zaszywaj liczb w wielu miejscach; przy przeglądzie sprawdzaj zgodność `settings.py` z PRD, a nie z liczbą zapamiętaną w tym skillu.

Wymagane w `settings.py`:
- `DOWNLOAD_DELAY` zgodny z wartością z PRD (obecnie projekt używa podwyższonego opóźnienia ze względu na dwustopniowy spider: lista + szczegóły każdej oferty)
- `AUTOTHROTTLE_ENABLED = True`
- `CONCURRENT_REQUESTS_PER_DOMAIN` zgodny z PRD (niski, by nie obciążać serwera)
- `ROBOTSTXT_OBEY` — świadoma, udokumentowana decyzja (nie zostawiaj domyślnej bez komentarza)

Jeśli kod łamie tę politykę — odrzuć go stanowczo i zaproponuj wersję bezpieczną dla serwerów docelowych.

```python
# ŹLE — agresywne, brak throttlingu, ryzyko blokady IP
DOWNLOAD_DELAY = 0
CONCURRENT_REQUESTS_PER_DOMAIN = 16

# DOBRZE — wartości pobrane z polityki PRD, throttling włączony
DOWNLOAD_DELAY = 2.5          # zgodnie z PRD (dwustopniowy spider)
AUTOTHROTTLE_ENABLED = True
CONCURRENT_REQUESTS_PER_DOMAIN = 1
```

## Reguła 2: Poprawne żądania do API JSON (nie HTML)

Endpointy portali to API JSON, często **POST z ciałem JSON** i niestandardowymi nagłówkami (np. NoFluff: `Content-Type: application/infiniteSearch+json`). Przy przeglądzie sprawdzaj:

- Czy żądanie używa właściwej metody (POST vs GET) zweryfikowanej empirycznie w DevTools, a nie założonej
- Czy `body` jest serializowany przez `json.dumps(...)`, a payload zbudowany jako słownik Pythona
- Czy nagłówki niestandardowe (Content-Type, kontekst sesji) są przekazane
- Czy paginacja iteruje po polach z odpowiedzi (`totalPages`/`pageTo`), a nie po zgadywanych liczbach
- Czy odpowiedź czytana jest przez `response.json()`, nie przez selektory CSS/XPath

```python
# DOBRZE — POST z payloadem JSON, czytanie response.json()
payload = {"criteriaSearch": {"requirement": [tech]}, "pageSize": 20}
yield scrapy.Request(
    url=API_URL,
    method="POST",
    body=json.dumps(payload),
    headers={"Content-Type": "application/infiniteSearch+json"},
    callback=self.parse_listing,
)
```

Jeśli widzisz `response.css(...)` / `response.xpath(...)` na danych, które są dostępne jako JSON — to regres architektoniczny. Zasygnalizuj i przekieruj na API.

## Reguła 3: Wiele portali, jeden wspólny Item

Projekt scrapuje co najmniej dwa portale (NoFluffJobs, JustJoin.it). Każdy ma inny format JSON i inne nazewnictwo pól. Architektura wymaga:

- **Jednego wspólnego `JobOfferItem`** jako docelowego formatu
- Osobnego pająka per portal, który **mapuje** swój format do wspólnego Itemu
- Logiki specyficznej dla portalu (np. interpretacja `salary.type`) zamkniętej w pająku/loaderze tego portalu, nie rozlanej po pipeline

Przy przeglądzie pilnuj, by pole `source_portal` było zawsze ustawiane (klucz deduplikacji `source_portal + external_id`).

## Reguła 4: Streaming do bazy, nie gromadzenie w RAM

Ostrzegaj, jeśli pająk lub pipeline gromadzi tysiące ofert w liście w pamięci przed zapisem. Dane mają płynąć przez `yield item` do pipeline'u zapisu na bieżąco. Listy akumulujące cały scrape to antywzorzec pamięciowy przy ~tysiącach ofert.

## Reguła 5: Czyszczenie pól JSON zawierających HTML

Większość danych przychodzi jako czysty JSON, ale **niektóre pola tekstowe (np. `description`, `requirements.description`) bywają fragmentami HTML** (`\u003cp\u003e...`). To je trzeba czyścić — nie cały dokument, bo nie parsujemy DOM. Czyszczenie rób w warstwie walidacji (Item Processor / pipeline walidujący):

- Usuwanie znaczników HTML z konkretnych pól tekstowych (np. `w3lib.html.remove_tags`)
- Dekodowanie encji (`\u003c` → `<`) i normalizacja białych znaków
- Walidacja pól wymaganych (tytuł, external_id, source_portal) przed przekazaniem dalej

Nie stosuj reguł "usuń HTML z całej odpowiedzi" — to relikt parsowania stron, nieadekwatny do API JSON.

## Format odpowiedzi przy przeglądzie

Po analizie wypisz znalezione problemy jako listę punktów (z odniesieniem do reguły), a następnie podaj poprawiony fragment kodu z type hints i docstringami w stylu Google (zgodnie ze skillem dokumentacyjnym projektu).
