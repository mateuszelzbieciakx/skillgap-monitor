# Projekt: SkillGap Monitor
# Autor: Mateusz Elżbieciak (Indeks: 233651)
# Uczelnia: Uniwersytet Ekonomiczny w Krakowie (UEK)

"""Pipelines dla scrapera SkillGap Monitor.

ValidationPipeline (priority 100) — czyści i waliduje dane przed zapisem.
PostgresPipeline (priority 200) — zapisuje oferty do bazy przez UPSERT.
"""

import logging
import os
import re
from typing import Any

import psycopg2
from dotenv import load_dotenv
from scrapy.exceptions import DropItem

from scraper.items import JobOfferItem

load_dotenv()

# Progi walidacji wynagrodzeń (PLN, rynek IT Polska 2026)
# Dolny próg miesięczny zależny od typu umowy — B2B nie schodzi tak nisko jak UoD/UoP
SALARY_MONTH_MIN: dict[str, float] = {
    "b2b": 6000.0,
    "uop": 3000.0,
    "uod": 3000.0,
    "other": 3000.0,
}
SALARY_MONTH_MAX: float = 150000.0   # górny sufit miesięczny
SALARY_HOUR_MIN: float = 20.0        # min stawka godzinowa
SALARY_HOUR_MAX: float = 500.0       # max realna stawka godzinowa; powyżej = błędny unit


class ValidationPipeline:
    """Waliduje i normalizuje dane JobOfferItem przed zapisem do bazy.

    Priority: 100 (wykonywany jako pierwszy).

    Operacje:
    - Usuwa tagi HTML z pól tekstowych (title, company_name).
    - Normalizuje experience_level do: junior/mid/senior/lead (default: mid).
    - Normalizuje contract_type do: b2b/uop/uod/other.
    - Odrzuca item jeśli brak external_id lub source_portal.
    - Salary opcjonalne — brak salary_min/max nie powoduje odrzucenia.
    """

    # Mapowanie dozwolonych wartości
    VALID_EXPERIENCE_LEVELS = {'junior', 'mid', 'senior', 'lead'}
    VALID_CONTRACT_TYPES = {'b2b', 'uop', 'uod', 'other'}

    # Regex usuwający tagi HTML
    HTML_TAG_PATTERN = re.compile(r'<[^>]+>')

    def __init__(self) -> None:
        """Inicjalizuje logger."""
        self.logger = logging.getLogger(__name__)

    def process_item(self, item: JobOfferItem) -> JobOfferItem:
        """Waliduje i normalizuje item.

        Args:
            item: Oferta pracy do walidacji.

        Returns:
            Zwalidowany i znormalizowany item.

        Raises:
            DropItem: Gdy brak wymaganych pól (external_id, source_portal).
        """
        # Wymagane pola
        if not item.get('external_id'):
            raise DropItem(f"Brak external_id w {item}")
        if not item.get('source_portal'):
            raise DropItem(f"Brak source_portal w {item}")

        # Czyszczenie HTML z pól tekstowych
        item['title'] = self._strip_html(item.get('title', ''))
        item['company_name'] = self._strip_html(item.get('company_name', ''))

        # Normalizacja experience_level
        exp_level = item.get('experience_level', '').lower()
        if exp_level not in self.VALID_EXPERIENCE_LEVELS:
            self.logger.warning(
                f"Nieznany experience_level='{exp_level}' w {item['external_id']}, "
                f"ustawiam 'mid'"
            )
            item['experience_level'] = 'mid'
        else:
            item['experience_level'] = exp_level

        # Normalizacja contract_type
        contract = item.get('contract_type', '').lower()
        if contract not in self.VALID_CONTRACT_TYPES:
            self.logger.warning(
                f"Nieznany contract_type='{contract}' w {item['external_id']}, "
                f"ustawiam 'other'"
            )
            item['contract_type'] = 'other'
        else:
            item['contract_type'] = contract

        self._validate_salary(item)
        return item

    def _validate_salary(self, item: JobOfferItem) -> None:
        """Waliduje i czyści pola salary w item in-place.

        Obsługuje brak widełek, odwrócone widełki, nierealne wartości
        oraz nieobsługiwane okresy rozliczeniowe. Wyzerowanie salary
        nie powoduje odrzucenia oferty (DropItem).

        Args:
            item: Oferta pracy z polami salary_min, salary_max,
                  salary_period i contract_type (już znormalizowanym).
        """
        salary_min: float | None = item.get('salary_min')
        salary_max: float | None = item.get('salary_max')
        period: str = item.get('salary_period', '')
        contract_type: str = item.get('contract_type', 'other')
        ext_id: str = item.get('external_id', '?')

        # Krok 2: brak obu wartości → widełki nieznane, nic nie rób
        if salary_min is None and salary_max is None:
            return

        # Krok 3: tylko jedna wartość → traktuj jako punkt, nie przedział
        if salary_min is None:
            salary_min = salary_max
        elif salary_max is None:
            salary_max = salary_min

        def _zero_out(reason: str) -> None:
            item['salary_min'] = None
            item['salary_max'] = None
            self.logger.warning(
                f"[salary] {ext_id}: wyzerowano ({reason}) "
                f"[min={salary_min}, max={salary_max}, period={period}]"
            )

        # Krok 4a: wartości ujemne lub zerowe
        if salary_min <= 0 or salary_max <= 0:
            _zero_out("wartość <= 0")
            return

        # Krok 4b: nieobsługiwany okres rozliczeniowy
        if period not in ('monthly', 'hourly'):
            _zero_out(f"nieobsługiwany period='{period}'")
            return

        # Krok 5: odwrócone widełki — zamień miejscami
        if salary_min > salary_max:
            salary_min, salary_max = salary_max, salary_min

        # Krok 6: walidacja zakresu przez midpoint
        midpoint: float = (salary_min + salary_max) / 2

        if period == 'monthly':
            lower_bound = SALARY_MONTH_MIN.get(contract_type, 3000.0)
            if midpoint < lower_bound or midpoint > SALARY_MONTH_MAX:
                _zero_out(
                    f"midpoint={midpoint:.0f} poza zakresem "
                    f"[{lower_bound:.0f}, {SALARY_MONTH_MAX:.0f}] monthly/{contract_type}"
                )
                return
        elif period == 'hourly':
            if midpoint < SALARY_HOUR_MIN or midpoint > SALARY_HOUR_MAX:
                _zero_out(
                    f"midpoint={midpoint:.1f} poza zakresem "
                    f"[{SALARY_HOUR_MIN}, {SALARY_HOUR_MAX}] hourly"
                )
                return

        # Zapisz ewentualnie skorygowane widełki (np. po zamianie lub uzupełnieniu)
        item['salary_min'] = salary_min
        item['salary_max'] = salary_max

    def _strip_html(self, text: str) -> str:
        """Usuwa tagi HTML z tekstu.

        Args:
            text: Tekst do oczyszczenia.

        Returns:
            Tekst bez tagów HTML.
        """
        if not text:
            return ''
        return self.HTML_TAG_PATTERN.sub('', text).strip()


