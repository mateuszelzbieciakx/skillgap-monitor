# Project Ready Design (PRD) - SkillGap Monitor
**Role for AI:** Jesteś Senior Data Engineerem & Python Developerem. Współpracujesz ze mną (Mateusz), aby zbudować profesjonalny system do analityki rynku pracy IT. 
**Kontekst:** Projekt powstaje w ramach studiów (Informatyka Stosowana, UEK). Wszelka generowana dokumentacja, komentarze i raporty końcowe muszą uwzględniać mój numer indeksu: 233651. Projekt posłuży mi również jako flagowy element portfolio w rekrutacjach na stanowiska Junior Python Developer / DevOps. Kod musi być wzorowy (Clean Code, PEP8, obsługa wyjątków).

## 1. Architektura Systemu i Technologie
*   **Język:** Python 3.11+
*   **Scraping:** Framework `Scrapy` (wyciąganie danych z ukrytych API JSON, nie parsowanie HTML).
*   **Baza Danych:** PostgreSQL (hostowana na platformie Supabase).
*   **Interfejs Użytkownika:** `Streamlit` (Aplikacja B2C).
*   **Sztuczna Inteligencja:** API OpenAI (funkcja BYOK) do modułu Text-to-SQL.
*   **Wdrażanie:** Docelowo architektura Cloud Serverless, obecnie lokalnie z użyciem `.env`.

## 2. Założenia Biznesowe i Logika
1.  **Polite Scraping:** `DOWNLOAD_DELAY = 1.5`, `CONCURRENT_REQUESTS_PER_DOMAIN = 2`. Omijamy zabezpieczenia szukając zapytań Fetch/XHR.
2.  **Soft Delete (Time-to-Fill):** Używamy operacji UPSERT (PostgreSQL: `ON CONFLICT DO UPDATE`). Jeśli ogłoszenie zniknie, po 48h ustalamy `is_active = FALSE`.
3.  **Deduplikacja:** Klucz unikalny: `source_portal` + `external_id`.
4.  **Podział Umów:** Kolumna `contract_type` rozróżnia B2B i UoP.
5.  **Bezpieczeństwo AI:** Mechanizm Text-to-SQL wykonuje kod TYLKO z użyciem roli `ai_read_only`.
6.  **Zimny Start (Słownik):** Wymagany skrypt inicjalizujący (Bootstrap) wypełniający tabelę `skill_taxonomy` startowymi danymi.

## 3. Struktura Danych Źródłowych (Przykład z inżynierii wstecznej)
Dla portalu NoFluffJobs zidentyfikowaliśmy ukryty payload JSON. Pająk Scrapy musi odczytywać następujące pola z odpowiedzi:
`{ "totalCount": 7574, "totalPages": 49, "postings": [ { "id": "...", "name": "...", "salary": { "from": 18000, "to": 25000, "currency": "PLN" }, "company": { "name": "ABC Corp" } } ] }`

## 4. Schemat Bazy Danych
Wdróż ten schemat DDL w Fazie 1:

```sql
CREATE TABLE skill_taxonomy (
    id SERIAL PRIMARY KEY,
    raw_name VARCHAR(100) UNIQUE NOT NULL,
    standardized_name VARCHAR(100) NOT NULL,
    category VARCHAR(50)
);

CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL
);

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
    currency VARCHAR(10) DEFAULT 'PLN',
    experience_level VARCHAR(50),
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    CONSTRAINT uq_source_external UNIQUE (source_portal, external_id)
);

CREATE TABLE offer_skills (
    offer_id UUID REFERENCES job_offers(id) ON DELETE CASCADE,
    skill_id INTEGER REFERENCES skill_taxonomy(id),
    PRIMARY KEY (offer_id, skill_id)
);

-- Role bezpieczeństwa dla AI
CREATE USER ai_read_only WITH PASSWORD 'zmienic_na_produkcji';
GRANT CONNECT ON DATABASE postgres TO ai_read_only;
GRANT USAGE ON SCHEMA public TO ai_read_only;
GRANT SELECT ON job_offers, companies, skill_taxonomy, offer_skills TO ai_read_only;