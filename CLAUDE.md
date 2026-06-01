# CLAUDE.md — SkillGap Monitor

> Instrukcja dla asystenta kodowego (Claude Code). Konstytucja projektu: zasady, których trzymamy się przy każdej zmianie.
> **Źródła prawdy:** szczegółowa specyfikacja → `PRD_SKILLGAP.md`; standardy kodu → `.claude/skills/`; dokładny schemat bazy → `init_db.py`; bieżący stan → `STATUS.md` (HANDOFF). W razie sprzeczności obowiązuje PRD.

## Kontekst projektu

Projekt akademicki: Mateusz Elżbieciak (indeks: 233651), Informatyka Stosowana, Uniwersytet Ekonomiczny w Krakowie (UEK). Służy też jako flagowy element portfolio (Junior Python Developer / DevOps).

Cel: automatyczne pozyskiwanie ofert pracy IT z wielu portali, wyliczanie median wynagrodzeń i identyfikacja luk kompetencyjnych (Skill Gap). Wartość biznesowa: statystyki rynkowe użyteczne dla HR (benchmark płac, "skill premium", popyt na umiejętności).

**Termin:** ~2 tygodnie. **Cel minimalny:** działający scraping (min. 2 portale) → czysta baza → analityka w Streamlit.

## Stos technologiczny

- **Python:** 3.13 (menedżer: `uv`, plik `pyproject.toml`)
- **Scraping:** Scrapy — pobieranie z ukrytych API JSON (Fetch/XHR), nie parsowanie HTML
- **Baza danych:** PostgreSQL na Supabase (Transaction Pooler, port 6543, IPv4)
- **Frontend:** Streamlit (dashboard analityczny)
- **AI (Text-to-SQL):** **Future Work** — NIE implementowane w tej fazie. Rola `ai_read_only` przygotowana pod przyszłość.
- **Zmienne środowiskowe:** `.env` (nigdy nie commitować)

## Zasady pisania kodu

- Zgodność z **PEP8**, **type hints** dla wszystkich funkcji i metod.
- Nazwy w kodzie: angielskie, `snake_case` / `PascalCase`. Dokumentacja opisowa: polski.
- Obsługa wyjątków obowiązkowa — nigdy gołego `except:`.
- Docstringi **Google Style** (`Args`, `Returns`, `Raises`).
- Każdy nowy plik główny zaczyna się nagłówkiem:

```python
# Projekt: SkillGap Monitor
# Autor: Mateusz Elżbieciak (Indeks: 233651)
# Uczelnia: Uniwersytet Ekonomiczny w Krakowie (UEK)
```

- Gdyby gdziekolwiek pojawiła się nazwa "Piotr Henzolt" (relikt starych dokumentów) — zamień na "Mateusz Elżbieciak".

### Zależności
- Zawsze `uv` — **nigdy** `pip install` ani `requirements.txt`.
- Dodawanie paczki: `uv add <pakiet>`; uruchamianie: `uv run <skrypt>`.

## Zasady scrapingu (Scrapy)

