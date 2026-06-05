# Projekt: SkillGap Monitor
# Autor: Mateusz Elżbieciak (Indeks: 233651)
# Uczelnia: Uniwersytet Ekonomiczny w Krakowie (UEK)

"""Dashboard analityczny SkillGap Monitor.

Streamlit dashboard z trzema zakładkami:
1. Salary Explorer — mediana i percentyle wynagrodzeń per doświadczenie × umowa
2. Skill Premium — top 20 skilli podnoszących medianę wynagrodzenia
3. Skill Gap — top 15 najczęściej wymaganych umiejętności per poziom

Warstwa wizualna inspirowana stroną Apple — dark theme, minimalistyczny,
dużo przestrzeni, czysta typografia, subtelne akcenty.
"""

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


# ==============================================================================
# CUSTOM CSS — Dark theme inspirowany Apple
# ==============================================================================
# Globalne style: ciemne tło (#0a0a0f), karty (#16161f), akcent Apple Blue (#0a84ff)
# Font stack: SF Pro Display / Inter / system sans-serif
# Ukrycie domyślnego menu Streamlit i stopki
# Większe paddingi, max-width kontenera ~1100px wyśrodkowany
# ==============================================================================

CUSTOM_CSS = """
<style>
/* Import fontów */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

/* Zmienne kolorystyczne */
:root {
    --bg-primary: #0a0a0f;
    --bg-card: #16161f;
    --text-primary: #e8e8ec;
    --text-secondary: #98989f;
    --accent: #0a84ff;
    --border: #2a2a35;
}

/* Globalne tło */
.stApp {
    background-color: var(--bg-primary);
    color: var(--text-primary);
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", sans-serif;
}

/* Ukryj menu Streamlit i stopkę */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {
    background: transparent;
}

/* Kontener główny — max-width 1100px, wyśrodkowany */
.block-container {
    max-width: 1100px;
    padding-top: 3rem;
    padding-bottom: 3rem;
}

/* Tytuł główny — duży, lekki, letter-spacing */
h1 {
    font-size: 3.5rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    color: var(--text-primary);
    margin-bottom: 0.5rem;
}

/* Nagłówki sekcji */
h2, h3 {
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--text-primary);
}

/* Paragraf */
p {
    color: var(--text-secondary);
    line-height: 1.6;
}

/* Karty metryk — border, zaokrąglone rogi, padding */
div[data-testid="metric-container"] {
    background-color: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
}

div[data-testid="stMetricValue"] {
    font-size: 2rem;
    font-weight: 600;
    color: var(--accent);
}

div[data-testid="stMetricLabel"] {
    color: var(--text-secondary);
    font-size: 0.875rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Zakładki */
.stTabs [data-baseweb="tab-list"] {
    gap: 1rem;
    background-color: transparent;
    border-bottom: 1px solid var(--border);
}

.stTabs [data-baseweb="tab"] {
    background-color: transparent;
    color: var(--text-secondary);
    font-weight: 500;
    padding: 0.75rem 1.5rem;
    border-radius: 8px 8px 0 0;
}

.stTabs [aria-selected="true"] {
    background-color: var(--bg-card);
    color: var(--accent);
}

/* Selectbox */
div[data-baseweb="select"] {
    background-color: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
}

/* Dataframe */
.stDataFrame {
    border: 1px solid var(--border);
    border-radius: 8px;
}

/* Warning box */
.stAlert {
    background-color: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text-primary);
}

/* Footer własny */
.footer-custom {
    text-align: center;
    color: var(--text-secondary);
    font-size: 0.85rem;
    margin-top: 4rem;
    padding-top: 2rem;
    border-top: 1px solid var(--border);
}

</style>
"""


# ==============================================================================
# PLOTLY TEMPLATE — wspólny dla wszystkich wykresów
# ==============================================================================

