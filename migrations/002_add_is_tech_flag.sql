-- Migration: 002_add_is_tech_flag
-- Autor: Mateusz Elżbieciak
-- Data: 2026-06-05
-- Opis: Dodaje flagę is_tech do skill_taxonomy i oznacza nie-technologie
--       (soft skille, metodyki, zarządzanie, kompetencje projektowe) jako FALSE.
--       Analityka Skill Premium / Skill Gap filtruje WHERE is_tech = TRUE.

ALTER TABLE skill_taxonomy
ADD COLUMN IF NOT EXISTS is_tech BOOLEAN DEFAULT TRUE;

UPDATE skill_taxonomy SET is_tech = FALSE
WHERE standardized_name IN (
    'Account Management','Agile','Agile methodologies','Agile methodology',
    'Agile/Scrum','AgilePM','Analytical skills','Asset management','Budget Management',
    'Business Analysis','Business management','Business process management',
    'Change Management','Collaboration skills','Communication',
    'communication and collaboration skills','Communication skills','contract management',
    'Cost management','Data analysis','Delivery Management','Design Thinking',
    'DevOps Agile/Scrum','Financial Management','Gap analysis','Incident management',
    'Internal Communication','Inventory Management','Leadership skills','Management',
    'Mentoring','Mentorship and coaching','Negotiation skills',
    'Presentation and communication','Problem solving','Problem-Solving','Process analysis',
    'Product Management','Project Management','Project Management Professional (PMP)',
    'Project Portfolio Management (PPM)','Quality Management','release management',
    'Resource Management','risk analysis','Risk Management','Scrum','Scrum Master',
    'Service Management','Software Development Management','Stakeholder Collaboration',
    'Stakeholder Management','supplier management','Supply chain management',
    'System Analysis','systems analysis','Team Management','Transition Management',
    'architektura systemów IT','Business Continuity Management System (BCMS)',
    'Deployment Management','Document Management','Product design','Graphic design',
    'UI Design','UX design','Visual Design','Design','Interaction design',
    'User-centered design'
);