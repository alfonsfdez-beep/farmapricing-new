"""
Log de decisiones del usuario, persistido en Google Sheets.

Pestañas:
  Decisiones_Pricing: una fila por decisión sobre una recomendación de pricing.
  Decisiones_Surtido: una fila por decisión sobre un hueco de surtido.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

import pandas as pd
import streamlit as st

from . import config as cfg
from . import sheets_client as gc

PRICING_HEADER = [
    "Timestamp", "Usuario", "IdArticulo", "Descripcion", "Familia",
    "Clasificacion", "TipoCambio", "PVP_Actual", "PVP_Mercado",
    "PVP_Propuesto", "Descuento_Pct",
    "Aplicar_Precio", "StockMinimo_Nuevo", "StockMaximo_Nuevo", "Aplicar_Stock",
    "Decision", "Estado", "Notas",
]

SURTIDO_HEADER = [
    "Timestamp", "Usuario", "CN", "Descripcion", "Familia", "Subfamilia",
    "PVP_Mercado", "Uds_por_Farmacia",
    "Decision", "Notas",
]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_pricing_decision(
    row: dict,
    decision: Literal["Aprobado", "Rechazado", "Pospuesto", "Aplicado", "Anulado"],
    notas: str = "",
    usuario: str = "Alfonso",
    aplicar_precio: bool = False,
    stock_min: int | None = None,
    stock_max: int | None = None,
    aplicar_stock: bool = False,
) -> None:
    """row es un dict-like con los campos de la recomendación."""
    payload = [
        _now(),
        usuario,
        str(row.get("IdArticulo", "")),
        str(row.get("Descripcion", "")),
        str(row.get("Familia", "")),
        str(row.get("Clasificacion", "")),
        str(row.get("TipoCambio", "")),
        _num(row.get("PVP")),
        _num(row.get("PVP_Mercado")),
        _num(row.get("PVP_Propuesto")),
        _num(row.get("Descuento_Pct")),
        "Sí" if aplicar_precio else "No",
        str(stock_min) if stock_min is not None else "",
        str(stock_max) if stock_max is not None else "",
        "Sí" if aplicar_stock else "No",
        decision,
        "Pendiente aplicar" if decision == "Aprobado" else decision,
        notas,
    ]
    gc.append_row(
        cfg.TAB_DECISIONES_PRICING, payload,
        create_if_missing=True, header=PRICING_HEADER,
    )


def log_surtido_decision(
    row: dict,
    decision: Literal["Comprar", "No me interesa", "Posponer"],
    notas: str = "",
    usuario: str = "Alfonso",
) -> None:
    payload = [
        _now(),
        usuario,
        str(row.get("CN", "")),
        str(row.get("Descripcion", "") or row.get("Descripcion_Mercado", "")),
        str(row.get("Familia", "")),
        str(row.get("Subfamilia", "")),
        _num(row.get("PVP_Mercado")),
        _num(row.get("Uds_por_Farmacia")),
        decision,
        notas,
    ]
    gc.append_row(
        cfg.TAB_DECISIONES_SURTIDO, payload,
        create_if_missing=True, header=SURTIDO_HEADER,
    )


def _num(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    try:
        return f"{float(v):.2f}"
    except (TypeError, ValueError):
        return str(v)


@st.cache_data(ttl=30, show_spinner=False)
def get_pricing_decisions() -> pd.DataFrame:
    """Devuelve el histórico de decisiones de pricing como DataFrame."""
    try:
        values = gc.read_tab(cfg.TAB_DECISIONES_PRICING)
    except Exception:
        return pd.DataFrame(columns=PRICING_HEADER)
    if not values or len(values) < 2:
        return pd.DataFrame(columns=PRICING_HEADER)
    df = pd.DataFrame(values[1:], columns=values[0])
    df["Timestamp_dt"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    return df


@st.cache_data(ttl=30, show_spinner=False)
def get_surtido_decisions() -> pd.DataFrame:
    try:
        values = gc.read_tab(cfg.TAB_DECISIONES_SURTIDO)
    except Exception:
        return pd.DataFrame(columns=SURTIDO_HEADER)
    if not values or len(values) < 2:
        return pd.DataFrame(columns=SURTIDO_HEADER)
    df = pd.DataFrame(values[1:], columns=values[0])
    df["Timestamp_dt"] = pd.to_datetime(df["Timestamp"], errors="coerce")
    return df


def get_decided_ids(kind: Literal["pricing", "surtido"]) -> set[str]:
    """IDs ya decididos (excluye Anulado y Rechazado para que vuelvan a aparecer)."""
    if kind == "pricing":
        df = get_pricing_decisions()
        col = "IdArticulo"
    else:
        df = get_surtido_decisions()
        col = "CN"
    if df.empty or col not in df.columns:
        return set()
    # Excluir decisiones anuladas o rechazadas
    if "Decision" in df.columns:
        df = df[~df["Decision"].isin(["Anulado", "Rechazado"])]
    return set(df[col].astype(str).str.strip())
