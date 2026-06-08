# PLAN DZIAŁANIA — SkillGap Monitor

**Autor:** Mateusz Elżbieciak (indeks: 233651), UEK
**Horyzont:** ~2 tygodnie | **Cel minimalny:** scraping (2 portale) → czysta baza → analityka w Streamlit

> Ten dokument opisuje sekwencję i kamienie milowe projektu. Hierarchiczny podział zadań → `WBS.md`. Specyfikacja techniczna → `PRD_SKILLGAP.md`.

---

## Stan końcowy (2026-06-08) — projekt ukończony ✅

Wszystkie fazy główne zrealizowane. Działający system end-to-end: dwa spidery Scrapy pobierają oferty z NoFluffJobs i JustJoin.it → ValidationPipeline czyści i waliduje dane → PostgresPipeline zapisuje przez UPSERT do Supabase → Streamlit Dashboard prezentuje trzy analizy HR.

---

## Tydzień 1 — Inżynieria danych (scraping + pipeline) ✅

### Dni 1-2: Szkielet Scrapy + spider NoFluff (krok 1) ✅
- Projekt Scrapy (`scraper/scraper/`), `settings.py` z Polite Scraping (DELAY 2.5, AutoThrottle, CONCURRENT 1).
- Wspólny `JobOfferItem` niezależny od portalu.
- Spider NoFluff krok 1: lista ofert (POST `/api/search/posting`, paginacja, 25 technologii).
- **Kamień milowy:** ✅ oferty z 1 strony w bazie.

### Dni 3-4: Spider NoFluff (krok 2) + pipeline zapisu ✅
- Krok 2: szczegóły każdej oferty (`GET /api/posting/{id}`) → pełne `requirements` (musts + nices).
- `ValidationPipeline`: czyszczenie HTML, normalizacja `contract_type`/`experience_level`, scentralizowana walidacja salary (`_validate_salary`) z progami rynkowymi per `contract_type`.
- `PostgresPipeline`: UPSERT do `job_offers`, UPSERT `skill_taxonomy`, INSERT `offer_skills` z `requirement_type`.
- **Kamień milowy:** ✅ oferty w bazie bez duplikatów, salary wyzerowane dla outlierów.

### Dzień 5: Walidacja danych ✅
- Próbny scrape kilku technologii; sanity-check (liczba rekordów, brak NULL w kluczowych polach).
- **Uwaga:** `bootstrap_skills.py` (seed `skill_taxonomy`) — niezaimplementowany, pozostaje Future Work.
- **Kamień milowy:** ✅ stabilny pipeline, dane gotowe do pełnego scrape'u.

---

## Tydzień 2 — Drugi portal, analityka, finalizacja ✅

### Dni 6-7: Drugi portal (JustJoin.it) ✅
- Reverse engineering API w DevTools: GET `/api/candidate-api/offers`, paginacja offsetowa.
- Spider jednokrokowy — wszystkie dane oferty w jednej odpowiedzi (brak kroku szczegółów).
- Mapowanie `employmentTypes` do `JobOfferItem` z priorytetem b2b > permanent > mandate_contract.
- Spider jako czysty maper: walidacja salary wyłącznie w `ValidationPipeline`, nie w spiderze.
- 4 migracje SQL czyszczące dane historyczne po pełnym scrape'ie (001–004).
- **Kamień milowy:** ✅ oferty z dwóch portali w jednej bazie, deduplikacja działa.

### Dni 8-9: Pełny scrape + analityka (silnik) ✅
- Pełny scrape: JustJoin.it 10 000 ofert + NoFluff 10 stron × 25 technologii (~10 000+ rekordów łącznie).
- Implementacja trzech zapytań SQL: Salary Explorer (mediana + P25/P75), Skill Premium (within-level), Skill Gap (must/nice per poziom).
- **Kamień milowy:** ✅ zapytania analityczne zwracają sensowne wyniki na realnych danych.

### Dni 10-11: Dashboard Streamlit ✅
- Trzy zakładki analityczne HR. Globalne filtry sidebar (portal, poziom, typ umowy).
- Dark theme inspirowany Apple; Plotly custom template dla spójności wizualnej.
- Skill Premium tooltip z komentarzem dla ujemnych wartości (korelacja z rolami junior/QA/support).
- Autor i indeks 233651 w ekspanderze sidebar.
- **Kamień milowy:** ✅ działający dashboard z trzema analizami.

### Dni 12-14: Dokumentacja ✅
- README.md portfolio-ready (architektura ASCII, badges, 6-krokowy setup).
- PRD_SKILLGAP.md i CLAUDE.md zaktualizowane do stanu rzeczywistego.
- WBS.md zaktualizowany (wszystkie zadania oznaczone jako ukończone).
- Conventional Commits w historii Git, push do GitHub.
- **Kamień milowy:** ✅ projekt gotowy do oddania.

---

## Co wyszło ponad plan

- **Scentralizowana walidacja salary** w `ValidationPipeline._validate_salary` — spidery są czystymi maperami, cała logika walidacyjna w jednym miejscu.
- **4 migracje SQL** — konieczne po pełnym scrape'ie do oczyszczenia danych historycznych (salary bugs, normalizacja skill_taxonomy, flaga is_tech).
- **Skill Premium within-level** — metoda kontrolująca poziom doświadczenia jako zmienną zakłócającą (planowano prostszy ranking).
- **NoFluff rozszerzony do 25 technologii** — pierwotnie mniejsza lista.

## Elementy niezrealizowane

- `bootstrap_skills.py` — seed startowy `skill_taxonomy` (Future Work).
- Trzeci portal Bulldogjob (opcjonalne).
- Moduł AI Text-to-SQL (Future Work).

---

## Zasady robocze (zastosowane przez cały projekt)

- **Git:** Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`), regularny `push` do GitHub.
- **Praca z asystentem:** Claude Code do pisania/edycji kodu (skille pilnują standardów PEP8, type hints, docstrings).
- **Bezpieczeństwo:** `.env` nigdy do repo; brak zahardkodowanych haseł; rola `ai_read_only` tylko SELECT.
