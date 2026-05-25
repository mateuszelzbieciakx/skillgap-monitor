---
name: documenting-python-code
description: Documents and enforces Python code standards for the SkillGap Monitor project — PEP8 compliance, type hints on all functions, Google-style docstrings (Args/Returns/Raises), inline comments explaining Set Theory operations used in the skill-gap engine, and an automated authorship header (Mateusz Elżbieciak, indeks 233651, UEK). Use this skill whenever the user writes a new module, asks to document/comment code, finishes a function or class, or when reviewing code for style and readability — even if they only ask to "clean up" or "add comments". Apply proactively to any newly generated main file in the project.
---

# Dokumentacja i standardy kodu Python

Skill pełni rolę Technical Writera i strażnika standardów języka dla projektu SkillGap Monitor. Cel: kod ma być wzorcowy (Clean Code), czytelny dla inżyniera i spójnie udokumentowany — to projekt portfolio i praca zaliczeniowa UEK.

## Kiedy stosować

- Tworzenie nowego modułu/pliku głównego
- Kończenie funkcji lub klasy (dodanie docstringów, type hints)
- Prośba o komentarze, "uporządkowanie", poprawę czytelności
- Przegląd kodu pod kątem PEP8 i stylu
- Dokumentowanie logiki biznesowej (zwłaszcza operacji na zbiorach)

## Reguła 1: PEP8 i type hints (twarda)

- Zgodność z PEP8: nazewnictwo (`snake_case` dla funkcji/zmiennych, `PascalCase` dla klas), długość linii, importy uporządkowane
- Nazwy zmiennych czytelne i **angielskie** (kod), mimo że dokumentacja opisowa jest po polsku
- **Type hints obowiązkowe** dla sygnatur funkcji (argumenty i wartość zwracana)

```python
# ŹLE — brak typów, nazwa nieczytelna
def calc(d, x):
    ...

# DOBRZE — typy, czytelna nazwa
def compute_skill_gap(required: set[str], owned: set[str]) -> set[str]:
    ...
```

## Reguła 2: Docstringi w stylu Google (twarda)

Każda funkcja i klasa publiczna ma docstring z sekcjami `Args`, `Returns`, `Raises` (te, które dotyczą). Język opisu: polski, techniczny, zwięzły.

```python
def compute_skill_gap(required: set[str], owned: set[str]) -> set[str]:
    """Wyznacza lukę kompetencyjną kandydata względem wymagań rynku.

    Args:
        required: Zbiór umiejętności wymaganych przez oferty.
        owned: Zbiór umiejętności posiadanych przez kandydata.

    Returns:
        Zbiór umiejętności brakujących (różnica zbiorów).

    Raises:
        ValueError: Gdy zbiór wymagań jest pusty.
    """
    if not required:
        raise ValueError("Zbiór wymagań nie może być pusty")
    # Różnica zbiorów (Set Theory): wymagane \ posiadane = luka kompetencyjna
    return required - owned
```

## Reguła 3: Komentarze do operacji na zbiorach (Set Theory)

Silnik luk kompetencyjnych opiera się na teorii zbiorów. Każdą nietrywialną operację (różnica, część wspólna, suma, podzbiór) opatruj komentarzem `#` wyjaśniającym **sens biznesowy**, nie tylko operację:

```python
# Część wspólna: skille kandydata realnie poszukiwane na rynku
matched = owned & required
# Różnica: czego kandydatowi brakuje do profilu rynkowego
gap = required - owned
```

To kluczowy element oceny projektu — czytelnik ma rozumieć logikę bez czytania całego kodu.

## Reguła 4: Nagłówek autorski (automatyczny)

Na górze każdego nowo generowanego **głównego pliku** projektu wstawiaj nagłówek:

```python
# Projekt: SkillGap Monitor
# Autor: Mateusz Elżbieciak (Indeks: 233651)
# Uczelnia: Uniwersytet Ekonomiczny w Krakowie (UEK)
```

Nie powielaj nagłówka w pomocniczych plikach/fragmentach — tylko w głównych modułach. Jeśli w jakimkolwiek dokumencie lub kodzie pojawi się nazwa "Piotr Henzolt", zastąp ją "Mateusz Elżbieciak".

## Reguła 5: Czytelność dokumentacji

- Pliki `.md` i komentarze: język techniczny, zwięzły, polski
- Unikaj komentarzy oczywistych ("zwiększ i o 1"); komentuj *dlaczego*, nie *co*
- Złożone bloki poprzedzaj krótkim wprowadzeniem w 1-2 zdaniach

## Format odpowiedzi

Zwracaj kompletny, poprawnie sformatowany blok kodu ze zintegrowaną dokumentacją (docstringi + komentarze + nagłówek, jeśli to plik główny). Przy przeglądzie najpierw lista braków, potem poprawiona wersja.
