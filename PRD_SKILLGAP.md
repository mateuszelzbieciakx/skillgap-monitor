# Project Ready Design (PRD) - SkillGap Monitor
**Autor:** Mateusz Elżbieciak (Indeks: 233651)  
**Role for AI:** Senior Data Engineer & Python Developer. Współpracujesz ze mną, aby zbudować profesjonalny system do analityki rynku pracy IT.  
**Kontekst:** Projekt na zaliczenie UEK (Informatyka Stosowana). Wszelka dokumentacja, komentarze i raporty muszą zawierać indeks 233651. Portfolio-ready, flagowy projekt do rekrutacji (Junior Python Developer / DevOps).

---

## 1. Architektura Systemu i Technologie

- **Język:** Python 3.13
- **Dependency Management:** `uv` (nie pip)
- **Scraping:** Scrapy (JSON API, nie HTML parsing)
- **Baza Danych:** PostgreSQL (Supabase)
- **UI:** Streamlit (aplikacja B2C)
- **Deployment:** Lokalnie z `.env`, docelowo Cloud Serverless
- **AI Module:** Odłożone (Future Work)

---

## 2. Założenia Biznesowe

1. **Polite Scraping:**
   - `DOWNLOAD_DELAY = 2.5s` (ze względu na dwustopniowy spider)
   - `CONCURRENT_REQUESTS_PER_DOMAIN = 1`
   - User-Agent: realny (Mozilla/5.0)

2. **Źródła danych:** dwa portale

   **NoFluffJobs** (spider dwustopniowy):
   - Krok 1: POST `/api/search/posting` — lista ofert per technologia (paginacja)
   - Krok 2: GET `/api/posting/{id}` — szczegóły + pełne requirements
   - Scraping per-technologia (25 tech) — portal multi-branżowy, brak filtra "całe IT"

   **JustJoin.it** (spider jednokrokowy):
   - GET `/api/candidate-api/offers?from={offset}&itemsCount=100` — paginacja offsetowa
   - Wszystkie dane oferty w jednej odpowiedzi, brak kroku szczegółów

3. **Deduplikacja:** `source_portal + external_id` (UNIQUE)

4. **Soft Delete:** Po 48h braku oferty w liscie → `is_active = FALSE` (UPSERT)

5. **Umowy:** `contract_type` (B2B, UoP, ...)

6. **Bezpieczeństwo:**
   - `ai_read_only` role — hasło z `.env` (nie hardkod)
   - SELECT-only, brak INSERT/UPDATE

7. **Bootstrap:** Skrypt `bootstrap_skills.py` wypełnia `skill_taxonomy` startowymi danymi (Future Work — skrypt jeszcze nie istnieje)

---

## 3. Schemat Bazy Danych (Zaktualizowany)

```sql
-- Taksonomia umiejętności
CREATE TABLE skill_taxonomy (
    id SERIAL PRIMARY KEY,
    raw_name VARCHAR(100) UNIQUE NOT NULL,
    standardized_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    is_tech BOOLEAN DEFAULT TRUE  -- filtr technologiczny w zapytaniach Streamlit
);

-- Firmy
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL
);

-- Ogłoszenia pracy
CREATE TABLE job_offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_portal VARCHAR(50) NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    company_id INTEGER REFERENCES companies(id),
    contract_type VARCHAR(20) NOT NULL,
    is_remote BOOLEAN DEFAULT FALSE,
    city VARCHAR(100),
    salary_min INTEGER,
    salary_max INTEGER,
    salary_period VARCHAR(20) DEFAULT 'month',
    currency VARCHAR(10) DEFAULT 'PLN',
    experience_level VARCHAR(50),
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT uq_source_external UNIQUE (source_portal, external_id)
);

-- Umiejętności w ofertach (with requirement type)
CREATE TABLE offer_skills (
    offer_id UUID REFERENCES job_offers(id) ON DELETE CASCADE,
    skill_id INTEGER REFERENCES skill_taxonomy(id),
    requirement_type VARCHAR(20) DEFAULT 'must',
    PRIMARY KEY (offer_id, skill_id)
);

-- Role bezpieczeństwa (hasło z .env)
CREATE USER ai_read_only WITH PASSWORD 'PLACEHOLDER_FROM_ENV';
GRANT CONNECT ON DATABASE postgres TO ai_read_only;
GRANT USAGE ON SCHEMA public TO ai_read_only;
GRANT SELECT ON skill_taxonomy, companies, job_offers, offer_skills TO ai_read_only;
```