- **Polite Scraping (bezwzględne):** `DOWNLOAD_DELAY = 2.5` (źródło: PRD — podwyższone ze względu na dwustopniowy spider), `AUTOTHROTTLE_ENABLED = True`, `CONCURRENT_REQUESTS_PER_DOMAIN = 1`. Realny `User-Agent`.
- **Dwustopniowy spider:** krok 1 = lista ofert (POST, paginacja); krok 2 = szczegóły każdej oferty (GET po `id`) → pełne `requirements` (musts + nices).
- **Scraping per-technologia:** portale (NoFluff) są multi-branżowe i nie mają filtra "całe IT". Oś scrapowania = lista konkretnych technologii (Python, Java, JS, TS, C#, Go, Rust, Kotlin, Scala, C++, React, Angular, PyTorch, Spark). Deduplikacja w bazie czyści nakładki.
- **Multi-portal:** osobny pająk per portal (`spiders/`), każdy mapuje do **wspólnego `JobOfferItem`**. Pole `source_portal` zawsze ustawione.
- **Streaming do bazy:** `yield item` → pipeline na bieżąco. Zakaz gromadzenia tysięcy ofert w liście w RAM.
- **Czyszczenie HTML tylko dla pól JSON, które bywają HTML** (np. `description`, `requirements.description`) — przez Item Processor / pipeline walidujący. NIE parsujemy DOM (dane są w JSON).
- Szczegóły API (endpointy, body, format odpowiedzi) → PRD sekcja 6.

## Zasady bazy danych (PostgreSQL / Supabase)

**Schemat (DDL) jest w `init_db.py` i PRD sekcja 3 — to źródło prawdy. Tu tylko reguły operacyjne.** Cztery tabele: `skill_taxonomy`, `companies`, `job_offers` (z `salary_period`), `offer_skills` (z `requirement_type`).

- **UPSERT obowiązkowy:** zapis ofert wyłącznie przez `ON CONFLICT (source_portal, external_id) DO UPDATE`. Zakaz zwykłego `INSERT` bez obsługi konfliktu.
- **Soft Delete:** nigdy `DELETE` na ofertach. Po okresie nieaktywności: `UPDATE job_offers SET is_active = FALSE`.
- **Deduplikacja:** klucz `(source_portal, external_id)`.
- **Separacja kontraktów:** `contract_type` oddziela B2B od UoP — zapobiega przekłamaniom statystyk (B2B netto vs UoP brutto).
- **3NF:** firmy w `companies`, technologie w `skill_taxonomy`, powiązania w `offer_skills`. Bez redundancji.
- **Normalizacja skilli:** surowe nazwy → `standardized_name` (unikać duplikatów "Postgres"/"PostgreSQL").
- **Indeksy:** `CREATE INDEX` na kolumnach filtrowanych w Streamlit (`city`, `experience_level`, `is_active`, `contract_type`).
- **Rola `ai_read_only`:** hasło z `.env` (`AI_READ_ONLY_PASSWORD`), NIE hardkod. Tworzona OSOBNO w SQL Editorze Supabase (Transaction Pooler blokuje DDL ról). Uprawnienia: tylko `SELECT`.
- **Połączenie:** `DATABASE_URL` z `.env`; połączenia zamykane w `finally`; commit jawny, przy błędzie `rollback`.

## Bezpieczeństwo modułu AI (Future Work)

Gdy moduł Text-to-SQL będzie implementowany: zapytania LLM **wyłącznie** przez `ai_read_only` (brak INSERT/UPDATE/DELETE), parametryzowane (zakaz f-stringów z danymi użytkownika). Dopóki moduł nie istnieje — nie traktować jego braku jako błędu.

## Struktura katalogów

Stan obecny: `init_db.py` w katalogu głównym, `.claude/skills/` gotowe. Docelowo (projekt Scrapy do utworzenia):

```
skillgap_scraper/
├── scraper/
│   ├── spiders/          # Pająki Scrapy (jeden plik = jeden portal)
│   ├── items.py          # Wspólny JobOfferItem
│   ├── pipelines.py      # ValidationPipeline, PostgresPipeline
│   └── settings.py       # Polite Scraping
├── scripts/
│   ├── init_db.py        # DDL (obecnie w katalogu głównym — do przeniesienia)
│   └── bootstrap_skills.py  # Zimny start: seed skill_taxonomy
├── app/
│   └── main.py           # Streamlit
├── .claude/skills/       # Skille Claude Code (gotowe)
├── .env                  # NIE commitować
├── pyproject.toml
├── PRD_SKILLGAP.md
└── CLAUDE.md
```

## Fazy projektu (zwięźle — pełny WBS w WBS.md)

| Faza | Zakres | Status |
|------|--------|--------|
| 1 | Środowisko (uv, 3.13) + baza Supabase (DDL, `.env`) | ✅ gotowe |
| 2 | Scrapy: dwustopniowy spider NoFluff, wspólny `JobOfferItem`, Polite Scraping | ▢ następne |
| 3 | Pipelines: Validation (czyszczenie, normalizacja, B2B/UoP) + Postgres (UPSERT) | ▢ |
| 4 | Drugi portal (JustJoin.it) — mapowanie do wspólnego Itemu | ▢ |
| 5 | Bootstrap `skill_taxonomy` + pełny scrape próbki (~700-2500 ofert) | ▢ |
| 6 | Streamlit: 3 statystyki HR (Salary Explorer, Skill Premium, Skill Gap) + filtry | ▢ |
| 7 | Dokumentacja, README, raport (indeks 233651), Conventional Commits | ▢ |

(Trzeci portal Bulldogjob i moduł AI Text-to-SQL = opcjonalne / Future Work.)

## Czego NIE robić

- Nie commituj `.env`, kluczy API, haseł.
- Nie używaj `pip` ani `requirements.txt`.
- Nie parsuj HTML/DOM — szukaj ukrytych endpointów JSON (Fetch/XHR w DevTools).
- Nie używaj `DELETE` na ofertach — tylko Soft Delete.
- Nie obniżaj `DOWNLOAD_DELAY` poniżej wartości z PRD.
- Nie nadawaj roli `ai_read_only` praw zapisu.
- Nie gromadź dużych zbiorów w RAM — strumieniuj do PostgreSQL.
- Nie odpalaj `git clean` bez `-e .env` (chroni przed skasowaniem `.env`).
