# Projekt: SkillGap Monitor
# Autor: Mateusz Elżbieciak (Indeks: 233651)
# Uczelnia: Uniwersytet Ekonomiczny w Krakowie (UEK)

import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import scrapy
from scrapy.http import Response

from scraper.items import JobOfferItem

logger = logging.getLogger(__name__)

# Technologie po których iterujemy — portal jest multi-branżowy,
# brak filtra "całe IT". Scraping per-technologia + deduplikacja w bazie.
TECHNOLOGIES = [
    "Python", "Java", "JavaScript", "TypeScript", "C#",
    "Go", "Rust", "Kotlin", "Scala", "React", "Angular",
    # nowe:
    "Docker", "Kubernetes", "AWS", "DevOps", "PHP",
    "Ruby", "Vue", "Node.js", "Swift", "Flutter",
    "Terraform", "Linux", "Spark", "Kafka", "Elasticsearch",
]

# Ile stron na technologię (20 ofert/strona → max ~100 ofert/tech przy 5 stronach)
PAGES_PER_TECH = 10

BASE_URL = "https://nofluffjobs.com"
SEARCH_ENDPOINT = f"{BASE_URL}/api/search/posting"
DETAIL_ENDPOINT = f"{BASE_URL}/api/posting"


class NoFluffJobsSpider(scrapy.Spider):
    """Dwustopniowy spider dla NoFluffJobs.

    Krok 1: POST /api/search/posting — lista ofert per technologia, paginacja.
    Krok 2: GET /api/posting/{id} — pełne szczegóły (requirements.musts + nices).

    Dane są w czystym JSON — nie parsujemy HTML/DOM.
    """

    name = "nofluffjobs"
    allowed_domains = ["nofluffjobs.com"]

    async def start(self) -> AsyncGenerator:
        """Generuje pierwsze żądania — lista ofert per technologia, strona 1."""
        for tech in TECHNOLOGIES:
            yield self._make_search_request(tech, page=1)

    def _make_search_request(self, technology: str, page: int) -> scrapy.Request:
        """Buduje żądanie POST do endpointu listy ofert.

        Args:
            technology: Nazwa technologii (np. 'Python').
            page: Numer strony (1-based).

        Returns:
            Żądanie POST z odpowiednim body i nagłówkami.
        """
        body = json.dumps({
            "criteriaSearch": {
                "city": [], "company": [], "category": [], "country": [],
                "employment": [], "seniority": [], "requirement": [technology],
                "salary": [], "more": [], "applicationStatus": [], "keyword": [],
                "jobLanguage": [], "jobPosition": [], "province": [], "id": [],
                "withSalaryMatch": [],
            },
            "pageSize": 20,
            "withSalaryMatch": True,
        })
        return scrapy.Request(
            url=(
                f"{SEARCH_ENDPOINT}"
                f"?pageFrom={page}&pageTo={page}&pageSize=20"
                f"&salaryCurrency=PLN&salaryPeriod=month"
                f"&region=pl&language=pl-PL&withSalaryMatch=true"
            ),
            method="POST",
            body=body,
            headers={
                "Content-Type": "application/infiniteSearch+json",
                "Accept": "application/json",
            },
            callback=self.parse_listing,
            cb_kwargs={"technology": technology, "page": page},
        )

    def parse_listing(
        self,
        response: Response,
        technology: str,
        page: int,
    ) -> Any:
        """Parsuje odpowiedź listy ofert i inicjuje pobieranie szczegółów.

        Args:
            response: Odpowiedź HTTP z listą ofert w formacie JSON.
            technology: Technologia której dotyczy żądanie (do logowania).
            page: Aktualny numer strony.

        Yields:
            Żądania GET do endpointów szczegółów ofert.
            Żądania POST do kolejnych stron (paginacja).
        """
        try:
            data = response.json()
        except Exception as e:
            logger.error(f"Błąd parsowania JSON (tech={technology}, page={page}): {e}")
            return

        postings = data.get("postings", [])
        if not postings:
            # Sprawdź alternatywną strukturę odpowiedzi
            postings = data.get("tiles", {}).get("values", [])

        logger.info(f"[{technology}] strona {page}: {len(postings)} ofert")

        for posting in postings:
            offer_id = posting.get("id") or posting.get("postingId")
            if not offer_id:
                logger.warning(f"Brak ID oferty: {posting}")
                continue

            yield scrapy.Request(
                url=f"{DETAIL_ENDPOINT}/{offer_id}",
                callback=self.parse_detail,
                cb_kwargs={"listing_data": posting},
            )

        # Paginacja — jeśli była pełna strona i nie przekroczyliśmy limitu
        if len(postings) == 20 and page < PAGES_PER_TECH:
            yield self._make_search_request(technology, page + 1)

    def parse_detail(
        self,
        response: Response,
        listing_data: dict[str, Any],
    ) -> Any:
        """Parsuje szczegóły oferty i zwraca wypełniony JobOfferItem.

        Args:
            response: Odpowiedź HTTP ze szczegółami oferty w formacie JSON.
            listing_data: Dane z listingu (seniority, salary.type, lokalizacja).

        Yields:
            Wypełniony JobOfferItem gotowy do walidacji w pipeline.
        """
        try:
            data = response.json()
        except Exception as e:
            logger.error(f"Błąd parsowania JSON szczegółów {response.url}: {e}")
            return

        # --- Identyfikacja ---
        offer_id = data.get("id") or listing_data.get("id")
        if not offer_id:
            logger.warning(f"Brak ID w szczegółach: {response.url}")
            return

        # --- Lokalizacja ---
        location = listing_data.get("location", {})
        fully_remote = location.get("fullyRemote", False)
        city = None
        if not fully_remote:
            colocations = location.get("colocations", [])
            if colocations:
                city = colocations[0].get("city")

        # --- Wynagrodzenie ---
        salary_data = listing_data.get("salary") or {}
        essentials = data.get("essentials", {})
        original_salary = essentials.get("originalSalary") or {}

        salary_min, salary_max, salary_currency, salary_period, contract_type = (
            self._extract_salary(salary_data, original_salary)
        )

        # --- Umiejętności z detali (pełna lista) ---
        requirements = data.get("requirements", {})
        skills = []
        for skill in requirements.get("musts", []):
            name = skill.get("value") or skill.get("name") or skill.get("skill")
            if name:
                skills.append({"name": name, "type": "must"})
        for skill in requirements.get("nices", []):
            name = skill.get("value") or skill.get("name") or skill.get("skill")
            if name:
                skills.append({"name": name, "type": "nice"})

        # --- Poziom doświadczenia ---
        seniority_raw = listing_data.get("seniority", [])
        experience_level = self._normalize_seniority(seniority_raw)

        item = JobOfferItem(
            external_id=str(offer_id),
            source_portal="nofluffjobs",
            title=data.get("title") or listing_data.get("title", ""),
            company_name=self._extract_company(data, listing_data),
            experience_level=experience_level,
            city=city,
            fully_remote=fully_remote,
            offer_url=f"{BASE_URL}/job/{offer_id}",
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            salary_period=salary_period,
            contract_type=contract_type,
            skills=skills,
            scraped_at=datetime.now(timezone.utc).isoformat(),
        )

        yield item

    # ------------------------------------------------------------------
    # Metody pomocnicze
    # ------------------------------------------------------------------

    def _extract_salary(
        self,
        salary_data: dict[str, Any],
        original_salary: dict[str, Any],
    ) -> tuple[float | None, float | None, str, str, str]:
        """Wyciąga dane wynagrodzenia z różnych miejsc w odpowiedzi API.

        Args:
            salary_data: Dane salary z listingu (typ umowy, waluta).
            original_salary: Dane z essentials.originalSalary (stawki, okres).

        Returns:
            Krotka (salary_min, salary_max, currency, period, contract_type).
        """
        contract_raw = salary_data.get("type", "")
        contract_type = self._normalize_contract(contract_raw)

        currency = (
            salary_data.get("currency")
            or original_salary.get("currency", "PLN")
        ).upper()

        # Okres rozliczenia — B2B często rozlicza godzinowo
        period_raw = original_salary.get("period", "monthly")
        salary_period = "hourly" if "hour" in period_raw.lower() else "monthly"

        from_val = original_salary.get("from") or salary_data.get("from")
        to_val = original_salary.get("to") or salary_data.get("to")

        salary_min = float(from_val) if from_val is not None else None
        salary_max = float(to_val) if to_val is not None else None

        return salary_min, salary_max, currency, salary_period, contract_type

    def _normalize_contract(self, contract_raw: str) -> str:
        """Normalizuje typ umowy do wartości słownikowej.

        Args:
            contract_raw: Surowa wartość z API (np. 'b2b', 'employment').

        Returns:
            Znormalizowany typ: 'b2b' | 'uop' | 'uod' | 'other'.
        """
        mapping = {
            "b2b": "b2b",
            "employment": "uop",
            "mandate": "uod",
        }
        return mapping.get(contract_raw.lower(), "other")

    def _normalize_seniority(self, seniority_raw: list | str) -> str:
        """Normalizuje poziom doświadczenia do wartości słownikowej.

        Args:
            seniority_raw: Lista lub string z API (np. ['junior'], 'senior').

        Returns:
            Znormalizowany poziom: 'junior' | 'mid' | 'senior' | 'lead'.
        """
        if isinstance(seniority_raw, list):
            value = seniority_raw[0] if seniority_raw else ""
        else:
            value = seniority_raw or ""

        mapping = {
            "junior": "junior",
            "mid": "mid",
            "regular": "mid",
            "senior": "senior",
            "lead": "lead",
            "expert": "lead",
            "principal": "lead",
        }
        return mapping.get(value.lower(), "mid")

    def _extract_company(
        self,
        detail_data: dict[str, Any],
        listing_data: dict[str, Any],
    ) -> str:
        """Wyciąga nazwę firmy z danych szczegółów lub listingu.

        Args:
            detail_data: Pełne dane szczegółów oferty.
            listing_data: Skrócone dane z listingu.

        Returns:
            Nazwa firmy lub pusty string jeśli niedostępna.
        """
        company = (
            detail_data.get("company", {}).get("name")
            or listing_data.get("company", {}).get("name")
            or listing_data.get("companyName", "")
        )
        return company or ""
