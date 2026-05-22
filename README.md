# 🎯 SkillGap Monitor

**Zautomatyzowany system analityczny (Data Engineering) do monitorowania rynku pracy IT, wyliczania median wynagrodzeń oraz identyfikacji luk kompetencyjnych kandydatów (Skill Gap).**

Projekt zrealizowany w ramach zajęć na kierunku Informatyka Stosowana.
* **Autor:** Mateusz Elżbieciak
* **Nr indeksu:** 233651
* **Uczelnia:** Uniwersytet Ekonomiczny w Krakowie (UEK)
* **Docelowe przeznaczenie:** Portfolio inżynierskie (Junior Python Developer / DevOps Engineer)

---

## 🛠️ Architektura i Stos Technologiczny

Projekt opiera się na nowoczesnej architekturze przetwarzania danych:
* **Ekstrakcja Danych:** Python 3.11+, framework `Scrapy` (pobieranie danych z ukrytych API JSON w trybie *Polite Scraping*).
* **Baza Danych:** `PostgreSQL` hostowany w chmurze Supabase (znormalizowana struktura 3NF).
* **Zarządzanie Środowiskiem:** `uv` (Astral) - ultraszybki menedżer pakietów z plikiem `pyproject.toml`.
* **Warstwa Analityczna & GUI:** Biblioteka `Streamlit`.
* **Moduł AI (BYOK):** API OpenAI używane do tłumaczenia zapytań w języku naturalnym na bezpieczny kod SQL (Text-to-SQL).

---

## 🚀 Główne Funkcjonalności i Założenia Biznesowe

1. **Mechanizm Upsert & Soft Delete:** System rozwiązuje problem duplikatów ofert między portalami, stosując klauzulę `ON CONFLICT DO UPDATE`. Ogłoszenia usunięte z sieci otrzymują flagę `is_active = FALSE` po 48h, co pozwala liczyć wskaźnik *Time-to-Fill*.
2. **Kalkulator "Skill Gap":** Zastosowanie operacji na zbiorach (Set Theory) do porównywania kompetencji kandydata z twardymi wymaganiami rynkowymi.
3. **Analiza Finansowa:** Ścisła separacja w bazie danych wynagrodzeń w formacie B2B (netto) od UoP (brutto) zapobiegająca przekłamaniom statystycznym.
4. **Bezpieczeństwo AI:** Dedykowana rola bazodanowa `ai_read_only` blokująca możliwość wykonania wstrzyknięcia SQL (SQL Injection) przez model LLM.

---

## 📋 Struktura Podziału Pracy (WBS)

```text
🎯 PROJEKT: SKILLGAP MONITOR (WBS)
│
├── 🗄️ FAZA 1: Środowisko i Baza Danych (Data Storage)
│   ├── 1.1 Konfiguracja bazy w chmurze (Supabase)
│   ├── 1.2 Wdrożenie struktury tabel DDL (3NF)
│   ├── 1.3 Utworzenie ról bezpieczeństwa (ai_read_only)
│   └── 1.4 Konfiguracja zmiennych środowiskowych (.env)
│
├── 🕷️ FAZA 2: Ekstrakcja Danych (Scraping)
│   ├── 2.1 Inicjalizacja frameworka Scrapy
│   ├── 2.2 Konfiguracja polityki Polite Scraping (Anty-Ban)
│   ├── 2.3 Budowa pająków pobierających z ukrytych API (JSON)
│   └── 2.4 Zmapowanie odpowiedzi do obiektów (JobOfferItem)
│
├── ⚙️ FAZA 3: Przetwarzanie Danych (Data Pipelines)
│   ├── 3.1 ValidationPipeline: Czyszczenie HTML, flagi B2B/UoP
│   ├── 3.2 PostgresPipeline: Zapis logiką UPSERT (bez duplikatów)
│   ├── 3.3 Implementacja logiki czasu widoczności (Soft Delete)
│   └── 3.4 Budowa modułu alertującego (Webhook) przy braku danych
│
├── 🧠 FAZA 4: Logika Biznesowa i Algorytmy
│   ├── 4.1 Zimny Start: Skrypt AI budujący początkowy słownik IT
│   ├── 4.2 Mechanizm mapowania surowych tagów na słownik w locie
│   └── 4.3 Silnik kalkulacji "Skill Gap" oparty na teorii zbiorów
│
├── 🖥️ FAZA 5: Aplikacja B2C i Moduł AI (Frontend)
│   ├── 5.1 Inicjalizacja dashboardu analitycznego w Streamlit
│   ├── 5.2 Budowa formularza profilowania kandydata
│   ├── 5.3 Wizualizacja danych (wykresy zarobków per kontrakt)
│   └── 5.4 Wdrożenie modułu OpenAI (BYOK) Text-to-SQL
│
└── 📋 FAZA 6: Zamknięcie i Dokumentacja
    ├── 6.1 Generowanie raportów technicznych (Indeks: 233651)
    └── 6.2 Opracowanie GitHub README (diagramy, instrukcje uruchomienia)
```

---

## 📅 Harmonogram Prac (Sprinty Agile)

### Sprint 1: Fundamenty, Inżynieria Danych i Pierwsze Zbiory
* **Cel:** Baza stoi w chmurze, a Scrapy potrafi autonomicznie zasysać oferty, nie tworząc duplikatów i rozróżniając B2B od UoP.
* **Zakres:** Faza 1 (Całość), Faza 2 (Całość), Faza 3 (3.1, 3.2, 3.3).

### Sprint 2: Analityka, Czystość Danych i Monitoring
* **Cel:** System potrafi zmapować "brudne" technologie rekruterów na czysty słownik. Pająki działają stabilnie, a w razie awarii API portalu wysyłają alert.
* **Zakres:** Faza 3 (3.4 - Webhook), Faza 4 (Całość).

### Sprint 3: Interfejs, AI i Portfolio
* **Cel:** Aplikacja otrzymuje interfejs Streamlit. Działa moduł Text-to-SQL. Projekt jest spakowany pod kątem wymagań rekrutacyjnych.
* **Zakres:** Faza 5 (Całość), Faza 6 (Całość).

---

## 💻 Instrukcja Uruchomienia (Local Setup)

Ten projekt wykorzystuje nowoczesnego menedżera pakietów `uv`.

### 1. Sklonuj repozytorium
```bash
git clone [https://github.com/TwojNick/skillgap-monitor.git](https://github.com/TwojNick/skillgap-monitor.git)
cd skillgap-monitor
```

### 2. Skonfiguruj zmienne środowiskowe
Utwórz plik `.env` w głównym katalogu projektu:
```env
# URL połączenia z bazą danych PostgreSQL (Supabase)
DATABASE_URL="postgresql://postgres:HASLO@adres-supabase.com:6543/postgres"

# Klucz do API OpenAI (Moduł Text-to-SQL)
OPENAI_API_KEY="sk-proj-twoj_tajny_klucz"
```

### 3. Zainstaluj zależności i aktywuj środowisko
```bash
uv sync
```

Aktywacja wirtualnego środowiska:
* **Windows (PowerShell):** `.venv\Scripts\activate`
* **Mac/Linux:** `source .venv/bin/activate`

### 4. Inicjalizacja bazy danych (Faza 1)
```bash
uv run scripts/init_db.py
```

### 5. Uruchomienie aplikacji Streamlit (Faza 5)
```bash
streamlit run app/main.py
```