---
name: managing-database
description: Reviews and guides all PostgreSQL/Supabase database code for the SkillGap Monitor project — DDL schema, write logic, and SQL queries. Enforces UPSERT (ON CONFLICT DO UPDATE) instead of plain INSERT, Soft Delete (is_active = FALSE) instead of DELETE, 3NF normalization, indexing of frequently-filtered columns, and the read-only ai_read_only role for any future LLM-generated queries. Use this skill whenever the user writes, reviews, or debugs anything touching the database: schema/DDL, the Postgres write pipeline, init scripts, analytical SQL for the Streamlit dashboard, or psycopg2 connection code — even if they don't explicitly say "database" or "SQL".
---

# Zarządzanie bazą danych (PostgreSQL / Supabase)

Skill nadzoruje bezpieczeństwo, integralność i wydajność warstwy bazodanowej projektu SkillGap Monitor. Baza (PostgreSQL na Supabase) pełni rolę Single Source of Truth. Schemat jest znormalizowany do 3NF.

## Kiedy stosować

- Pisanie lub przegląd DDL (definicje tabel, ograniczenia, role)
- Logika zapisu danych z pipeline'u Scrapy do bazy
- Skrypty inicjalizujące (`init_db.py`, bootstrap słownika)
- Zapytania analityczne pod dashboard Streamlit
- Kod połączenia (`psycopg2`) i obsługa transakcji

## Reguła 1: UPSERT zamiast INSERT (twarda)

Zapis ofert MUSI używać `ON CONFLICT (...) DO UPDATE`. Generowanie zwykłych `INSERT` grozi duplikatami i łamie deduplikację. Klucz konfliktu wynika z ograniczenia unikalności `source_portal + external_id`.

```sql
-- ŹLE — duplikaty przy ponownym scrape
INSERT INTO job_offers (source_portal, external_id, title, ...)
VALUES (%s, %s, %s, ...);

-- DOBRZE — idempotentny zapis, aktualizacja czasu widoczności
INSERT INTO job_offers (source_portal, external_id, title, ..., last_seen_at)
VALUES (%s, %s, %s, ..., CURRENT_TIMESTAMP)
ON CONFLICT (source_portal, external_id)
DO UPDATE SET last_seen_at = CURRENT_TIMESTAMP,
              is_active = TRUE,
              salary_min = EXCLUDED.salary_min,
              salary_max = EXCLUDED.salary_max;
```

## Reguła 2: Soft Delete zamiast DELETE (twarda)

System nigdy nie kasuje ofert fizycznie. Oferta zniknięta z portalu jest oznaczana flagą `is_active = FALSE` (po okresie zdefiniowanym w PRD). Pozwala to później wyliczyć wskaźnik Time-to-Fill. Każde `DELETE FROM job_offers` to błąd — zaproponuj `UPDATE ... SET is_active = FALSE`.

## Reguła 3: Normalizacja 3NF

Pilnuj braku redundancji. Konkretnie w tym schemacie:
- Firmy w osobnej tabeli `companies`, oferta trzyma `company_id` (FK), nie powtórzoną nazwę
- Umiejętności w `skill_taxonomy`, powiązania w tabeli łączącej `offer_skills` (relacja N:M)
- Surowe nazwy skilli mapowane na znormalizowane (`raw_name` → `standardized_name`), by uniknąć duplikatów typu "Postgres"/"PostgreSQL"

Jeśli widzisz powtarzaną nazwę firmy lub skilla wprost w `job_offers` — to naruszenie 3NF.

## Reguła 4: Bezpieczeństwo — rola ai_read_only (dotyczy modułu AI / Future Work)

Moduł Text-to-SQL (planowany jako Future Work) wykonuje zapytania generowane przez LLM. Każde takie zapytanie MUSI iść przez rolę `ai_read_only` z prawami wyłącznie `SELECT` — bez `INSERT/UPDATE/DELETE/DROP`. To bariera przeciw SQL Injection ze strony modelu.

Uwaga: hasło roli pochodzi z `.env` (`AI_READ_ONLY_PASSWORD`), nigdy zahardkodowane w DDL. Rola tworzona jest osobno (przez SQL Editor Supabase), bo Transaction Pooler bywa blokuje DDL ról.

```sql
-- DOBRZE — read-only, hasło z .env (placeholder podstawiany przy wykonaniu)
GRANT SELECT ON skill_taxonomy, companies, job_offers, offer_skills TO ai_read_only;
-- ŹLE — nadanie praw zapisu roli AI
GRANT INSERT, UPDATE ON job_offers TO ai_read_only;
```

Gdy moduł AI nie jest jeszcze implementowany, reguła pozostaje walidacyjna na przyszłość — nie zgłaszaj jej braku jako błędu w kodzie, który AI nie dotyczy.

## Reguła 5: Indeksowanie kolumn filtrowanych

Sugeruj `CREATE INDEX` dla kolumn najczęściej filtrowanych na dashboardzie Streamlit: `experience_level`, `contract_type`, `city`, `is_active`. Indeksy zakładaj świadomie (nie na wszystko), uzasadniając wzorcem zapytań analitycznych.

## Reguła 6: Połączenie i transakcje

- `DATABASE_URL` z `.env`, nigdy w kodzie
- Połączenia zamykane w `finally` lub przez context manager
- Zapisy commitowane jawnie; przy błędzie `rollback`
- Świadomość ograniczeń Transaction Poolera (port 6543) — przy problemach z prepared statements rozważ Session pooler

## Format odpowiedzi przy przeglądzie

Wypisz błędy jako listę punktów ze wskazaniem, jak zagrażają integralności, bezpieczeństwu lub wydajności. Następnie podaj bezpieczny wariant zapytania/kodu.
