# Projekt: SkillGap Monitor
# Autor: Mateusz Elżbieciak (Indeks: 233651)
# Uczelnia: Uniwersytet Ekonomiczny w Krakowie (UEK)

import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import scrapy
from scrapy.http import Response

from scraper.items import JobOfferItem

logger = logging.getLogger(__name__)

BASE_URL = "https://justjoin.it"
API_ENDPOINT = f"{BASE_URL}/api/candidate-api/offers"
PAGE_SIZE = 100
MAX_ITEMS = 1000

# Priorytet wyboru typu umowy przy salary extraction
CONTRACT_PRIORITY = ["b2b", "permanent", "mandate_contract"]

CONTRACT_MAPPING: dict[str, str] = {
    "b2b": "b2b",
    "permanent": "uop",
    "mandate_contract": "uod",
}


class JustJoinSpider(scrapy.Spider):
    """Spider dla JustJoin.it — pobiera oferty z REST API kandydatów.

    Paginacja oparta na offsetcie (from=0, 100, 200, ...).
    Wszystkie dane oferty dostępne w pojedynczym GET — brak kroku szczegółów.
    Zatrzymuje się przy len(data) < PAGE_SIZE lub po osiągnięciu MAX_ITEMS.
    """

    name = "justjoin"
    allowed_domains = ["justjoin.it"]

    async def start(self) -> AsyncGenerator:
        """Generuje pierwsze żądanie — pierwsza strona listy ofert."""
        yield self._make_request(offset=0)

    def _make_request(self, offset: int) -> scrapy.Request:
        """Buduje żądanie GET do endpointu listy ofert.

        Args:
            offset: Numer oferty od której zaczyna się strona (0-based).

        Returns:
            Żądanie GET z parametrami paginacji.
        """
        url = (
            f"{API_ENDPOINT}"
            f"?from={offset}&itemsCount={PAGE_SIZE}"
            f"&sortBy=publishedAt&orderBy=descending"
        )
        return scrapy.Request(
            url=url,
            headers={"Accept": "application/json"},
            callback=self.parse_listing,
            cb_kwargs={"offset": offset},
        )

    def parse_listing(self, response: Response, offset: int) -> Any:
        """Parsuje stronę listy ofert i zwraca itemy + kolejne żądanie.

        Args:
            response: Odpowiedź HTTP z listą ofert w formacie JSON.
            offset: Aktualny offset paginacji.

        Yields:
            Wypełnione JobOfferItem gotowe do walidacji w pipeline.
            Żądanie GET do następnej strony (paginacja).
        """
        try:
            payload = response.json()
        except Exception as e:
            logger.error(f"Błąd parsowania JSON (offset={offset}): {e}")
            return

        offers: list[dict[str, Any]] = payload.get("data", [])
        logger.info(f"[justjoin] offset={offset}: {len(offers)} ofert")

        for offer in offers:
            item = self._map_offer(offer)
            if item is not None:
                yield item

        fetched_so_far = offset + len(offers)
        if len(offers) == PAGE_SIZE and fetched_so_far < MAX_ITEMS:
            next_offset = payload.get("meta", {}).get("next", {}).get("cursor", fetched_so_far)
            yield self._make_request(offset=next_offset)

    def _map_offer(self, offer: dict[str, Any]) -> JobOfferItem | None:
        """Mapuje pojedynczą ofertę z API do wspólnego JobOfferItem.

        Args:
            offer: Słownik z danymi oferty z JustJoin.it API.

        Returns:
            Wypełniony JobOfferItem lub None jeśli brak wymaganego ID.
        """
        external_id = offer.get("guid")
        if not external_id:
            logger.warning(f"Brak guid w ofercie: {offer.get('title', '?')}")
            return None

        slug = offer.get("slug", "")
        offer_url = f"{BASE_URL}/job-offer/{slug}" if slug else f"{BASE_URL}"

        workplace_type = offer.get("workplaceType", "")
        fully_remote = workplace_type == "remote"
        city: str | None = offer.get("city") if not fully_remote else None

        salary_min, salary_max, salary_currency, salary_period, contract_type = (
            self._extract_salary(offer.get("employmentTypes", []))
        )

        skills: list[dict[str, str]] = []
        for skill in offer.get("requiredSkills", []):
            name = skill.get("name")
            if name:
                skills.append({"name": name, "type": "must"})
        for skill in offer.get("niceToHaveSkills", []):
            name = skill.get("name")
            if name:
                skills.append({"name": name, "type": "nice"})

        experience_level = self._normalize_experience(offer.get("experienceLevel", ""))

        return JobOfferItem(
            external_id=str(external_id),
            source_portal="justjoin",
            title=offer.get("title", ""),
            company_name=offer.get("companyName", ""),
            experience_level=experience_level,
            city=city,
            fully_remote=fully_remote,
            offer_url=offer_url,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            salary_period=salary_period,
            contract_type=contract_type,
            skills=skills,
            scraped_at=datetime.now(timezone.utc).isoformat(),
        )

    # ------------------------------------------------------------------
    # Metody pomocnicze
    # ------------------------------------------------------------------

    def _extract_salary(
        self,
        employment_types: list[dict[str, Any]],
    ) -> tuple[float | None, float | None, str, str, str]:
        """Wybiera najlepszy wpis wynagrodzenia według priorytetu typu umowy.

        Filtruje wyłącznie wpisy z currencySource == "original" i currency == "PLN".
        Priorytet: b2b > permanent > mandate_contract > pierwszy dostępny.

        Args:
            employment_types: Lista obiektów employmentTypes z odpowiedzi API.

        Returns:
            Krotka (salary_min, salary_max, currency, salary_period, contract_type).
            Zwraca (None, None, 'PLN', 'monthly', 'other') gdy brak wpisu PLN original.
        """
        # Tylko oryginalne wpisy PLN
        pln_entries = [
            et for et in employment_types
            if et.get("currencySource") == "original"
            and (et.get("currency") or "").upper() == "PLN"
        ]

        if not pln_entries:
            return None, None, "PLN", "monthly", "other"

        # Wybierz według priorytetu typu umowy
        selected: dict[str, Any] | None = None
        for contract_key in CONTRACT_PRIORITY:
            for entry in pln_entries:
                if entry.get("type") == contract_key:
                    selected = entry
                    break
            if selected is not None:
                break

        if selected is None:
            selected = pln_entries[0]

        contract_raw = selected.get("type", "")
        contract_type = CONTRACT_MAPPING.get(contract_raw, "other")

        unit = selected.get("unit", "Month")
        salary_period = "hourly" if (unit or "").lower() == "hour" else "monthly"

        from_val = selected.get("from")
        to_val = selected.get("to")
        salary_min = float(from_val) if from_val is not None else None
        salary_max = float(to_val) if to_val is not None else None

        return salary_min, salary_max, "PLN", salary_period, contract_type

    def _normalize_experience(self, level: str) -> str:
        """Normalizuje poziom doświadczenia z API JustJoin do wartości słownikowej.

        Args:
            level: Surowa wartość z API (np. 'junior', 'mid', 'c_level').

        Returns:
            Znormalizowany poziom: 'junior' | 'mid' | 'senior' | 'lead'.
        """
        mapping: dict[str, str] = {
            "junior": "junior",
            "mid": "mid",
            "senior": "senior",
            "manager": "lead",
            "c_level": "lead",
        }
        return mapping.get(level.lower() if level else "", "mid")
