# Projekt: SkillGap Monitor
# Autor: Mateusz Elżbieciak (Indeks: 233651)
# Uczelnia: Uniwersytet Ekonomiczny w Krakowie (UEK)

import scrapy


class JobOfferItem(scrapy.Item):
    """Ujednolicona struktura oferty pracy — niezależna od źródłowego portalu.

    Każdy spider (NoFluffJobs, JustJoin.it) mapuje dane portalu
    do tej struktury. Pipeline nie wie skąd pochodzi oferta.
    """

    # Identyfikacja i źródło
    external_id: str = scrapy.Field()       # ID oferty na portalu źródłowym
    source_portal: str = scrapy.Field()     # 'nofluffjobs' | 'justjoin'

    # Podstawowe dane oferty
    title: str = scrapy.Field()
    company_name: str = scrapy.Field()
    experience_level: str = scrapy.Field()  # 'junior' | 'mid' | 'senior' | 'lead'
    city: str = scrapy.Field()              # None jeśli fully_remote
    fully_remote: bool = scrapy.Field()
    offer_url: str = scrapy.Field()

    # Wynagrodzenie
    salary_min: float = scrapy.Field()      # None jeśli brak widełek
    salary_max: float = scrapy.Field()
    salary_currency: str = scrapy.Field()   # 'PLN' | 'EUR' | 'USD'
    salary_period: str = scrapy.Field()     # 'monthly' | 'hourly'
    contract_type: str = scrapy.Field()     # 'b2b' | 'uop' | 'uod' | 'other'

    # Umiejętności — listy słowników [{"name": str, "type": "must"|"nice"}]
    skills: list = scrapy.Field()

    # Metadane scrape'u
    scraped_at: str = scrapy.Field()        # ISO 8601
