# WBS — SkillGap Monitor (Work Breakdown Structure)

**Autor:** Mateusz Elżbieciak (indeks: 233651), UEK

> Hierarchiczny podział prac. Harmonogram/sekwencja → `PLAN_DZIALANIA.md`. Specyfikacja → `PRD_SKILLGAP.md`.
> Legenda: ✅ ukończone · ▢ do zrobienia · ◇ opcjonalne (Future Work / jeśli czas pozwoli)

---

```
PROJEKT: SKILLGAP MONITOR
│
├── FAZA 1: Środowisko i Baza Danych                                    ✅
│   ├── 1.1 Konfiguracja środowiska (uv, Python 3.13, pyproject.toml)   ✅
│   ├── 1.2 Konfiguracja bazy w chmurze (Supabase, Transaction Pooler)  ✅
│   ├── 1.3 Wdrożenie schematu DDL w 3NF (init_db.py, 4 tabele)         ✅
│   ├── 1.4 Konfiguracja zmiennych środowiskowych (.env)               ✅
│   └── 1.5 Rola bezpieczeństwa ai_read_only (SQL Editor, hasło z .env) ▢
│
├── FAZA 2: Ekstrakcja danych — portal podstawowy (NoFluffJobs)         ▢
│   ├── 2.1 Inicjalizacja projektu Scrapy + settings.py (Polite Scraping) ▢
│   ├── 2.2 Definicja wspólnego JobOfferItem                            ▢
│   ├── 2.3 Spider krok 1: lista ofert (POST, paginacja, per-technologia) ▢
│   └── 2.4 Spider krok 2: szczegóły oferty (GET /posting/{id}, requirements) ▢
│
├── FAZA 3: Przetwarzanie danych (Data Pipelines)                       ▢
│   ├── 3.1 ValidationPipeline: czyszczenie pól JSON-HTML, flagi B2B/UoP ▢
│   ├── 3.2 ValidationPipeline: normalizacja nazw skilli                ▢
│   ├── 3.3 PostgresPipeline: zapis logiką UPSERT (bez duplikatów)      ▢
│   ├── 3.4 PostgresPipeline: zapis skilli i powiązań (requirement_type) ▢
│   └── 3.5 Logika Soft Delete (is_active = FALSE)                      ▢
│
├── FAZA 4: Drugi portal (JustJoin.it)                                  ▢
│   ├── 4.1 Weryfikacja API w DevTools (endpoint, format, paginacja)    ▢
│   ├── 4.2 Spider JustJoin mapujący do wspólnego JobOfferItem          ▢
│   └── 4.3 Test deduplikacji między portalami                         ▢
│
├── FAZA 5: Logika biznesowa i zbiór danych                             ▢
│   ├── 5.1 Bootstrap: skrypt seedujący słownik skill_taxonomy          ▢
│   ├── 5.2 Mapowanie surowych tagów na słownik znormalizowany          ▢
│   └── 5.3 Pełny scrape reprezentatywnej próbki (~700-2500 ofert)      ▢
│
├── FAZA 6: Aplikacja analityczna (Streamlit)                           ▢
│   ├── 6.1 Inicjalizacja dashboardu Streamlit                          ▢
│   ├── 6.2 Statystyka 1: Salary Explorer (mediana + P25/P75)           ▢
│   ├── 6.3 Statystyka 2: Skill Premium (wpływ skilli na medianę płac)  ▢
│   ├── 6.4 Statystyka 3: Skill Gap / Demand (skille per poziom)        ▢
│   ├── 6.5 Interaktywne filtry (poziom, miasto, typ umowy)             ▢
│   └── 6.6 Strona tytułowa z indeksem 233651                           ▢
│
├── FAZA 7: Zamknięcie i dokumentacja                                   ▢
│   ├── 7.1 README (instrukcja setup + uruchamiania)                    ▢
│   ├── 7.2 Finalizacja Raportu (indeks 233651)                         ▢
│   ├── 7.3 Porządek Git (Conventional Commits) + push                  ▢
│   └── 7.4 Własny code review (PEP8, type hints, docstringi)           ▢
│
└── ELEMENTY OPCJONALNE                                                 ◇
    ├── O.1 Trzeci portal (Bulldogjob)                                  ◇
    ├── O.2 Moduł AI Text-to-SQL (BYOK) na roli ai_read_only            ◇
    ├── O.3 Konteneryzacja (Docker)                                     ◇
    └── O.4 Wdrożenie chmurowe (Vercel/Railway) + scheduled scraping    ◇
```

---

## Zmiany względem pierwotnego WBS (od Gemini)

Dla przejrzystości — co i dlaczego się zmieniło:

- **AI Text-to-SQL** przeniesione z Fazy 5 (aktywna) do elementów opcjonalnych (Future Work) — zakres realny na 2 tygodnie.
- **Webhook alertujący** (dawna Faza 3.4) usunięty — nie jest częścią celu minimalnego.
- **Dodano osobną Fazę 4 (drugi portal)** — projekt jest świadomie multi-portal (min. 2 źródła).
- **Doprecyzowano scraping per-technologia** (NoFluff jest wielobranżowy, brak filtra „całe IT").
- **Dodano normalizację skilli** jako osobne zadanie (jakość danych analitycznych).
- **Analityka rozbita na 3 konkretne statystyki HR** zamiast ogólnego „silnika Skill Gap".