PLOTLY_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        font=dict(
            family="-apple-system, BlinkMacSystemFont, 'SF Pro Display', Inter, sans-serif",
            size=14,
            color="#e8e8ec"
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            zerolinecolor="rgba(255,255,255,0.1)",
            color="#e8e8ec"
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            zerolinecolor="rgba(255,255,255,0.1)",
            color="#e8e8ec"
        ),
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="#16161f",
            font_size=13,
            font_family="-apple-system, BlinkMacSystemFont, 'SF Pro Display', Inter",
            bordercolor="#2a2a35"
        ),
        title=dict(
            font=dict(size=20, color="#e8e8ec"),
            x=0.05,
            xanchor="left"
        ),
        colorway=["#0a84ff", "#30d158", "#ff375f", "#ffcc00", "#bf5af2", "#00c7be"]
    )
)

# Kolory per typ umowy — spójne przez wszystkie wykresy
CONTRACT_COLORS: dict[str, str] = {
    "b2b": "#0a84ff",
    "uop": "#30d158",
    "uod": "#ffcc00",
    "other": "#bf5af2",
}

LEVEL_ORDER: list[str] = ["junior", "mid", "senior", "lead"]

# Kolejność typów umów na wykresie słupkowym (uop przed b2b)
CONTRACT_PLOT_ORDER: list[str] = ["uop", "uod", "b2b", "other"]


# ==============================================================================
# FUNKCJE ZAPYTAŃ SQL
# ==============================================================================

@st.cache_data(ttl=300, show_spinner=False)
def query_overview_metrics() -> dict[str, int]:
    """Pobiera metryki przeglądowe dla kart na stronie głównej.

    Metryki nie reagują na filtry — przedstawiają stan całego zbioru danych.

    Returns:
        Słownik z kluczami: total_offers, total_companies, total_portals.
    """
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    try:
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM job_offers WHERE is_active = TRUE")
        total_offers: int = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM companies")
        total_companies: int = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(DISTINCT source_portal) FROM job_offers WHERE is_active = TRUE"
        )
        total_portals: int = cur.fetchone()[0]

        cur.close()
        return {
            "total_offers": total_offers,
            "total_companies": total_companies,
            "total_portals": total_portals,
        }
    finally:
        conn.close()


@st.cache_data(ttl=300, show_spinner=False)
def query_salary_stats(
    levels: list[str],
    contracts: list[str],
    portals: list[str],
    salary_required: bool,
    currency: str = "PLN",
) -> pd.DataFrame:
    """Pobiera statystyki wynagrodzeń per experience_level × contract_type.

    Args:
        levels: Filtr poziomów doświadczenia (ANY).
        contracts: Filtr typów umów (ANY).
        portals: Filtr portali źródłowych (ANY).
        salary_required: Gdy True, wyklucza oferty bez widełek.
        currency: Waluta (domyślnie PLN).

    Returns:
        DataFrame z kolumnami: experience_level, contract_type,
        count, p25, median, p75, min_salary, max_salary.
        Wartości wynagrodzeń jako float.
    """
    salary_clause = (
        "AND salary_min IS NOT NULL AND salary_max IS NOT NULL"
        if salary_required else ""
    )
    query = f"""
        SELECT
            experience_level,
            contract_type,
            COUNT(*) AS count,
            PERCENTILE_CONT(0.25) WITHIN GROUP (
                ORDER BY (salary_min + salary_max) / 2.0
            ) AS p25,
            PERCENTILE_CONT(0.50) WITHIN GROUP (
                ORDER BY (salary_min + salary_max) / 2.0
            ) AS median,
            PERCENTILE_CONT(0.75) WITHIN GROUP (
                ORDER BY (salary_min + salary_max) / 2.0
            ) AS p75,
            MIN((salary_min + salary_max) / 2.0) AS min_salary,
            MAX((salary_min + salary_max) / 2.0) AS max_salary
        FROM job_offers
        WHERE is_active = TRUE
          AND salary_min IS NOT NULL
          AND salary_max IS NOT NULL
          AND currency = %(currency)s
          AND salary_period = 'month'
          AND experience_level = ANY(%(levels)s)
          AND contract_type = ANY(%(contracts)s)
          AND source_portal = ANY(%(portals)s)
          {salary_clause}
        GROUP BY experience_level, contract_type
        HAVING COUNT(*) >= 3
        ORDER BY experience_level, contract_type
    """
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    try:
        return pd.read_sql_query(
            query, conn,
            params={
                "currency": currency,
                "levels": levels,
                "contracts": contracts,
                "portals": portals,
            },
        )
    finally:
        conn.close()


