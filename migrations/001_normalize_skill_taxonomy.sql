-- Migration: 001_normalize_skill_taxonomy
-- Autor: Mateusz Elżbieciak
-- Data: 2026-06-05
-- Opis: Normalizacja kolumny standardized_name w skill_taxonomy.
--       Dla duplikatów (ten sam raw_name w różnym case) ustawia kanoniczną
--       formę jako standardized_name. Kanoniczna forma = wariant najczęściej
--       występujący w offer_skills.

UPDATE skill_taxonomy st
SET standardized_name = canonical.best_name
FROM (
    SELECT DISTINCT ON (LOWER(raw_name))
        LOWER(raw_name) as normalized,
        st2.raw_name as best_name
    FROM skill_taxonomy st2
    LEFT JOIN offer_skills os ON st2.id = os.skill_id
    GROUP BY LOWER(st2.raw_name), st2.raw_name
    ORDER BY LOWER(st2.raw_name), COUNT(os.skill_id) DESC
) canonical
WHERE LOWER(st.raw_name) = canonical.normalized;