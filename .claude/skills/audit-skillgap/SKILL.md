# Ścisły Code Review dla projektu SkillGap Monitor

Ten skill służy do weryfikacji nowo napisanego kodu Pythona (Scrapy, FastAPI, Streamlit) oraz zapytań SQL dla projektu analitycznego rynku pracy IT.

## Zasady weryfikacji:

1. **Standardy Pythona:** Upewnij się, że kod jest zgodny z PEP8. Zmienne powinny mieć czytelne, angielskie nazwy. Używaj typowania (Type Hints) dla funkcji.
2. **Polityka Scrapingu (Faza 2):** Jeśli kod dotyczy frameworka Scrapy, absolutnie wymagane jest zachowanie polityki "Polite Scraping". Sprawdź, czy `DOWNLOAD_DELAY` wynosi co najmniej 1.5 sekundy.
3. **Baza Danych (PostgreSQL):** Jeśli sprawdzasz zapytania SQL lub logikę zapisu, upewnij się, że kod wykorzystuje mechanizm UPSERT (`ON CONFLICT DO UPDATE`) zamiast zwykłego `INSERT`.
4. **Zarządzanie Zależnościami:** Pamiętaj, że projekt wykorzystuje menedżera pakietów `uv`. Nie sugeruj instalacji przez `pip install` ani używania pliku `requirements.txt`.
5. **Bezpieczeństwo:** Jeśli kod dotyczy modułu sztucznej inteligencji, upewnij się, że w zapytaniach do bazy używana jest rola `ai_read_only`.

Po przeprowadzeniu analizy, wypisz błędy w formie wypunktowanej listy i zaproponuj poprawiony kod.