@st.cache_data(ttl=300, show_spinner=False)
def query_skill_premium(
    levels: list[str],
    contracts: list[str],
    portals: list[str],
    salary_required: bool,
    top_n: int = 20,
    currency: str = "PLN",
) -> pd.DataFrame:
    """Oblicza skill premium — różnicę median wynagrodzeń ofert ze/bez danego skilla.

    Args:
        levels: Filtr poziomów doświadczenia (ANY).
        contracts: Filtr typów umów (ANY).
        portals: Filtr portali źródłowych (ANY).
        salary_required: Gdy True, wyklucza oferty bez widełek.
        top_n: Liczba top skilli do zwrócenia.
        currency: Waluta (domyślnie PLN).

    Returns:
        DataFrame z kolumnami: skill_name, median_with_skill,
        median_without_skill, premium. Wartości jako float.
    """
    query = f"""
        WITH base_offers AS (
            SELECT id,
                   (salary_min + salary_max) / 2.0 AS midpoint
            FROM job_offers
            WHERE is_active = TRUE
              AND salary_min IS NOT NULL
              AND salary_max IS NOT NULL
              AND currency = %(currency)s
              AND salary_period = 'month'
              AND experience_level = ANY(%(levels)s)
              AND contract_type = ANY(%(contracts)s)
              AND source_portal = ANY(%(portals)s)
        ),
        overall_median AS (
            SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (
                ORDER BY midpoint
            ) AS median_salary
            FROM base_offers
        ),
        skill_counts AS (
            SELECT skill_id, COUNT(*) AS offer_count
            FROM offer_skills os
            JOIN base_offers bo ON os.offer_id = bo.id
            GROUP BY skill_id
            HAVING COUNT(*) >= 10
        ),
        skill_medians AS (
            SELECT
                st.standardized_name AS skill_name,
                PERCENTILE_CONT(0.5) WITHIN GROUP (
                    ORDER BY bo.midpoint
                ) AS median_with_skill
            FROM offer_skills os
            JOIN skill_taxonomy st ON os.skill_id = st.id
            JOIN base_offers bo ON os.offer_id = bo.id
            WHERE os.skill_id IN (SELECT skill_id FROM skill_counts)
              AND st.is_tech = TRUE
            GROUP BY st.standardized_name
        )
        SELECT
            sm.skill_name,
            sm.median_with_skill,
            om.median_salary AS median_without_skill,
            (sm.median_with_skill - om.median_salary) AS premium
        FROM skill_medians sm
        CROSS JOIN overall_median om
        ORDER BY premium DESC
        LIMIT %(top_n)s
    """
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    try:
        return pd.read_sql_query(
            query, conn,
            params={
                "currency": currency,
                "levels": levels,
                "contracts": contracts,
                "portals": portals,
                "top_n": top_n,
            },
        )
    finally:
        conn.close()


