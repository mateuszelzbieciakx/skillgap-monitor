-- Migration: 004_clean_all_salary_bugs
-- Czyszczenie istniejących rekordów wg tych samych progów co ValidationPipeline.
-- Progi: B2B month >= 6000, pozostałe month >= 3000, month <= 150000,
--        hour 20-500. Poza zakresem → NULL (soft, nie usuwamy oferty).

-- 1. Miesięczne B2B poniżej 6000 PLN
UPDATE job_offers
SET salary_min = NULL, salary_max = NULL
WHERE salary_period = 'month'
  AND contract_type = 'b2b'
  AND (salary_min + salary_max) / 2.0 < 6000;

-- 2. Miesięczne pozostałe (uop/uod/other) poniżej 3000 PLN
UPDATE job_offers
SET salary_min = NULL, salary_max = NULL
WHERE salary_period = 'month'
  AND contract_type IN ('uop', 'uod', 'other')
  AND (salary_min + salary_max) / 2.0 < 3000;

-- 3. Miesięczne powyżej sufitu 150000 PLN
UPDATE job_offers
SET salary_min = NULL, salary_max = NULL
WHERE salary_period = 'month'
  AND (salary_min + salary_max) / 2.0 > 150000;

-- 4. Godzinowe poza zakresem 20-500 PLN/h
UPDATE job_offers
SET salary_min = NULL, salary_max = NULL
WHERE salary_period = 'hour'
  AND ((salary_min + salary_max) / 2.0 < 20 OR (salary_min + salary_max) / 2.0 > 500);

-- 5. Wartości ujemne lub zerowe (dowolny period)
UPDATE job_offers
SET salary_min = NULL, salary_max = NULL
WHERE salary_min <= 0 OR salary_max <= 0;

-- 6. Odwrócone widełki — zamiana miejscami (nie zerujemy, naprawiamy)
UPDATE job_offers
SET salary_min = salary_max, salary_max = salary_min
WHERE salary_min > salary_max;
