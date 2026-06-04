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
from typing import Any

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
header {visibility: hidden;}

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


# ==============================================================================
# FUNKCJE ZAPYTAŃ SQL (bez zmian logiki)
# ==============================================================================

@st.cache_data(ttl=300)
def query_overview_metrics() -> dict[str, int | float]:
    """Pobiera metryki przeglądowe dla kart na stronie głównej.

    Returns:
        Słownik z metrykami: total_offers, total_companies, median_b2b_senior, total_skills.
    """
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    try:
        cur = conn.cursor()

        # Liczba aktywnych ofert
        cur.execute("SELECT COUNT(*) FROM job_offers WHERE is_active = TRUE")
        total_offers = cur.fetchone()[0]

        # Liczba firm
        cur.execute("SELECT COUNT(*) FROM companies")
        total_companies = cur.fetchone()[0]

        # Mediana B2B Senior PLN
        cur.execute("""
            SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (
                ORDER BY (salary_min + salary_max) / 2.0
            )
            FROM job_offers
            WHERE is_active = TRUE
              AND contract_type = 'b2b'
              AND experience_level = 'senior'
              AND currency = 'PLN'
              AND salary_min IS NOT NULL
              AND salary_max IS NOT NULL
        """)
        result = cur.fetchone()
        median_b2b_senior = int(result[0]) if result and result[0] else 0

        # Liczba unikalnych technologii
        cur.execute("SELECT COUNT(DISTINCT standardized_name) FROM skill_taxonomy")
        total_skills = cur.fetchone()[0]

        cur.close()
        return {
            "total_offers": total_offers,
            "total_companies": total_companies,
            "median_b2b_senior": median_b2b_senior,
            "total_skills": total_skills
        }
    finally:
        conn.close()


@st.cache_data(ttl=300)
def query_salary_stats(
    contract_filter: str | None = None,
    currency_filter: str = "PLN"
) -> pd.DataFrame:
    """Pobiera statystyki wynagrodzeń per experience_level × contract_type.

    Args:
        contract_filter: Typ umowy do filtrowania (None = wszystkie).
        currency_filter: Waluta (domyślnie PLN).

    Returns:
        DataFrame z kolumnami: experience_level, contract_type, count, p25, median, p75.
    """
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    try:
        query = """
        SELECT
            experience_level,
            contract_type,
            COUNT(*) as count,
            PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY (salary_min + salary_max) / 2.0) as p25,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY (salary_min + salary_max) / 2.0) as median,
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY (salary_min + salary_max) / 2.0) as p75
        FROM job_offers
        WHERE
            is_active = TRUE
            AND salary_min IS NOT NULL
            AND salary_max IS NOT NULL
            AND currency = %s
            AND salary_period = 'month'
        """
        params = [currency_filter]

        if contract_filter and contract_filter != "Wszystkie":
            query += " AND contract_type = %s"
            params.append(contract_filter.lower())

        query += """
        GROUP BY experience_level, contract_type
        HAVING COUNT(*) >= 3
        ORDER BY experience_level, contract_type
        """

        df = pd.read_sql_query(query, conn, params=params)
        return df
    finally:
        conn.close()


@st.cache_data(ttl=300)
def query_skill_premium(top_n: int = 20, currency_filter: str = "PLN") -> pd.DataFrame:
    """Oblicza skill premium — różnicę median wynagrodzeń ze/bez skilla.

    Args:
        top_n: Liczba top skilli do zwrócenia.
        currency_filter: Waluta (domyślnie PLN).

    Returns:
        DataFrame z kolumnami: skill_name, median_with_skill, median_without_skill, premium.
    """
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    try:
        query = """
        WITH skill_counts AS (
            SELECT skill_id, COUNT(*) as offer_count
            FROM offer_skills
            GROUP BY skill_id
            HAVING COUNT(*) >= 10
        ),
        overall_median AS (
            SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (
                ORDER BY (salary_min + salary_max) / 2.0
            ) as median_salary
            FROM job_offers
            WHERE is_active = TRUE
              AND salary_min IS NOT NULL
              AND salary_max IS NOT NULL
              AND currency = %s
              AND salary_period = 'month'
        ),
        skill_medians AS (
            SELECT
                st.standardized_name as skill_name,
                PERCENTILE_CONT(0.5) WITHIN GROUP (
                    ORDER BY (jo.salary_min + jo.salary_max) / 2.0
                ) as median_with_skill
            FROM offer_skills os
            JOIN skill_taxonomy st ON os.skill_id = st.id
            JOIN job_offers jo ON os.offer_id = jo.id
            WHERE os.skill_id IN (SELECT skill_id FROM skill_counts)
              AND jo.is_active = TRUE
              AND jo.salary_min IS NOT NULL
              AND jo.salary_max IS NOT NULL
              AND jo.currency = %s
              AND jo.salary_period = 'month'
            GROUP BY st.standardized_name
        )
        SELECT
            sm.skill_name,
            sm.median_with_skill,
            om.median_salary as median_without_skill,
            (sm.median_with_skill - om.median_salary) as premium
        FROM skill_medians sm
        CROSS JOIN overall_median om
        ORDER BY premium DESC
        LIMIT %s
        """
        df = pd.read_sql_query(query, conn, params=[currency_filter, currency_filter, top_n])
        return df
    finally:
        conn.close()


