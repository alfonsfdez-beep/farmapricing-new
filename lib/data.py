"""
Capa de datos: lee las pestañas del Sheet alimentadas por el pipeline
y devuelve DataFrames normalizados, con caché de Streamlit.
"""
from __future__ import annotations

import re
import pandas as pd
import streamlit as st

from . import config as cfg
from . import sheets_client as gc


# TTL de caché: 60s. Si quieres datos en tiempo real, llama a clear_cache()
CACHE_TTL = 60


def _to_df(values: list[list[str]]) -> pd.DataFrame:
    if not values:
        return pd.DataFrame()
    header = [str(c).strip() for c in values[0]]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=header)
    # quita columnas con cabecera vacía
    df = df.loc[:, [c for c in df.columns if c != ""]]
    return df


def _coerce_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c].astype(str).str.replace(",", ".").replace("", pd.NA),
                errors="coerce",
            )
    return df


@st.cache_data(ttl=CACHE_TTL, show_spinner="Leyendo recomendaciones...")
def get_recomendaciones() -> pd.DataFrame:
    df = _to_df(gc.read_tab(cfg.TAB_RECOMENDACIONES))
    if df.empty:
        return df
    numeric = [
        "PVP", "PrecioCoste", "MargenActual_Pct",
        "PVP_Mercado", "DeltaPctMercado", "PVP_Propuesto", "Descuento_Pct",
        "Ventas_30d", "Ventas_365d", "StockActual", "DiasStock",
        "Impacto_Facturacion_30d_est", "Impacto_Margen_30d_est",
        "BreakEven_Uplift_Pct",
    ]
    df = _coerce_numeric(df, numeric)
    # IdArticulo siempre como string
    if "IdArticulo" in df.columns:
        df["IdArticulo"] = df["IdArticulo"].astype(str).str.strip()
    return df


@st.cache_data(ttl=CACHE_TTL, show_spinner="Leyendo catálogo (todos los productos)...")
def get_catalogo_todos() -> pd.DataFrame:
    """Lee la pestaña de catálogo con TODOS los productos (incluyendo NO_TOCAR)."""
    try:
        df = _to_df(gc.read_tab("Catalogo_Todos_Productos"))
    except Exception:
        # Fallback a recomendaciones si no existe la pestaña
        return get_recomendaciones()

    if df.empty:
        return df

    numeric = [
        "PVP", "PrecioCoste", "MargenActual_Pct",
        "PVP_Mercado", "DeltaPctMercado", "PVP_Propuesto", "Descuento_Pct",
        "Ventas_30d", "Ventas_365d", "StockActual", "DiasStock",
        "Impacto_Facturacion_30d_est", "Impacto_Margen_30d_est",
        "BreakEven_Uplift_Pct",
    ]
    df = _coerce_numeric(df, numeric)
    if "IdArticulo" in df.columns:
        df["IdArticulo"] = df["IdArticulo"].astype(str).str.strip()
    return df


@st.cache_data(ttl=CACHE_TTL, show_spinner="Leyendo resumen...")
def get_resumen() -> pd.DataFrame:
    try:
        df = _to_df(gc.read_tab(cfg.TAB_RECOMENDACIONES_RESUMEN))
    except Exception:
        return pd.DataFrame()
    return _coerce_numeric(df, ["n", "impacto_fact_30d", "impacto_margen_30d"])


@st.cache_data(ttl=CACHE_TTL, show_spinner="Leyendo huecos por familia...")
def get_huecos_familia() -> pd.DataFrame:
    try:
        df = _to_df(gc.read_tab(cfg.TAB_HUECOS_FAMILIA))
    except Exception:
        return pd.DataFrame()
    return _coerce_numeric(df, [
        "SKUs_Mercado", "SKUs_Que_Tengo", "SKUs_Que_Me_Faltan",
        "Cobertura_Pct", "Venta_Mercado_Total", "Venta_Faltantes",
        "Pct_Venta_Faltantes",
    ])


@st.cache_data(ttl=CACHE_TTL, show_spinner="Leyendo huecos por subfamilia...")
def get_huecos_subfamilia() -> pd.DataFrame:
    try:
        df = _to_df(gc.read_tab(cfg.TAB_HUECOS_SUBFAMILIA))
    except Exception:
        return pd.DataFrame()
    return _coerce_numeric(df, [
        "SKUs_Mercado", "SKUs_Que_Tengo", "SKUs_Que_Me_Faltan",
        "Cobertura_Pct", "Venta_Mercado_Total", "Venta_Faltantes",
        "Pct_Venta_Faltantes",
    ])


@st.cache_data(ttl=CACHE_TTL, show_spinner="Leyendo huecos de productos...")
def get_huecos_productos() -> pd.DataFrame:
    try:
        df = _to_df(gc.read_tab(cfg.TAB_HUECOS_PRODUCTOS))
    except Exception:
        return pd.DataFrame()
    df = _coerce_numeric(df, [
        "PVP_Mercado", "Uds_por_Farmacia", "Uds_Mercado", "VentaTotal_Mercado",
    ])
    if "CN" in df.columns:
        df["CN"] = df["CN"].astype(str).str.strip()
    return df


def _remove_accents(text: str) -> str:
    """Remueve acentos de una cadena."""
    import unicodedata
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')


@st.cache_data(ttl=CACHE_TTL, show_spinner="Leyendo mercado...")
def get_mercado() -> pd.DataFrame:
    try:
        df = _to_df(gc.read_tab(cfg.TAB_MERCADO))
    except Exception:
        return pd.DataFrame()
    # Las columnas pueden venir con nombres variados. Normalizamos flexible.
    rename = {}
    for c in df.columns:
        k = _remove_accents(c.strip().lower())
        # Matching flexible - busca palabras clave en la columna
        if "codigo" in k:
            rename[c] = "CN"
        elif "p." in k and "medio" in k:
            rename[c] = "PVP_Mercado"
        elif "uds" in k and "farmacia" in k:
            rename[c] = "Uds_por_Farmacia"
        elif k == "uds" or k == "uds_mercado":
            rename[c] = "Uds_Mercado"
        elif "venta" in k and "total" in k:
            rename[c] = "VentaTotal_Mercado"
        elif "descripcion" in k:
            rename[c] = "Descripcion_Mercado"
        elif "familia" in k and "subfamilia" not in k:
            rename[c] = "Familia"
        elif "subfamilia" in k:
            rename[c] = "Subfamilia"
    df = df.rename(columns=rename)
    if "CN" in df.columns:
        df["CN"] = df["CN"].astype(str).str.strip()
    df = _coerce_numeric(df, [
        "PVP_Mercado", "Uds_por_Farmacia", "Uds_Mercado", "VentaTotal_Mercado",
    ])
    return df


@st.cache_data(ttl=CACHE_TTL, show_spinner="Leyendo laboratorios...")
def get_laboratorios_lookup() -> pd.DataFrame:
    """Lee tabla de lookup de laboratorios (código → nombre)."""
    try:
        df = _to_df(gc.read_tab("Laboratorios_Lookup"))
    except Exception:
        return pd.DataFrame()

    if df.empty:
        return df

    # Asegurar que Laboratorio es string
    if "Laboratorio" in df.columns:
        df["Laboratorio"] = df["Laboratorio"].astype(str).str.strip()
    return df


def refresh_all() -> None:
    """Limpia toda la caché para forzar lectura fresca de Sheets."""
    st.cache_data.clear()