---

## 4. Fazy Realizacji

### Faza 1: Środowisko + Baza Danych ✅
- [x] `uv init` + `pyproject.toml`
- [x] `.env` z `DATABASE_URL`
- [x] `init_db.py` — wdraża schema (idempotentny, w katalogu głównym)
- [x] Test: schema załadowany, tabele puste

### Faza 2: Spider NoFluffJobs ✅
- [x] Scrapy project structure (`scraper/scraper/`)
- [x] `NoFluffJobsSpider` — dwustopniowy, 25 technologii, 10 stron/tech:
  - Krok 1: POST `/api/search/posting` — iteracja po stronach per technologia
  - Krok 2: GET `/api/posting/{id}` — szczegóły każdej oferty
- [x] Wspólny `JobOfferItem` dla wszystkich portali
- [x] Test: dane w bazie bez duplikatów

### Faza 3: Pipelines ✅
- [x] `ValidationPipeline` — czyszczenie i normalizacja:
  - Normalizacja `experience_level` (junior/mid/senior/lead) i `contract_type` (b2b/uop/uod/other)
  - Usuwanie tagów HTML z pól tekstowych
  - Scentralizowana walidacja salary (`_validate_salary`): progi rynkowe per `contract_type`
    (B2B min 6 000 PLN/mies., hourly 20–500 PLN), obsługa odwróconych widełek,
    passthrough nieobsługiwanych `salary_period` do wyzerowania
  - Odrzucenie (DropItem) tylko przy braku `external_id` lub `source_portal`
- [x] `PostgresPipeline` — zapis do bazy:
  - UPSERT do `job_offers` (ON CONFLICT `source_portal, external_id`)
  - UPSERT do `skill_taxonomy`, INSERT `offer_skills` z `requirement_type`
- [x] Test: baza bez duplikatów, salary wyzerowane dla outlierów

### Faza 4: Drugi portal (JustJoin.it) ✅
- [x] `JustJoinSpider` — jednokrokowy GET, paginacja offsetowa, do 10 000 ofert
- [x] Mapowanie `employmentTypes` → wspólny `JobOfferItem` (priorytet: b2b > permanent > mandate_contract)
- [x] Spider jako czysty maper — walidacja salary wyłącznie w `ValidationPipeline`
- [x] 4 migracje SQL czyszczące dane historyczne:
  - `001` normalizacja `standardized_name` w `skill_taxonomy`
  - `002` dodanie flagi `is_tech`
  - `003` czyszczenie salary bugs JustJoin
  - `004` globalne czyszczenie salary outlierów

### Faza 5: Pełny Scrape + Bootstrap ✅
- [x] Pełny scrape: JustJoin 10 000 ofert + NoFluff 10 stron × 25 technologii
- [x] Sanity check: liczba rekordów, brak NULL w kluczowych polach
- [ ] `bootstrap_skills.py` — seed `skill_taxonomy` (Future Work — skrypt niezaimplementowany)

### Faza 6: Streamlit + Analityka ✅
- [x] 3 zakładki analityczne (HR-friendly):
  1. **Salary Explorer** — mediana + P25/P75 × level × contract type (tylko `salary_period='month'`)
  2. **Skill Premium** — metoda within-level: mediana odchyleń ofert ze skillem od mediany poziomu;
     kontroluje experience_level jako zmienną zakłócającą
  3. **Skill Gap** — ranking top 15 skilli per poziom: must-have vs nice-to-have
- [x] Globalne filtry sidebar: portal, poziom doświadczenia, typ umowy
- [x] Dark theme inspirowany Apple, Plotly custom template

### Faza 7: Dokumentacja ✅
- [x] `README.md` — portfolio-ready (architektura, setup, badges)
- [x] `docs/RAPORT.md` — raport zaliczeniowy (indeks 233651)
- [x] Conventional Commits w Git
- [x] PEP8, type hints, Google-style docstrings

---

## 5. Engineering Standards

