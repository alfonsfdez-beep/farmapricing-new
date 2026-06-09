"""
Componentes UI reutilizables + estilos globales.
"""
from __future__ import annotations

import datetime
import streamlit as st


# ---------------------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------------------
PRIMARY   = "#00897B"   # teal
PRIMARY_L = "#E0F2F1"   # teal claro (hover / fondo activo)
DANGER    = "#C62828"
SUCCESS   = "#2E7D32"
WARNING   = "#F57F17"
NEUTRAL   = "#B0BEC5"
TEXT      = "#212529"
TEXT_MUTED = "#6C757D"
BG        = "#F0F2F6"
CARD_BG   = "#FFFFFF"
BORDER    = "#E9ECEF"

CLASIF_COLORS = {
    "TOP_VENTAS": "#0070C0",
    "GANCHO":     "#C00000",
    "MARGEN":     "#00B050",
    "DINAMIZAR":  "#ED7D31",
    "LIQUIDAR":   "#7030A0",
    "NO_TOCAR":   "#A6A6A6",
}

# ---------------------------------------------------------------------------
# CSS global
# ---------------------------------------------------------------------------
_CSS = f"""
<style>

/* ── Fondo general ── */
.stApp {{
    background-color: {BG};
    font-family: 'Inter', 'Segoe UI', sans-serif;
}}

/* ── Área de contenido principal ── */
.main .block-container {{
    padding: 2rem 2.5rem 3rem 2.5rem;
    max-width: 1400px;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background-color: {CARD_BG} !important;
    border-right: 1px solid {BORDER};
}}
[data-testid="stSidebar"] > div:first-child {{
    padding-top: 0.5rem;
}}

/* ── Logo en el sidebar - SIN TRUCOS DE CSS ── */
[data-testid="stSidebar"] img {{
    display: block;
    margin: 0 auto 1.5rem auto;
    padding: 0;
    max-width: 90%;
    object-fit: contain;
}}
[data-testid="stSidebarNav"] a {{
    border-radius: 8px;
    padding: 8px 14px;
    color: {TEXT_MUTED};
    font-weight: 500;
    font-size: 0.9rem;
    transition: all 0.15s ease;
}}
[data-testid="stSidebarNav"] a:hover {{
    background: {PRIMARY_L};
    color: {PRIMARY};
}}
[data-testid="stSidebarNav"] a[aria-current="page"] {{
    background: {PRIMARY_L};
    color: {PRIMARY};
    font-weight: 600;
    border-left: 3px solid {PRIMARY};
}}

/* ── Métricas como tarjetas ── */
[data-testid="stMetric"] {{
    background: {CARD_BG};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 1.1rem 1.4rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}}
[data-testid="stMetricLabel"] {{
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: {TEXT_MUTED} !important;
}}
[data-testid="stMetricValue"] {{
    font-size: 1.7rem !important;
    font-weight: 700 !important;
    color: {TEXT} !important;
}}

/* ── Título de página ── */
h1 {{
    font-size: 1.65rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    color: {TEXT} !important;
    margin-bottom: 0 !important;
}}
h2 {{
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    color: {TEXT} !important;
}}
h3 {{
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    color: {TEXT} !important;
}}

/* ── Botones primarios ── */
.stButton > button[kind="primary"] {{
    background: {PRIMARY};
    border: none;
    border-radius: 8px;
    font-weight: 600;
    padding: 0.45rem 1.2rem;
    transition: background 0.15s;
}}
.stButton > button[kind="primary"]:hover {{
    background: #00796B;
}}
.stButton > button {{
    border-radius: 8px;
    font-weight: 500;
}}

/* ── Selectbox / inputs ── */
[data-testid="stSelectbox"] > label,
[data-testid="stSlider"] > label,
[data-testid="stTextInput"] > label {{
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: {TEXT_MUTED};
}}

/* ── Selectbox destacado ── */
[data-testid="stSelectbox"] > div > div {{
    border: 2px solid {PRIMARY} !important;
    border-radius: 8px;
    background: {CARD_BG};
    transition: all 0.2s ease;
}}
[data-testid="stSelectbox"] > div > div:hover {{
    border-color: #00796B;
    box-shadow: 0 2px 8px rgba(0, 137, 123, 0.15);
}}

/* ── Text Input destacado ── */
[data-testid="stTextInput"] input {{
    border: 2px solid {PRIMARY} !important;
    border-radius: 8px;
    transition: all 0.2s ease;
}}
[data-testid="stTextInput"] input:hover {{
    border-color: #00796B;
}}
[data-testid="stTextInput"] input:focus {{
    border-color: #00796B !important;
    box-shadow: 0 0 0 3px rgba(0, 137, 123, 0.1);
}}

/* ── Checkbox mejorado ── */
[data-testid="stCheckbox"] {{
    padding: 0.5rem;
}}
[data-testid="stCheckbox"] label {{
    font-weight: 500;
    color: {TEXT};
}}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}}

/* ── Divisor ── */
hr {{
    border: none;
    border-top: 1px solid {BORDER};
    margin: 1.5rem 0;
}}

/* ── Info / Warning / Success ── */
[data-testid="stAlert"] {{
    border-radius: 10px;
    border-left-width: 4px;
}}

/* ── Caption ── */
[data-testid="stCaptionContainer"] p {{
    color: {TEXT_MUTED};
    font-size: 0.82rem;
}}

/* ── Ocultar footer de Streamlit ── */
footer {{ visibility: hidden; }}
#MainMenu {{ visibility: hidden; }}

/* ── Progress bars (ProgressColumn) ── */
.stProgress > div > div > div {{
    background-color: {PRIMARY};
}}

</style>
"""


