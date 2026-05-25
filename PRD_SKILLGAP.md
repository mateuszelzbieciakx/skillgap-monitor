# Project Ready Design (PRD) - SkillGap Monitor
**Autor:** Mateusz Elżbieciak (Indeks: 233651)  
**Role for AI:** Senior Data Engineer & Python Developer. Współpracujesz ze mną, aby zbudować profesjonalny system do analityki rynku pracy IT.  
**Kontekst:** Projekt na zaliczenie UEK (Informatyka Stosowana). Wszelka dokumentacja, komentarze i raporty muszą zawierać indeks 233651. Portfolio-ready, flagowy projekt do rekrutacji (Junior Python Developer / DevOps).

---

## 1. Architektura Systemu i Technologie

- **Język:** Python 3.11+
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

2. **Źródło danych:** NoFluffJobs API
   - Faza 1: `/api/search/posting` — lista ofert (pagination)
   - Faza 2: `/api/posting/{id}` — szczegóły + pełne requirements

3. **Deduplikacja:** `source_portal + external_id` (UNIQUE)

4. **Soft Delete:** Po 48h braku oferty w liscie → `is_active = FALSE` (UPSERT)

5. **Umowy:** `contract_type` (B2B, UoP, ...)

6. **Bezpieczeństwo:**
   - `ai_read_only` role — hasło z `.env` (nie hardkod)
   - SELECT-only, brak INSERT/UPDATE

7. **Bootstrap:** Skrypt `init_skill_taxonomy.py` wypełnia `skill_taxonomy` startowymi danymi

---

## 3. Schemat Bazy Danych (Zaktualizowany)

```sql
-- Taksonomia umiejętności
CREATE TABLE skill_taxonomy (
    id SERIAL PRIMARY KEY,
    raw_name VARCHAR(100) UNIQUE NOT NULL,
    standardized_name VARCHAR(100) NOT NULL,
    category VARCHAR(50)
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

### Faza 1: Środowisko + Baza Danych (Dzień 1)
- [ ] `uv init` + `pyproject.toml`
- [ ] `.env` z `DATABASE_URL`
- [ ] `init_db.py` — wdraża schema (idempotentny)
- [ ] Test: schema załadowany, tabele puste

### Faza 2: Spider (Dni 2-3)
- [ ] Scrapy project structure
- [ ] `NoFluffJobsSpider` — dwustopniowy:
  - Krok 1: `/api/search/posting` — iteracja po stronach
  - Krok 2: `/api/posting/{id}` — szczegóły każdej oferty
- [ ] `JobOfferItem` + `RequirementItem`
- [ ] Test: 1 strona (20 ofert) załadowana do konsoli

### Faza 3: Pipelines (Dni 3-4)
- [ ] `ValidationPipeline` — czyszczenie i normalizacja:
  - Ekstraktowanie `contract_type` z `salary.type`
  - Normalizacja nazw skilli (lowercase, trim)
  - Walidacja pól wymaganych
- [ ] `PostgresPipeline` — zapis do bazy:
  - UPSERT do `job_offers` (ON CONFLICT)
  - Wstawianie skilli do `skill_taxonomy` (idempotentny insert)
  - Łączenie w `offer_skills` z `requirement_type`
- [ ] Test: 1 strona w bazie bez duplikatów

### Faza 4: Pełny Scrape + Bootstrap (Dzień 5)
- [ ] `init_skill_taxonomy.py` — seed danych (Python, Django, React, ...)
- [ ] Pełny scrape: wszystkie strony (może być overnight)
- [ ] Sanity check: liczba rekordów, brak NULL w kluczowych polach

### Faza 5: Streamlit + Analityka (Dni 5-6)
- [ ] 3 główne statystyki (HR-friendly):
  1. **Salary Explorer** — mediana + P25/P75 × level × contract type
  2. **Skill Premium** — ranking skilli wg wpływu na medianę pensji
  3. **Skill Gap / Demand** — ranking skilli per poziom doświadczenia
- [ ] Interaktywne filtry (poziom, miasto, typ umowy)
- [ ] Strona tytułowa z indeksem 233651

### Faza 6: Dokumentacja + Bufor (Dzień 7)
- [ ] README.md (instrukcja setup + uruchamiania)
- [ ] Strona tytułowa (PDF lub markdown) — indeks, imię, nazwisko
- [ ] Conventional Commits w Git
- [ ] Code review własny (PEP8, type hints, docstrings)

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

## 6. Dane z NoFluffJobs API

### Endpoint 1: Lista ofert
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

### Endpoint 2: Szczegóły oferty
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

---

## 7. Metryki na zaliczenie

✅ **Scraping:** 500+ ofert z NoFluff  
✅ **Baza:** Czysta, bez duplikatów, z umiejętnościami  
✅ **Analityka:** 3 wiarygodne statystyki (HR-ready)  
✅ **UI:** Streamlit z filtrami i wizualizacją  
✅ **Kod:** Clean Code, dokumentacja, indeks 233651  
✅ **Git:** Historia commitów, proper messages  

---

## 8. Future Work (Po zaliczeniu)

- [ ] Integracja z justjoin.it, pracuj.pl (multi-portal)
- [ ] Text-to-SQL AI module (BYOK OpenAI)
- [ ] Deployment na Vercel/Railway
- [ ] Docker containerization
- [ ] Scheduled scraping (cron/APScheduler)
- [ ] Redis caching dla analityki

---

**Status:** Ready for execution (Dzień 1 start)