- **Dependency Management:** `uv` (pyproject.toml, nie requirements.txt)
- **Code Style:** PEP8, Type Hints, Google-style docstrings
- **Error Handling:** Try-except na wszystkich I/O (DB, network)
- **Logging:** structlog lub print() z timestamp (nie silent failures)
- **Testing:** Unit testy dla pipeline'ów (co najmniej, by pokazać że działa)
- **Git:** Conventional Commits (`feat:`, `fix:`, `refactor:`)
- **Secrets:** `.env` + `python-dotenv`, nigdy hardkod

---

## 6. Dane z API portali

### NoFluffJobs — Endpoint 1: Lista ofert
```
POST /api/search/posting?pageFrom=1&pageTo=1&pageSize=20&...
Content-Type: application/infiniteSearch+json
Body: { "criteriaSearch": {...}, "pageSize": 20, ... }

Response:
{
  "postings": [
    {
      "id": "...",
      "name": "Company Name",
      "title": "Job Title",
      "seniority": ["Mid"],
      "salary": { "from": 18000, "to": 25000, "type": "b2b", "currency": "PLN" },
      "location": { "fullyRemote": true, "places": [...] },
      "tiles": {
        "values": [
          { "value": "Python", "type": "requirement" },
          { "value": "FastAPI", "type": "requirement" }
        ]
      }
    }
  ],
  "totalCount": 6853,
  "totalPages": 45
}
```

### NoFluffJobs — Endpoint 2: Szczegóły oferty
```
GET /api/posting/{id}

Response:
{
  "id": "...",
  "company": { "name": "..." },
  "title": "...",
  "basics": { "seniority": ["Mid"], "category": "backend" },
  "salary": { "type": "b2b", "range": [18000, 25000], ... },
  "location": { "fullyRemote": true, ... },
  "requirements": {
    "musts": [
      { "value": "Python", "type": "main" },
      { "value": "FastAPI", "type": "main" }
    ],
    "nices": [
      { "value": "Cloud", "type": "main" }
    ]
  }
}
```

### JustJoin.it — Endpoint: Lista ofert
```
GET /api/candidate-api/offers?from={offset}&itemsCount=100&sortBy=publishedAt&orderBy=descending
Accept: application/json

Response:
{
  "data": [
    {
      "guid": "...",
      "slug": "...",
      "title": "Job Title",
      "companyName": "Company",
      "experienceLevel": "mid",
      "workplaceType": "remote",
      "city": "Kraków",
      "employmentTypes": [
        {
          "type": "b2b",
          "currency": "PLN",
          "currencySource": "original",
          "unit": "month",
          "from": 18000,
          "to": 25000
        }
      ],
      "requiredSkills": [{ "name": "Python" }],
      "niceToHaveSkills": [{ "name": "FastAPI" }]
    }
  ],
  "meta": { "next": { "cursor": 100 } }
}
```

---

## 7. Metryki na zaliczenie

✅ **Scraping:** 10 000+ ofert z JustJoin.it + NoFluffJobs (2 portale)  
✅ **Baza:** Czysta, bez duplikatów, z umiejętnościami, 4 migracje SQL  
✅ **Analityka:** 3 zakładki HR-ready (Salary Explorer, Skill Premium within-level, Skill Gap)  
✅ **UI:** Streamlit z filtrami, dark theme, Plotly  
✅ **Kod:** Clean Code, PEP8, type hints, Google docstrings, indeks 233651  
✅ **Git:** Historia commitów, Conventional Commits  

---

## 8. Future Work (Po zaliczeniu)

- [x] ~~Integracja z justjoin.it~~ — zaimplementowane
- [ ] Trzeci portal: Bulldogjob
- [ ] `bootstrap_skills.py` — seed startowy `skill_taxonomy`
- [ ] Text-to-SQL AI module (BYOK) — zapytania przez rolę `ai_read_only`
- [ ] Scheduled scraping (GitHub Actions cron lub AWS EventBridge)
- [ ] Wdrożenie chmurowe (AWS EC2 + RDS lub Railway)
- [ ] Docker containerization
- [ ] Testy jednostkowe `ValidationPipeline._validate_salary` (pytest)

---

**Status:** Zrealizowany (2026-06-08). Wszystkie fazy główne ukończone.