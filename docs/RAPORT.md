# RAPORT Z FAZY PLANOWANIA I ARCHITEKTURY SYSTEMU
## Projekt: „SkillGap Monitor"

**Uniwersytet Ekonomiczny w Krakowie**
**Kierunek:** Informatyka Stosowana
**Autor:** Mateusz Elżbieciak
**Nr indeksu:** 233651

---

## 1. Cel biznesowy i założenia projektu

Celem projektu jest budowa zautomatyzowanego systemu analitycznego klasy Data Engineering, służącego do monitorowania polskiego rynku pracy IT, z możliwością analizy na poziomie poszczególnych miast (m.in. Krakowa). System umożliwia analizę trendów wynagrodzeń, badanie wymagań technologicznych oraz identyfikację tzw. luk kompetencyjnych (Skill Gap) — szczególnie pod kątem stanowisk wejściowych, takich jak Junior Python Developer czy Junior DevOps.

Wartością wyróżniającą projekt jest nacisk na statystyki użyteczne biznesowo (z perspektywy działów HR i rekrutacji): benchmark wynagrodzeń, wpływ konkretnych umiejętności na medianę płac („skill premium") oraz mapa popytu na kompetencje w podziale na poziomy doświadczenia.

System pobiera, czyści i normalizuje publicznie dostępne dane z portali branżowych, dostarczając ustrukturyzowane informacje do relacyjnej bazy danych pełniącej rolę Single Source of Truth. W obecnej fazie źródłem podstawowym jest **NoFluffJobs**, a docelowo (w ramach niniejszego projektu) dołączany jest drugi portal — **JustJoin.it**. Architektura jest świadomie zaprojektowana pod wiele źródeł, co umożliwia dalszą rozbudowę (np. Bulldogjob) bez zmian w warstwie składowania.

## 2. Architektura systemu i stos technologiczny

Projekt opiera się na architekturze chmurowej z lokalną warstwą ekstrakcji:

- **Moduł ekstrakcji danych:** Python 3.13 z wykorzystaniem frameworka Scrapy. Zarządzanie zależnościami: `uv`.
- **Baza danych:** PostgreSQL w architekturze chmurowej (platforma Supabase), pełniąca rolę Single Source of Truth. Połączenie przez Transaction Pooler (kompatybilność IPv4).
- **Warstwa prezentacji (Frontend):** biblioteka Streamlit, udostępniająca interaktywny dashboard analityczny.
- **Moduł AI / NLP (Future Work):** docelowo wykorzystanie API modelu językowego do zapytań w języku naturalnym (Text-to-SQL). W niniejszej fazie moduł nie jest implementowany; przygotowano natomiast warstwę bezpieczeństwa (rola `ai_read_only`) umożliwiającą jego bezpieczne wdrożenie w przyszłości.

## 3. Analiza źródeł danych i Proof of Concept (PoC)

Przeprowadzono proces inżynierii wstecznej (Reverse Engineering) na portalu docelowym przy użyciu narzędzi deweloperskich przeglądarki (DevTools, zakładka Network → XHR).

**Wynik PoC (zweryfikowany empirycznie):**
- Zidentyfikowano ukryty endpoint API serwujący dane w formacie JSON: `POST /api/search/posting` (lista ofert z paginacją), wykorzystujący niestandardowy nagłówek `Content-Type: application/infiniteSearch+json` oraz kryteria wyszukiwania przekazywane w ciele żądania.
- Potwierdzono drugi endpoint: `GET /api/posting/{id}`, zwracający pełne szczegóły oferty, w tym kompletną listę wymagań (`requirements.musts` oraz `requirements.nices`) i szczegółowe widełki wynagrodzeń.
- Ustalono, że lista ofert nie zawiera pełnego zestawu umiejętności (jedynie skrócone „kafelki"), co uzasadnia zastosowanie **architektury dwustopniowej**: pobranie listy, a następnie szczegółów każdej oferty.
- Stwierdzono, że portal ma charakter wielobranżowy (IT, Marketing, HR, Finanse i in.) i nie udostępnia pojedynczego filtra „cała branża IT". W konsekwencji przyjęto **strategię scrapingu per-technologia** — pobieranie po kolejnych, konkretnych technologiach (Python, Java, JavaScript, TypeScript, C#, Go i in.), co zapewnia kontrolowany, czysto informatyczny zakres danych.

**Wniosek:** pobieranie czystego JSON pozwala całkowicie pominąć niewydajne i kruche parsowanie kodu HTML (DOM) za pomocą XPath/CSS, co zwiększa stabilność skryptów i zmniejsza obciążenie sieciowe serwera docelowego.

## 4. Projekt struktury bazodanowej i zapewnienie jakości danych

Zaprojektowano znormalizowany schemat bazy relacyjnej (trzecia postać normalna, 3NF), adresujący kluczowe wyzwania analityczne. Schemat obejmuje cztery tabele: `skill_taxonomy` (taksonomia umiejętności), `companies` (firmy), `job_offers` (oferty) oraz `offer_skills` (relacja N:M między ofertami a umiejętnościami).

- **Separacja typów umów:** wyodrębnienie ofert B2B (kwoty netto na fakturze) od umów o pracę (kwoty brutto) za pomocą atrybutu `contract_type`, co zapobiega zniekształceniom miar statystycznych. Dodatkowo atrybut `salary_period` rejestruje okres rozliczenia (miesięczny/godzinowy), istotny zwłaszcza dla kontraktów B2B.
- **Mechanizm UPSERT i deduplikacja:** zastosowanie klauzuli `ON CONFLICT DO UPDATE` w PostgreSQL w oparciu o unikalny klucz kompozytowy (`source_portal` + `external_id`). Rozwiązuje to problem duplikatów — przy ponownym uruchomieniu skryptu liczba rekordów nie rośnie, aktualizowany jest jedynie czas ostatniej widoczności oferty.
- **Soft Delete:** ogłoszenia usunięte z portali nie są kasowane, lecz oznaczane flagą `is_active = FALSE`. Umożliwia to późniejsze wyliczenie wskaźnika Time-to-Fill (czasu zamknięcia rekrutacji).
- **Normalizacja umiejętności:** surowe nazwy technologii pozyskiwane z ofert są mapowane na nazwy znormalizowane (`raw_name` → `standardized_name`), co eliminuje duplikaty typu „Postgres" / „PostgreSQL" i zapewnia wiarygodność analiz kompetencyjnych.
- **Rozróżnienie wymagań:** relacja `offer_skills` rejestruje typ wymagania (`requirement_type`: must/nice), co pozwala odróżnić kompetencje obowiązkowe od mile widzianych.

## 5. Metodyka analityczna

Zaprojektowano trzy główne miary analityczne, ukierunkowane na użyteczność dla działów HR:

1. **Benchmark wynagrodzeń (Salary Explorer):** mediana oraz rozstęp międzykwartylowy (P25/P75) wynagrodzeń w podziale na poziom doświadczenia i typ umowy. Zastosowanie mediany (a nie średniej) wynika ze skośności rozkładu widełek płacowych. Miarą bazową jest punkt środkowy widełek oferty.
2. **Skill Premium:** analiza wpływu poszczególnych umiejętności na medianę wynagrodzenia (porównanie median ofert zawierających daną technologię względem ofert jej pozbawionych). Operacyjnie realizuje to teorię zbiorów (część wspólna zbioru ofert z daną umiejętnością i zbioru ofert z górnego kwartyla płac).
3. **Skill Gap / Demand:** ranking najczęściej wymaganych umiejętności w podziale na poziomy doświadczenia (Junior/Mid/Senior), obrazujący ścieżkę rozwoju kompetencji i lukę między poziomami.

## 6. Identyfikacja i mitygacja ryzyk

- **Zabezpieczenia anty-scrapingowe:** zastosowano podejście „Polite Scraping" — `DOWNLOAD_DELAY` na poziomie 2,5 s (podwyższone ze względu na dwustopniową architekturę spidera), mechanizm AutoThrottle oraz symulację realistycznego nagłówka `User-Agent`. Minimalizuje to ryzyko blokady IP (błąd 403/429). Świadomie ograniczono również wielkość próby (scraping reprezentatywnej próbki zamiast pełnej populacji ofert), co skraca czas pobierania i dodatkowo zmniejsza obciążenie serwera.
- **Heterogeniczność źródeł (multi-portal):** każdy portal udostępnia dane w odmiennym formacie JSON. Ryzyko mityguje wzorzec wspólnego obiektu docelowego (`JobOfferItem`) — osobny pająk per portal mapuje dane do jednolitej struktury, izolując logikę specyficzną dla źródła.
- **Bezpieczeństwo modułu Text-to-SQL (Future Work):** aby zapobiec atakom typu SQL Injection ze strony modelu językowego, w PostgreSQL przygotowano odrębną rolę `ai_read_only` z uprawnieniami wyłącznie do odczytu (`SELECT`), bez praw do operacji `INSERT`/`UPDATE`/`DELETE`/`DROP`. Hasło roli przechowywane jest w zmiennych środowiskowych (`.env`), nie w kodzie.
- **Ochrona danych wrażliwych:** plik `.env` z poświadczeniami do bazy jest wykluczony z repozytorium (`.gitignore`); w kodzie nie występują zahardkodowane hasła ani klucze.

## 7. Harmonogram realizacji

Prace zaplanowano w horyzoncie dwutygodniowym, z podziałem na fazy zgodne ze strukturą WBS:

- **Tydzień 1:** utworzenie struktur bazodanowych (DDL) w Supabase, implementacja dwustopniowego pająka Scrapy dla portalu podstawowego (NoFluffJobs), budowa warstwy Data Pipeline (walidacja, normalizacja, zapis logiką UPSERT).
- **Tydzień 2:** dołączenie drugiego portalu (JustJoin.it) z mapowaniem do wspólnego obiektu danych, bootstrap słownika umiejętności, pełny scrape reprezentatywnej próbki, budowa dashboardu analitycznego w Streamlit (trzy miary HR) oraz finalizacja dokumentacji.

## 8. Status realizacji (na moment sporządzenia raportu)

Ukończono fazę fundamentów: skonfigurowano środowisko (`uv`, Python 3.13) oraz bazę danych w chmurze Supabase wraz z wdrożeniem znormalizowanego schematu (cztery tabele). Przeprowadzono i zweryfikowano Proof of Concept dla portalu NoFluffJobs (oba endpointy API). Opracowano dokumentację projektową oraz zestaw reguł jakości kodu (standardy scrapingu, bazy danych i dokumentacji). Kolejnym etapem jest implementacja warstwy ekstrakcji (pająki Scrapy).

---

*Dokument sporządzono w ramach fazy planowania i architektury projektu „SkillGap Monitor". Indeks: 233651.*
