-- Migration: 003_clean_justjoin_salary
-- Autor: Mateusz Elżbieciak
-- Data: 2026-06-05
-- Opis: Czyści błędne wynagrodzenia z JustJoin wynikające z niespójnego pola 'unit'.
--       1) Miesięczne B2B < 8000 PLN to dniówki/stawki błędnie zapisane — NULL.
--       2) Godzinowe > 500 PLN to faktycznie kwoty miesięczne — przełącz na month.

UPDATE job_offers
SET salary_min = NULL, salary_max = NULL
WHERE source_portal = 'justjoin'
  AND salary_period = 'month'
  AND contract_type = 'b2b'
  AND (salary_min + salary_max) / 2.0 < 8000;

UPDATE job_offers
SET salary_period = 'month'
WHERE source_portal = 'justjoin'
  AND salary_period = 'hour'
  AND (salary_min + salary_max) / 2.0 > 500;