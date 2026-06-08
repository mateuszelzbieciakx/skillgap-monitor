"""Inicjalizacja schematu bazy danych dla SkillGap Monitor.

Tworzy tabele zgodnie ze schematem PRD. Skrypt jest idempotentny —
można go uruchamiać wielokrotnie bez błędów (CREATE TABLE IF NOT EXISTS).

Rola ai_read_only jest tworzona osobno przez SQL Editor w panelu Supabase,
ponieważ DDL ról bywa blokowane przez Transaction Pooler.

Autor: Mateusz Elżbieciak (indeks: 233651)
"""

import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str | None = os.getenv("DATABASE_URL")

SCHEMA_DDL: str = """
CREATE TABLE IF NOT EXISTS skill_taxonomy (
    id SERIAL PRIMARY KEY,
    raw_name VARCHAR(100) UNIQUE NOT NULL,
    standardized_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    is_tech BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS job_offers (
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

CREATE TABLE IF NOT EXISTS offer_skills (
    offer_id UUID REFERENCES job_offers(id) ON DELETE CASCADE,
    skill_id INTEGER REFERENCES skill_taxonomy(id),
    requirement_type VARCHAR(20) DEFAULT 'must',
    PRIMARY KEY (offer_id, skill_id)
);
"""


def init_database() -> None:
    """Łączy się z bazą i wdraża schemat DDL.

    Raises:
        SystemExit: Gdy brak DATABASE_URL lub połączenie/wykonanie DDL zawiedzie.
    """
    if not DATABASE_URL:
        print("BŁĄD: Brak DATABASE_URL w .env", file=sys.stderr)
        sys.exit(1)

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            cur.execute(SCHEMA_DDL)
        conn.commit()
        print("OK: Schemat bazy danych wdrożony pomyślnie.")

        # Weryfikacja - lista utworzonych tabel
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
                """
            )
            tables = [row[0] for row in cur.fetchall()]
        print(f"Tabele w bazie ({len(tables)}): {', '.join(tables)}")

    except psycopg2.Error as exc:
        print(f"BŁĄD połączenia/wykonania DDL: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    init_database()