@st.cache_data(ttl=300, show_spinner=False)
def query_skill_gap(
    levels: list[str],
    contracts: list[str],
    portals: list[str],
    salary_required: bool,
    top_n: int = 15,
) -> pd.DataFrame:
    """Pobiera top N skilli i rozkład must/nice dla każdego z nich.

    Dwuetapowe zapytanie: najpierw wyłania top N skilli (po sumie must+nice),
    następnie pobiera osobne liczby must i nice. Zapobiega znikaniu 'nice'
    przy globalnym LIMIT.

    Args:
        levels: Filtr poziomów doświadczenia (ANY).
        contracts: Filtr typów umów (ANY).
        portals: Filtr portali źródłowych (ANY).
        salary_required: Gdy True, wyklucza oferty bez widełek.
        top_n: Liczba top skilli do wyłonienia.

    Returns:
        DataFrame z kolumnami: skill_name, requirement_type, count.
    """
    salary_clause = (
        "AND jo.salary_min IS NOT NULL AND jo.salary_max IS NOT NULL"
        if salary_required else ""
    )
    query = f"""
        WITH top_skills AS (
            SELECT st.standardized_name AS skill_name
            FROM offer_skills os
            JOIN skill_taxonomy st ON os.skill_id = st.id
            JOIN job_offers jo ON os.offer_id = jo.id
            WHERE jo.is_active = TRUE
              AND jo.experience_level = ANY(%(levels)s)
              AND jo.contract_type = ANY(%(contracts)s)
              AND jo.source_portal = ANY(%(portals)s)
              {salary_clause}
              AND st.is_tech = TRUE
            GROUP BY st.standardized_name
            ORDER BY COUNT(*) DESC
            LIMIT %(top_n)s
        )
        SELECT
            st.standardized_name AS skill_name,
            os.requirement_type,
            COUNT(*) AS count
        FROM offer_skills os
        JOIN skill_taxonomy st ON os.skill_id = st.id
        JOIN job_offers jo ON os.offer_id = jo.id
        WHERE jo.is_active = TRUE
          AND jo.experience_level = ANY(%(levels)s)
          AND jo.contract_type = ANY(%(contracts)s)
          AND jo.source_portal = ANY(%(portals)s)
          {salary_clause}
          AND st.standardized_name IN (SELECT skill_name FROM top_skills)
          AND st.is_tech = TRUE
        GROUP BY st.standardized_name, os.requirement_type
        ORDER BY skill_name, requirement_type
    """
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    try:
        return pd.read_sql_query(
            query, conn,
            params={
                "levels": levels,
                "contracts": contracts,
                "portals": portals,
                "top_n": top_n,
            },
        )
    finally:
        conn.close()


# ==============================================================================
# GŁÓWNA FUNKCJA DASHBOARD
# ==============================================================================