@st.cache_data(ttl=300)
def query_skill_gap(
    top_n: int = 15,
    experience_filter: str | None = None
) -> pd.DataFrame:
    """Pobiera najczęściej wymagane skille per experience_level × requirement_type.

    Args:
        top_n: Liczba top skilli do zwrócenia.
        experience_filter: Poziom doświadczenia do filtrowania (None = wszystkie).

    Returns:
        DataFrame z kolumnami: skill_name, experience_level, requirement_type, count.
    """
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    try:
        query = """
        SELECT
            st.standardized_name as skill_name,
            jo.experience_level,
            os.requirement_type,
            COUNT(*) as count
        FROM offer_skills os
        JOIN skill_taxonomy st ON os.skill_id = st.id
        JOIN job_offers jo ON os.offer_id = jo.id
        WHERE jo.is_active = TRUE
        """
        params: list[Any] = []

        if experience_filter and experience_filter != "Wszystkie":
            query += " AND jo.experience_level = %s"
            params.append(experience_filter.lower())

        query += """
        GROUP BY st.standardized_name, jo.experience_level, os.requirement_type
        ORDER BY count DESC
        LIMIT %s
        """
        params.append(top_n)

        df = pd.read_sql_query(query, conn, params=params)
        return df
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
        initial_sidebar_state="collapsed"
    )

    # Wstrzyknij custom CSS
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # ========================================================================
    # STRONA GŁÓWNA — nagłówek + karty metryk
    # ========================================================================

    st.markdown("<h1>SkillGap Monitor</h1>", unsafe_allow_html=True)
    st.markdown(
        """
        <p style='font-size: 1.25rem; margin-bottom: 2.5rem;'>
        Automatyczna analityka rynku pracy IT — wynagrodzenia, kompetencje, trendy.
        </p>
        """,
        unsafe_allow_html=True
    )

    # Karty metryk — 4 kolumny
    metrics = query_overview_metrics()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Oferty pracy", f"{metrics['total_offers']:,}")
    with col2:
        st.metric("Firmy", f"{metrics['total_companies']:,}")
    with col3:
        st.metric("Mediana B2B Senior", f"{metrics['median_b2b_senior']:,} PLN")
    with col4:
        st.metric("Technologie", f"{metrics['total_skills']:,}")

    st.markdown("<div style='margin-top: 3rem;'></div>", unsafe_allow_html=True)

    # ========================================================================
    # ZAKŁADKI ANALITYCZNE
    # ========================================================================

    tab1, tab2, tab3 = st.tabs([
        "💰 Salary Explorer",
        "🚀 Skill Premium",
        "📈 Skill Gap"
    ])

    # ------------------------------------------------------------------------
    # TAB 1: Salary Explorer
    # ------------------------------------------------------------------------
    with tab1:
        st.markdown("### Rozkład wynagrodzeń")
        st.markdown(
            "<p style='margin-bottom: 1.5rem;'>Mediana i percentyle (P25/P75) per poziom doświadczenia i typ umowy.</p>",
            unsafe_allow_html=True
        )

        col1, col2 = st.columns(2)
        with col1:
            contract_type = st.selectbox(
                "Typ umowy",
                ["Wszystkie", "B2B", "UoP", "UoD", "Other"],
                key="salary_contract"
            )
        with col2:
            currency = st.selectbox(
                "Waluta",
                ["PLN", "EUR", "USD"],
                key="salary_currency"
            )

        contract_filter = None if contract_type == "Wszystkie" else contract_type
        df_salary = query_salary_stats(contract_filter, currency)

        if df_salary.empty:
            st.warning("⚠️ Brak danych dla wybranych filtrów.")
        else:
            # Przygotowanie danych do box plot
            plot_data = []
            for _, row in df_salary.iterrows():
                label = f"{row['experience_level'].capitalize()} ({row['contract_type'].upper()})"
                plot_data.extend([
                    {"Grupa": label, "Wynagrodzenie": row['p25'], "experience_level": row['experience_level']},
                    {"Grupa": label, "Wynagrodzenie": row['median'], "experience_level": row['experience_level']},
                    {"Grupa": label, "Wynagrodzenie": row['p75'], "experience_level": row['experience_level']},
                ])

            df_plot = pd.DataFrame(plot_data)

            # Kolejność kategorii
            category_order = ["junior", "mid", "senior", "lead"]
            ordered_groups = []
            for level in category_order:
                for ct in sorted(df_salary["contract_type"].unique()):
                    label = f"{level.capitalize()} ({ct.upper()})"
                    if label in df_plot["Grupa"].values:
                        ordered_groups.append(label)

            # Gradient kolorów per poziom
            color_map = {
                "junior": "#30d158",
                "mid": "#0a84ff",
                "senior": "#ff375f",
                "lead": "#bf5af2"
            }

            fig = px.box(
                df_plot,
                x="Grupa",
                y="Wynagrodzenie",
                color="experience_level",
                color_discrete_map=color_map,
                labels={"Wynagrodzenie": f"Wynagrodzenie ({currency})"},
                category_orders={"Grupa": ordered_groups},
                height=500
            )
            fig.update_layout(
                template=PLOTLY_TEMPLATE,
                xaxis_tickangle=0,
                showlegend=True,
                legend=dict(
                    title="Poziom",
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                title=None
            )
            st.plotly_chart(fig, use_container_width=True)

            # Tabela szczegółów
            st.markdown("#### Szczegóły statystyk")
            df_display = df_salary.copy()
            df_display.columns = ["Poziom", "Umowa", "Liczba ofert", "P25", "Mediana", "P75"]
            st.dataframe(df_display, use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------------
    # TAB 2: Skill Premium
    # ------------------------------------------------------------------------
    with tab2:
        st.markdown("### Skill Premium")
        st.markdown(
            "<p style='margin-bottom: 1.5rem;'>Top 20 umiejętności podnoszących medianę wynagrodzenia.</p>",
            unsafe_allow_html=True
        )

        currency_premium = st.selectbox(
            "Waluta",
            ["PLN", "EUR", "USD"],
            key="premium_currency"
        )

        df_premium = query_skill_premium(top_n=20, currency_filter=currency_premium)

        if df_premium.empty:
            st.warning("⚠️ Brak danych dla wybranej waluty.")
        else:
            fig = px.bar(
                df_premium,
                x="premium",
                y="skill_name",
                orientation="h",
                labels={
                    "premium": f"Premium ({currency_premium})",
                    "skill_name": "Umiejętność"
                },
                color_discrete_sequence=["#0a84ff"]
            )
            fig.update_layout(
                template=PLOTLY_TEMPLATE,
                yaxis={"categoryorder": "total ascending"},
                margin=dict(l=150, r=20, t=40, b=40),
                showlegend=False,
                height=550,
                title=None
            )
            st.plotly_chart(fig, use_container_width=True)

            # Tabela szczegółów
            st.markdown("#### Szczegóły premium")
            df_display = df_premium.copy()
            df_display.columns = [
                "Umiejętność",
                "Mediana (ze skilliem)",
                "Mediana (bez skilla)",
                "Premium"
            ]
            st.dataframe(df_display, use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------------
    # TAB 3: Skill Gap
    # ------------------------------------------------------------------------
    with tab3:
        st.markdown("### Skill Gap")
        st.markdown(
            "<p style='margin-bottom: 1.5rem;'>Top 15 najczęściej wymaganych umiejętności per poziom doświadczenia.</p>",
            unsafe_allow_html=True
        )

        experience_level = st.selectbox(
            "Poziom doświadczenia",
            ["Wszystkie", "Junior", "Mid", "Senior", "Lead"],
            key="gap_experience"
        )

        exp_filter = None if experience_level == "Wszystkie" else experience_level
        df_gap = query_skill_gap(top_n=15, experience_filter=exp_filter)

        if df_gap.empty:
            st.warning("⚠️ Brak danych dla wybranego poziomu.")
        else:
            fig = px.bar(
                df_gap,
                x="count",
                y="skill_name",
                color="requirement_type",
                barmode="group",
                orientation="h",
                labels={
                    "count": "Liczba ofert",
                    "skill_name": "Umiejętność",
                    "requirement_type": "Typ wymagania"
                },
                color_discrete_map={"must": "#ff375f", "nice": "#30d158"},
                height=600
            )
            fig.update_layout(
                template=PLOTLY_TEMPLATE,
                yaxis={"categoryorder": "total ascending"},
                margin=dict(l=160, r=20, t=40, b=40),
                legend=dict(
                    title="Typ wymagania",
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                title=None
            )
            st.plotly_chart(fig, use_container_width=True)

            # Tabela szczegółów
            st.markdown("#### Szczegóły wymagań")
            df_display = df_gap.copy()
            df_display.columns = ["Umiejętność", "Poziom", "Typ wymagania", "Liczba ofert"]
            st.dataframe(df_display, use_container_width=True, hide_index=True)

    # ========================================================================
    # FOOTER z indeksem
    # ========================================================================

    st.markdown(
        """
        <div class='footer-custom'>
            Projekt akademicki: <strong>Mateusz Elżbieciak (Indeks: 233651)</strong><br>
            Informatyka Stosowana, Uniwersytet Ekonomiczny w Krakowie
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