# ---------------------------------------------------------------------------
# Helpers de formato
# ---------------------------------------------------------------------------

def clasif_badge(clasif: str) -> str:
    color = CLASIF_COLORS.get(clasif, "#595959")
    return (
        f'<span style="background:{color};color:white;padding:2px 8px;'
        f'border-radius:10px;font-size:11px;font-weight:600;">{clasif}</span>'
    )


def metric_row(items: list[tuple[str, str, str | None]]) -> None:
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        label, value, delta = item
        with col:
            st.metric(label=label, value=value, delta=delta)


def euro(v) -> str:
    try:
        return f"{float(v):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "-"


def pct(v, decimals: int = 1) -> str:
    try:
        return f"{float(v) * 100:.{decimals}f}%"
    except (TypeError, ValueError):
        return "-"


def pct_already(v, decimals: int = 1) -> str:
    try:
        return f"{float(v):.{decimals}f}%"
    except (TypeError, ValueError):
        return "-"


# ---------------------------------------------------------------------------
# Componentes de layout
# ---------------------------------------------------------------------------

def page_header(title: str, subtitle: str = "") -> None:
    """Cabecera de página con título en mayúsculas y timestamp a la derecha."""
    now = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M")
    col_title, col_ts = st.columns([8, 2])
    with col_title:
        st.markdown(f"# {title}")
        if subtitle:
            st.caption(subtitle)
    with col_ts:
        st.markdown(
            f'<p style="text-align:right;color:{TEXT_MUTED};font-size:11px;'
            f'margin-top:14px;font-weight:500;letter-spacing:0.3px;">'
            f'ÚLTIMA ACTUALIZACIÓN<br><b>{now}</b></p>',
            unsafe_allow_html=True,
        )


def filter_card(label: str = "FILTROS DE DATOS") -> None:
    """Encabezado de sección de filtros."""
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:0.75rem;">'
        f'<span style="color:{PRIMARY};font-size:1rem;">▼</span>'
        f'<span style="font-size:0.78rem;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:0.6px;color:{TEXT_MUTED};">{label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def section_card_start() -> None:
    """Abre una tarjeta de contenido con sombra y borde."""
    st.markdown(
        f'<div style="background:{CARD_BG};border:1px solid {BORDER};'
        f'border-radius:12px;padding:1.25rem 1.5rem;'
        f'box-shadow:0 1px 4px rgba(0,0,0,0.05);margin-bottom:1rem;">',
        unsafe_allow_html=True,
    )


def section_card_end() -> None:
    st.markdown('</div>', unsafe_allow_html=True)


def sidebar_logo() -> None:
    """Intenta cargar el logo Pharmapricing en el sidebar desde múltiples rutas."""
    import os

    possible_paths = [
        "assets/Pharmapricing_logo.png",
        os.path.join(os.path.dirname(__file__), "..", "assets", "Pharmapricing_logo.png"),
        "/Users/alfonsofernandezbernal/Documents/Claude/Projects/Farmapricing Agent/app/assets/Pharmapricing_logo.png",
    ]

    for logo_path in possible_paths:
        if os.path.exists(logo_path):
            try:
                st.sidebar.image(logo_path, width=200)
                st.sidebar.divider()
                return
            except Exception:
                continue

    # Fallback: mostrar icono de texto
    st.sidebar.markdown(
        f'<div style="padding:1rem 0.5rem;text-align:center;">'
        f'<div style="font-size:1.2rem;font-weight:800;color:{PRIMARY};">◯</div>'
        f'<div style="font-size:0.9rem;color:{TEXT};font-weight:700;">Farmapricing</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.sidebar.divider()


def sidebar_brand(name: str = "Farmapricing") -> None:
    """Logo / nombre de la farmacia en el sidebar."""
    st.sidebar.markdown(
        f'<div style="padding:0.5rem 0.5rem 1.2rem 0.5rem;">'
        f'<div style="font-size:1.05rem;font-weight:800;color:{TEXT};'
        f'letter-spacing:0.3px;">'
        f'<span style="color:{PRIMARY};">⬡</span>&nbsp;{name}</div>'
        f'<div style="font-size:0.72rem;color:{TEXT_MUTED};margin-top:2px;">'
        f'Centro de decisiones</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Configuración de página
# ---------------------------------------------------------------------------

def setup_page(title: str, icon: str = "💊") -> None:
    st.set_page_config(
        page_title=f"Farmapricing · {title}",
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(_CSS, unsafe_allow_html=True)
    sidebar_logo()
    sidebar_brand()


def sidebar_refresh_button() -> None:
    from . import data as d
    with st.sidebar:
        st.divider()
        if st.button("⟳  Recargar datos", use_container_width=True):
            d.refresh_all()
            st.rerun()
        st.caption("Caché 60 s · pulsa para forzar lectura")
