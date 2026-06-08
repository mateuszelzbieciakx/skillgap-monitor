# WBS — SkillGap Monitor (Work Breakdown Structure)

**Autor:** Mateusz Elżbieciak (indeks: 233651), UEK

> Hierarchiczny podział prac. Plan realizacji → `PLAN_DZIALANIA.md`. Specyfikacja → `PRD_SKILLGAP.md`.
> Legenda: ✅ ukończone · ▢ niezrealizowane · ◇ opcjonalne (Future Work)

---

```
PROJEKT: SKILLGAP MONITOR
│
├── FAZA 1: Środowisko i Baza Danych                                          ✅
│   ├── 1.1 Konfiguracja środowiska (uv, Python 3.13, pyproject.toml)         ✅
│   ├── 1.2 Konfiguracja bazy w chmurze (Supabase, Transaction Pooler)        ✅
│   ├── 1.3 Wdrożenie schematu DDL w 3NF (init_db.py, 4 tabele + is_tech)     ✅
│   ├── 1.4 Konfiguracja zmiennych środowiskowych (.env)                      ✅
│   └── 1.5 Rola bezpieczeństwa ai_read_only (SQL Editor, hasło z .env)       ✅
│
├── FAZA 2: Ekstrakcja danych — NoFluffJobs (dwustopniowy)                    ✅
│   ├── 2.1 Inicjalizacja projektu Scrapy + settings.py (Polite Scraping)     ✅
│   ├── 2.2 Definicja wspólnego JobOfferItem (multi-portal)                   ✅
│   ├── 2.3 Spider krok 1: lista ofert (POST, paginacja, 25 technologii)      ✅
│   └── 2.4 Spider krok 2: szczegóły oferty (GET /posting/{id}, requirements) ✅
│
├── FAZA 3: Przetwarzanie danych (Data Pipelines)                             ✅
│   ├── 3.1 ValidationPipeline: czyszczenie HTML, normalizacja experience/contract ✅
│   ├── 3.2 ValidationPipeline: scentralizowana walidacja salary              ✅
│   │       (progi rynkowe per contract_type, odwrócone widełki, period passthrough)
│   ├── 3.3 PostgresPipeline: zapis logiką UPSERT (bez duplikatów)            ✅
│   ├── 3.4 PostgresPipeline: zapis skilli i powiązań (requirement_type)      ✅
│   └── 3.5 Logika Soft Delete (is_active = FALSE)                            ✅
│
├── FAZA 4: Drugi portal (JustJoin.it)                                        ✅
│   ├── 4.1 Weryfikacja API w DevTools (GET candidate-api, format offset)     ✅
│   ├── 4.2 Spider JustJoin — jednokrokowy, do 10 000 ofert                  ✅
│   │       (priorytet umów: b2b > permanent > mandate_contract)
│   ├── 4.3 Spider jako czysty maper — salary validation wyłącznie w pipeline ✅
│   ├── 4.4 Test deduplikacji między portalami                                ✅
│   └── 4.5 4 migracje SQL czyszczące dane historyczne (001–004)              ✅
│
├── FAZA 5: Logika biznesowa i zbiór danych                                   ✅
│   ├── 5.1 Bootstrap: skrypt seedujący słownik skill_taxonomy                ▢
│   │       (bootstrap_skills.py — niezaimplementowany, Future Work)
│   ├── 5.2 Normalizacja skilli: standardized_name via migracja 001           ✅
│   └── 5.3 Pełny scrape (~10 000+ ofert: JustJoin 10k + NoFluff 25 tech)    ✅
│
├── FAZA 6: Aplikacja analityczna (Streamlit)                                 ✅
│   ├── 6.1 Dark theme (Apple-inspired), Plotly custom template                ✅
│   ├── 6.2 Salary Explorer — mediana + P25/P75 × level × contract type       ✅
│   ├── 6.3 Skill Premium — metoda within-level (mediana odchyleń od baseline) ✅
│   │       kontroluje experience_level jako zmienną zakłócającą
│   ├── 6.4 Skill Gap — top 15 skilli per poziom: must-have vs nice-to-have   ✅
│   ├── 6.5 Globalne filtry sidebar: portal, poziom doświadczenia, typ umowy  ✅
│   └── 6.6 Informacja o autorze (indeks 233651) w ekspanderze sidebar        ✅
│
├── FAZA 7: Zamknięcie i dokumentacja                                         ✅
│   ├── 7.1 README.md — portfolio-ready (architektura, badges, setup guide)   ✅
│   ├── 7.2 Finalizacja RAPORT.md (indeks 233651)                             ✅
│   ├── 7.3 PRD_SKILLGAP.md — zaktualizowany do stanu rzeczywistego           ✅
│   ├── 7.4 CLAUDE.md — zaktualizowany do stanu rzeczywistego                 ✅
│   ├── 7.5 Conventional Commits + push do GitHub                             ✅
│   └── 7.6 Code review: PEP8, type hints, Google-style docstrings            ✅
│
└── ELEMENTY OPCJONALNE (Future Work)                                         ◇
    ├── O.1 Trzeci portal (Bulldogjob)                                        ◇
    ├── O.2 bootstrap_skills.py — seed startowy skill_taxonomy                ◇
    ├── O.3 Moduł AI Text-to-SQL (BYOK) na roli ai_read_only                 ◇
    ├── O.4 Scheduled scraping (GitHub Actions cron / AWS EventBridge)        ◇
    ├── O.5 Wdrożenie chmurowe (AWS EC2 + RDS lub Railway)                   ◇
    ├── O.6 Konteneryzacja (Docker)                                           ◇
    └── O.7 Testy jednostkowe ValidationPipeline._validate_salary (pytest)    ◇
```

---

## Zmiany względem pierwotnego WBS

- **AI Text-to-SQL** przeniesione do elementów opcjonalnych — poza zakresem projektu.
- **Webhook alertujący** usunięty — nie jest częścią celu minimalnego.
- **Faza 4 (drugi portal JustJoin.it)** zrealizowana — jednokrokowy spider, 10 000 ofert.
- **Scentralizowana walidacja salary** (3.2) dodana — progi rynkowe per `contract_type`, spidery są czystymi maperami.
- **4 migracje SQL** (4.5) — czyszczenie danych historycznych po pełnym scrape'ie.
- **Skill Premium within-level** (6.3) — metoda kontrolująca zmienną zakłócającą (poziom doświadczenia).
- **Próba scrapowania** zaktualizowana: 700–2500 ofert → 10 000+ z dwóch portali.
- **bootstrap_skills.py** (5.1) — pozostaje niezrealizowany (Future Work).