def main() -> None:
    """Główna funkcja uruchamiająca dashboard Streamlit."""
    st.set_page_config(
        page_title="SkillGap Monitor",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    if not os.getenv("DATABASE_URL"):
        st.error("Brak zmiennej DATABASE_URL. Sprawdź plik .env.")
        return

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # ========================================================================
    # SIDEBAR — globalne filtry
    # ========================================================================

    with st.sidebar:
        st.markdown("## Filtry")

        all_levels = ["junior", "mid", "senior", "lead"]
        levels: list[str] = st.pills(
            "Poziom doświadczenia",
            options=all_levels,
            selection_mode="multi",
            default=all_levels,
        )

        all_contracts = ["b2b", "uop", "uod", "other"]
        contracts: list[str] = st.pills(
            "Typ umowy",
            options=all_contracts,
            selection_mode="multi",
            default=["b2b", "uop"],
        )

        all_portals = ["nofluffjobs", "justjoin"]
        portals: list[str] = st.pills(
            "Portal",
            options=all_portals,
            selection_mode="multi",
            default=all_portals,
        )

        salary_required: bool = st.checkbox(
            "Tylko oferty z wynagrodzeniem",
            value=True,
        )

        with st.expander("ℹ️ O projekcie"):
            st.markdown(
                "**Autor:** Mateusz Elżbieciak  \n"
                "**Źródła danych:** NoFluffJobs, JustJoin.it  \n"
                "**Uczelnia:** Uniwersytet Ekonomiczny w Krakowie (UEK)"
            )

    # ========================================================================
    # NAGŁÓWEK
    # ========================================================================

    st.markdown("<h1>SkillGap Monitor</h1>", unsafe_allow_html=True)
    st.markdown(
        """
        <p style='font-size: 1.25rem; margin-bottom: 2.5rem;'>
        Automatyczna analityka rynku pracy IT — wynagrodzenia, kompetencje, trendy.
        </p>
        """,
        unsafe_allow_html=True,
    )

    # ========================================================================
    # KARTY METRYK — cały zbiór, bez filtrów
    # ========================================================================

    metrics = query_overview_metrics()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Oferty pracy", f"{metrics['total_offers']:,}")
    with col2:
        st.metric("Firmy", f"{metrics['total_companies']:,}")
    with col3:
        st.metric("Portale", f"{metrics['total_portals']:,}")

    st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)

    # ========================================================================
    # ZAKŁADKI ANALITYCZNE
    # ========================================================================

    tab1, tab2, tab3 = st.tabs([
        "💰 Salary Explorer",
        "🚀 Skill Premium",
        "📈 Skill Gap",
    ])

    # ------------------------------------------------------------------------
    # TAB 1: Salary Explorer
    # ------------------------------------------------------------------------
    with tab1:
        st.markdown("### Rozkład wynagrodzeń")
        st.markdown(
            "<p style='margin-bottom: 1.5rem;'>"
            "Mediana i percentyle (P25/P75) per poziom doświadczenia i typ umowy."
            "</p>",
            unsafe_allow_html=True,
        )

        df_salary = query_salary_stats(levels, contracts, portals, salary_required)

        if df_salary.empty:
            st.warning("⚠️ Brak danych dla wybranych filtrów.")
        else:
            fig = go.Figure()

            present_contracts = df_salary["contract_type"].unique().tolist()
            ordered_contracts = [c for c in CONTRACT_PLOT_ORDER if c in present_contracts]
            ordered_contracts += [c for c in present_contracts if c not in CONTRACT_PLOT_ORDER]

            for contract in ordered_contracts:
                df_ct = (
                    df_salary[df_salary["contract_type"] == contract]
                    .set_index("experience_level")
                    .reindex(LEVEL_ORDER)
                    .dropna(subset=["median"])
                )
                if df_ct.empty:
                    continue

                x_vals = df_ct.index.tolist()
                medians = df_ct["median"].tolist()
                p25s = df_ct["p25"].tolist()
                p75s = df_ct["p75"].tolist()

                error_plus = [p75 - med for med, p75 in zip(medians, p75s)]
                error_minus = [med - p25 for med, p25 in zip(medians, p25s)]

                custom = [[int(round(p)), int(round(q))] for p, q in zip(p25s, p75s)]

                fig.add_trace(go.Bar(
                    name=contract.upper(),
                    x=x_vals,
                    y=[int(round(m)) for m in medians],
                    error_y=dict(
                        type="data",
                        array=[int(round(e)) for e in error_plus],
                        arrayminus=[int(round(e)) for e in error_minus],
                        visible=True,
                        color="rgba(255,255,255,0.45)",
                        thickness=1.5,
                        width=6,
                    ),
                    marker_color=CONTRACT_COLORS.get(contract, "#98989f"),
                    customdata=custom,
                    hovertemplate=(
                        "Poziom: %{x}"
                        f" | Umowa: {contract.upper()}"
                        " | Mediana: %{y:,} PLN"
                        " | P25: %{customdata[0]:,}"
                        " | P75: %{customdata[1]:,}"
                        "<extra></extra>"
                    ),
                ))

            fig.update_layout(
                template=PLOTLY_TEMPLATE,
                barmode="group",
                title="",
                xaxis=dict(
                    categoryorder="array",
                    categoryarray=LEVEL_ORDER,
                    title="",
                ),
                yaxis=dict(
                    title="PLN",
                    tickformat=",d",
                ),
                legend=dict(
                    title="Typ umowy",
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                ),
                height=500,
                margin=dict(l=60, r=20, t=60, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("#### Szczegóły statystyk")
            df_display = df_salary.copy()
            for col in ["p25", "median", "p75", "min_salary", "max_salary"]:
                df_display[col] = df_display[col].apply(
                    lambda x: int(round(x)) if pd.notna(x) else None
                )
            df_display = df_display[[
                "experience_level", "contract_type", "count",
                "min_salary", "p25", "median", "p75", "max_salary"
            ]]
            df_display.columns = [
                "Poziom", "Umowa", "Liczba ofert", "Min", "P25", "Mediana", "P75", "Max"
            ]
            st.dataframe(df_display, use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------------
    # TAB 2: Skill Premium
    # ------------------------------------------------------------------------
    with tab2:
        st.markdown("### Skill Premium")

        df_premium = query_skill_premium(levels, contracts, portals, salary_required, top_n=20)

        if df_premium.empty:
            st.warning("⚠️ Brak danych dla wybranych filtrów.")
        else:
            df_premium_sorted = df_premium.sort_values("premium", ascending=True)
            bar_colors = [
                "#30d158" if v >= 0 else "#ff375f"
                for v in df_premium_sorted["premium"]
            ]
            premium_ints = [int(round(v)) for v in df_premium_sorted["premium"]]

            fig = go.Figure(go.Bar(
                x=premium_ints,
                y=df_premium_sorted["skill_name"].tolist(),
                orientation="h",
                marker_color=bar_colors,
                customdata=[[v] for v in premium_ints],
                hovertemplate=(
                    "Skill: %{y} | Wzrost mediany: %{x:+,d} PLN<extra></extra>"
                ),
            ))
            fig.update_layout(
                template=PLOTLY_TEMPLATE,
                title="",
                xaxis=dict(title="Wzrost mediany (PLN)", tickformat=",d"),
                yaxis=dict(title=""),
                showlegend=False,
                height=550,
                margin=dict(l=160, r=20, t=40, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("#### Szczegóły premium")
            df_display = df_premium.copy()
            for col in ["median_with_skill", "median_without_skill", "premium"]:
                df_display[col] = df_display[col].apply(
                    lambda x: int(round(x)) if pd.notna(x) else None
                )
            df_display.columns = [
                "Umiejętność",
                "Mediana (ze skilliem)",
                "Mediana (bez skilla)",
                "Premium",
            ]
            st.dataframe(df_display, use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------------
    # TAB 3: Skill Gap
    # ------------------------------------------------------------------------
    with tab3:
        st.markdown("### Skill Gap")
        st.markdown(
            "<p style='margin-bottom: 1.5rem;'>"
            "Top 15 najczęściej wymaganych umiejętności per poziom doświadczenia."
            "</p>",
            unsafe_allow_html=True,
        )

        df_gap = query_skill_gap(levels, contracts, portals, salary_required, top_n=15)

        if df_gap.empty:
            st.warning("⚠️ Brak danych dla wybranych filtrów.")
        else:
            # Kolejność skilli na osi Y — od najmniej do najbardziej popularnego
            skill_totals = (
                df_gap.groupby("skill_name")["count"]
                .sum()
                .sort_values(ascending=True)
            )
            skill_order = skill_totals.index.tolist()
            chart_height = max(400, len(skill_order) * 55)

            fig = px.bar(
                df_gap,
                x="count",
                y="skill_name",
                color="requirement_type",
                barmode="group",
                orientation="h",
                color_discrete_map={"must": "#0a84ff", "nice": "#30d158"},
                category_orders={"requirement_type": ["nice", "must"]},
                labels={
                    "count": "Liczba ofert",
                    "skill_name": "Umiejętność",
                    "requirement_type": "Typ wymagania",
                },
                custom_data=["skill_name", "requirement_type", "count"],
                height=chart_height,
            )
            fig.update_traces(
                hovertemplate=(
                    "Skill: %{customdata[0]}"
                    " | Typ: %{customdata[1]}"
                    " | Ofert: %{customdata[2]:,d}"
                    "<extra></extra>"
                )
            )
            fig.update_layout(
                template=PLOTLY_TEMPLATE,
                title="",
                xaxis=dict(title="Liczba ofert", tickformat=",d"),
                yaxis=dict(
                    title="",
                    categoryorder="array",
                    categoryarray=skill_order,
                ),
                bargap=0.4,
                bargroupgap=0.15,
                legend=dict(
                    title="Typ wymagania",
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                ),
                margin=dict(l=160, r=20, t=60, b=40),
            )
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("#### Szczegóły wymagań")
            df_display = df_gap[["skill_name", "requirement_type", "count"]].copy()
            df_display.columns = ["Umiejętność", "Typ wymagania", "Liczba ofert"]
            st.dataframe(df_display, use_container_width=True, hide_index=True)

    # ========================================================================
    # STOPKA
    # ========================================================================

    st.caption("Autor projektu: Mateusz Elżbieciak")


if __name__ == "__main__":
    main()