class PostgresPipeline:
    """Zapisuje oferty pracy do PostgreSQL przez UPSERT.

    Priority: 200 (wykonywany po ValidationPipeline).

    Operacje:
    - UPSERT companies po name → company_id.
    - UPSERT job_offers po (source_portal, external_id) → offer_id.
    - UPSERT skill_taxonomy po raw_name → skill_id.
    - INSERT offer_skills z ON CONFLICT DO NOTHING.
    - Commit po każdym itemie, rollback przy błędzie.
    """

    def __init__(self) -> None:
        """Inicjalizuje połączenie jako None (nawiązywane w open_spider)."""
        self.conn: psycopg2.extensions.connection | None = None
        self.logger = logging.getLogger(__name__)

    def open_spider(self) -> None:
        """Otwiera połączenie z bazą danych na początku scrape'u.

        Raises:
            RuntimeError: Gdy brak DATABASE_URL w .env.
        """
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise RuntimeError("Brak DATABASE_URL w .env")

        self.conn = psycopg2.connect(database_url)
        self.logger.info("Połączenie z bazą PostgreSQL nawiązane")

    def close_spider(self) -> None:
        """Zamyka połączenie z bazą danych po zakończeniu scrape'u."""
        if self.conn is not None:
            self.conn.close()
            self.logger.info("Połączenie z bazą PostgreSQL zamknięte")

    def process_item(self, item: JobOfferItem) -> JobOfferItem:
        """Zapisuje item do bazy danych przez UPSERT.

        Args:
            item: Oferta pracy do zapisania.

        Returns:
            Item po zapisaniu do bazy.

        Raises:
            DropItem: Gdy zapis do bazy zawiedzie.
        """
        try:
            cur = self.conn.cursor()

            # 1. UPSERT companies → company_id
            company_id = self._upsert_company(cur, item['company_name'])

            # 2. UPSERT job_offers → offer_id
            offer_id = self._upsert_job_offer(cur, item, company_id)

            # 3. UPSERT skills i powiązania offer_skills
            self._upsert_skills(cur, offer_id, item.get('skills', []))

            self.conn.commit()
            self.logger.debug(
                f"Zapisano ofertę {item['source_portal']}:{item['external_id']}"
            )

            cur.close()
            return item

        except psycopg2.Error as exc:
            self.conn.rollback()
            self.logger.error(
                f"Błąd zapisu {item['external_id']} do bazy: {exc}"
            )
            raise DropItem(f"Błąd bazy danych: {exc}") from exc

    def _upsert_company(self, cur: psycopg2.extensions.cursor, name: str) -> int:
        """UPSERT firmy po name.

        Args:
            cur: Kursor bazy danych.
            name: Nazwa firmy.

        Returns:
            ID firmy (company_id).
        """
        cur.execute(
            """
            INSERT INTO companies (name)
            VALUES (%s)
            ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """,
            (name,)
        )
        return cur.fetchone()[0]

    def _upsert_job_offer(
        self,
        cur: psycopg2.extensions.cursor,
        item: JobOfferItem,
        company_id: int
    ) -> str:
        """UPSERT oferty pracy po (source_portal, external_id).

        Przy konflikcie aktualizuje last_seen_at i is_active=TRUE.

        Args:
            cur: Kursor bazy danych.
            item: Oferta pracy.
            company_id: ID firmy.

        Returns:
            ID oferty (UUID jako string).
        """
        # Mapowanie salary_period: 'monthly' → 'month', 'hourly' → 'hour'
        salary_period = item.get('salary_period', 'month')
        if salary_period == 'monthly':
            salary_period = 'month'
        elif salary_period == 'hourly':
            salary_period = 'hour'

        cur.execute(
            """
            INSERT INTO job_offers (
                source_portal, external_id, title, company_id, contract_type,
                is_remote, city, salary_min, salary_max, salary_period,
                currency, experience_level
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_portal, external_id) DO UPDATE SET
                title = EXCLUDED.title,
                contract_type = EXCLUDED.contract_type,
                is_remote = EXCLUDED.is_remote,
                city = EXCLUDED.city,
                salary_min = EXCLUDED.salary_min,
                salary_max = EXCLUDED.salary_max,
                salary_period = EXCLUDED.salary_period,
                currency = EXCLUDED.currency,
                experience_level = EXCLUDED.experience_level,
                last_seen_at = CURRENT_TIMESTAMP,
                is_active = TRUE
            RETURNING id
            """,
            (
                item['source_portal'],
                item['external_id'],
                item['title'],
                company_id,
                item['contract_type'],
                item.get('fully_remote', False),  # fully_remote → is_remote
                item.get('city'),
                item.get('salary_min'),
                item.get('salary_max'),
                salary_period,
                item.get('salary_currency', 'PLN'),  # salary_currency → currency
                item['experience_level']
            )
        )
        return cur.fetchone()[0]

    def _upsert_skills(
        self,
        cur: psycopg2.extensions.cursor,
        offer_id: str,
        skills: list[dict[str, Any]]
    ) -> None:
        """UPSERT umiejętności i powiązania offer_skills.

        Args:
            cur: Kursor bazy danych.
            offer_id: ID oferty (UUID).
            skills: Lista umiejętności [{"name": str, "type": "must"|"nice"}].
        """
        for skill in skills:
            skill_name = skill.get('name', '').strip()
            if not skill_name:
                continue

            # UPSERT skill_taxonomy → skill_id
            # Na razie standardized_name = raw_name (normalizacja w przyszłości)
            cur.execute(
                """
                INSERT INTO skill_taxonomy (raw_name, standardized_name)
                VALUES (%s, %s)
                ON CONFLICT (raw_name) DO UPDATE SET raw_name = EXCLUDED.raw_name
                RETURNING id
                """,
                (skill_name, skill_name)
            )
            skill_id = cur.fetchone()[0]

            # INSERT offer_skills z ON CONFLICT DO NOTHING
            requirement_type = skill.get('type', 'must')  # 'must' | 'nice'
            cur.execute(
                """
                INSERT INTO offer_skills (offer_id, skill_id, requirement_type)
                VALUES (%s, %s, %s)
                ON CONFLICT (offer_id, skill_id) DO NOTHING
                """,
                (offer_id, skill_id, requirement_type)
            )
