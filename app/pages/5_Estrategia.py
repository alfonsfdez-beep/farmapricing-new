"""
Estrategia de Mercado: Análisis competitivo y cobertura de categoría.

Compara tu oferta vs el mercado:
- Cobertura: ¿Qué productos tiene el mercado que tú no?
- Precios: ¿Estás alineado con el mercado?
- Stock: ¿Tienes disponibilidad en productos top venta?
- Decisiones: ¿Promocionar, reponer, o alinear precio?
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from lib import data as d  # noqa: E402
from lib import ui  # noqa: E402

ui.setup_page("Estrategia")
ui.page_header("Estrategia de Mercado", "Compara tu oferta vs el mercado: cobertura, precios, stock")

# ── Cargar datos ──────────────────────────────────────────────────────────────
mercado = d.get_mercado()
rec = d.get_recomendaciones()

if mercado.empty or rec.empty:
    st.error("No hay datos disponibles. Ejecuta el pipeline primero.")
    st.stop()

# ── Sidebar: Logo + Filtros ───────────────────────────────────────────────────
with st.sidebar:
    # Logo
    try:
        st.image("assets/Pharmapricing_logo.png", width=200)
    except Exception:
        st.markdown("""
        <div style="padding-bottom: 20px;">
            <h2 style="margin: 0; color: #00897B;">◯ Farmapricing</h2>
            <p style="margin: 5px 0 0 0; color: #999; font-size: 14px;">Centro de decisiones</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    st.subheader("Filtros")

    # Filtro 1: Familia
    familias_disponibles = sorted(
        mercado["Familia"].dropna().unique().tolist()
    )
    familia_seleccionada = st.selectbox(
        "Familia a analizar",
        familias_disponibles,
        index=0 if familias_disponibles else None,
    )

    # Filtro 2: Subfamilia (dinámico según familia)
    if familia_seleccionada:
        subfamilias_disponibles = sorted(
            mercado[mercado["Familia"] == familia_seleccionada]["Subfamilia"].dropna().unique().tolist()
        )
        subfamilia_seleccionada = st.selectbox(
            "Subfamilia",
            subfamilias_disponibles,
            index=0 if subfamilias_disponibles else None,
        )
    else:
        subfamilia_seleccionada = None

    mostrar_solo_gaps = st.checkbox("Mostrar solo GAPS (me falta)", value=False)

    st.divider()
    if st.button("🔄 Recargar datos", use_container_width=True):
        d.refresh_all()
        st.rerun()

    ui.sidebar_refresh_button()

# ── Filtrar datos ──────────────────────────────────────────────────────────────
if not familia_seleccionada or not subfamilia_seleccionada:
    st.info("Selecciona familia y subfamilia en el sidebar para ver el análisis.")
    st.stop()

mercado_fam = mercado[mercado["Familia"] == familia_seleccionada].copy()
rec_fam = rec[rec["Familia"] == familia_seleccionada].copy()

mercado_subfam = mercado_fam[mercado_fam["Subfamilia"] == subfamilia_seleccionada].copy()
rec_subfam = rec_fam[rec_fam["Subfamilia"] == subfamilia_seleccionada].copy()

if mercado_subfam.empty:
    st.warning(f"No hay datos de mercado para {familia_seleccionada} > {subfamilia_seleccionada}.")
    st.stop()

# ── Análisis de Cobertura ─────────────────────────────────────────────────────
st.subheader("📊 Cobertura de Categoría")

n_mercado = len(mercado_subfam)
n_tengo = len(rec_subfam)
n_falta = n_mercado - n_tengo
cobertura_pct = round(n_tengo / n_mercado * 100, 1) if n_mercado > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("SKUs en Mercado", n_mercado)
col2.metric("SKUs que Tengo", n_tengo, delta=f"{cobertura_pct}%")
col3.metric("SKUs Faltantes", n_falta)
col4.metric("Cobertura", f"{cobertura_pct}%", delta="del catálogo")

# Insight de cobertura
if cobertura_pct >= 80:
    insight = "✅ Buena cobertura - tienes la mayoría del catálogo"
elif cobertura_pct >= 60:
    insight = "⚠️ Cobertura media - hay gaps importantes"
else:
    insight = "🚨 Cobertura baja - estás perdiendo productos top"

st.markdown(f"**Insight:** {insight}")

st.divider()

# ── Análisis de Competitividad ────────────────────────────────────────────────
st.subheader("🎯 Análisis Competitivo")

# Preparar datos para merge
# Ordenar por precio de mercado si existe
if "PVP_Mercado" in mercado_subfam.columns:
    try:
        mercado_subfam = mercado_subfam.sort_values("PVP_Mercado", ascending=False).reset_index(drop=True)
    except Exception:
        mercado_subfam = mercado_subfam.reset_index(drop=True)
else:
    mercado_subfam = mercado_subfam.reset_index(drop=True)

# Preparar datos de mis productos para el merge
cols_rec = ["IdArticulo", "PVP", "MargenActual_Pct", "StockActual"]
cols_rec_available = [c for c in cols_rec if c in rec_subfam.columns]
rec_subfam_merge = rec_subfam[cols_rec_available].copy()
rec_subfam_merge = rec_subfam_merge.rename(columns={"IdArticulo": "IdArticulo_Mio"})

# Identificar columna de código en mercado (puede ser CN o IdArticulo)
merge_key = None
if "CN" in mercado_subfam.columns:
    merge_key = "CN"
elif "IdArticulo" in mercado_subfam.columns:
    merge_key = "IdArticulo"
else:
    st.error(f"No se encontró columna CN o IdArticulo en datos de mercado. Columnas: {mercado_subfam.columns.tolist()}")
    st.stop()

# Join
try:
    merged = mercado_subfam.merge(
        rec_subfam_merge,
        left_on=merge_key,
        right_on="IdArticulo_Mio",
        how="left"
    )
except Exception as e:
    st.error(f"Error en merge: {e}")
    merged = mercado_subfam.copy()

# Calcular posición de precio
if "PVP_Mercado" in merged.columns and "PVP" in merged.columns:
    merged["Diferencia_Precio"] = merged["PVP"] - merged["PVP_Mercado"]
    merged["Posicion"] = merged["Diferencia_Precio"].apply(
        lambda x: "🔴 Más caro" if pd.notna(x) and x > 1 else ("🟢 Más barato" if pd.notna(x) and x < -1 else "🟡 Igual")
    )
else:
    merged["Diferencia_Precio"] = None
    merged["Posicion"] = "—"

# Tabla de análisis - solo columnas clave, compacta
cols_base = [merge_key, "Descripcion_Mercado", "PVP_Mercado"]
cols_display = [c for c in cols_base if c in merged.columns]

# Agregar columns opcionales solo si tienen datos reales
if "PVP" in merged.columns and merged["PVP"].notna().any():
    cols_display.extend(["PVP", "Diferencia_Precio", "Posicion"])
if "StockActual" in merged.columns and merged["StockActual"].notna().any():
    cols_display.append("StockActual")

tabla_competitiva = merged[cols_display].copy()

# Renombrar columnas de forma compacta
new_names = {
    merge_key: "CN",
    "Descripcion_Mercado": "Producto",
    "PVP_Mercado": "P.Mercado €",
    "PVP": "Tu P. €",
    "Diferencia_Precio": "Dif. €",
    "Posicion": "Posición",
    "StockActual": "Stock"
}
rename_map = {k: v for k, v in new_names.items() if k in tabla_competitiva.columns}
tabla_competitiva = tabla_competitiva.rename(columns=rename_map)

# Filtrar gaps si lo pide
if mostrar_solo_gaps and "Tu P. €" in tabla_competitiva.columns:
    tabla_competitiva = tabla_competitiva[tabla_competitiva["Tu P. €"].isna()].copy()

st.dataframe(
    tabla_competitiva,
    use_container_width=True,
    hide_index=True,
    height=min(400, 50 + len(tabla_competitiva) * 30),
    column_config={
        "CN": st.column_config.TextColumn(width="small"),
        "Producto": st.column_config.TextColumn(width="medium"),
        "P.Mercado €": st.column_config.NumberColumn(format="%.2f", width="small"),
        "Tu P. €": st.column_config.NumberColumn(format="%.2f", width="small"),
        "Dif. €": st.column_config.NumberColumn(format="%.2f", width="small"),
        "Posición": st.column_config.TextColumn(width="small"),
        "Stock": st.column_config.NumberColumn(width="small"),
    }
)

# Estadísticas
col1, col2, col3, col4 = st.columns(4)
col1.metric("SKUs Mercado", len(mercado_subfam))
col2.metric("SKUs que tengo", len(rec_subfam))
col3.metric("Cobertura %", f"{cobertura_pct}%")
col4.metric("Tu Margen Avg", f"{rec_subfam['MargenActual_Pct'].mean():.1f}%" if len(rec_subfam) > 0 else "—")

st.divider()

# ── Análisis Pareto del Mercado ──────────────────────────────────────────────
st.subheader("📊 Top Productos del Mercado (Pareto 80/20)")

# Calcular Pareto del mercado (por venta)
venta_col = "VentaTotal_Mercado" if "VentaTotal_Mercado" in mercado_subfam.columns else None

if venta_col and mercado_subfam[venta_col].sum() > 0:
    from lib import estrategia as est

    pareto_mercado = est.calcular_pareto(mercado_subfam, venta_col)

    # Top 20% que generan 80% de venta
    top_20_mercado = pareto_mercado[pareto_mercado["es_top_20_pct"]].copy()

    # Verificar qué de estos TOP tengo yo
    top_20_mercado["Tengo"] = top_20_mercado[merge_key].isin(
        rec_subfam[["IdArticulo"]].values.flatten()
    )

    n_top_total = len(top_20_mercado)
    n_top_tengo = top_20_mercado["Tengo"].sum()
    n_top_falta = n_top_total - n_top_tengo

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("SKUs TOP 20%", n_top_total)
    col2.metric("De estos, TENGO", int(n_top_tengo))
    col3.metric("De estos, ME FALTA", int(n_top_falta))
    col4.metric("Cobertura TOP", f"{round(n_top_tengo/n_top_total*100, 1)}%")

    # Tabla de TOP productos
    st.markdown("#### Productos que generan 80% de venta")

    tabla_top = top_20_mercado[[merge_key, "Descripcion_Mercado", venta_col, "Tengo"]].copy()
    tabla_top.columns = ["CN", "Producto", "Venta Mercado", "¿Tengo?"]
    tabla_top["¿Tengo?"] = tabla_top["¿Tengo?"].apply(lambda x: "✅ Sí" if x else "❌ No")

    st.dataframe(
        tabla_top,
        use_container_width=True,
        hide_index=True,
        height=min(400, 50 + len(tabla_top) * 30),
    )

    # Insight
    if n_top_falta > 0:
        st.warning(
            f"⚠️ **Te faltan {int(n_top_falta)} productos del TOP 20% del mercado.**\n\n"
            f"Estos {int(n_top_total)} SKUs generan el **80% de la venta del mercado**. "
            f"Para competir efectivamente, deberías tener al menos estos {int(n_top_total)} productos."
        )
    else:
        st.success(f"✅ **Tienes cobertura completa del TOP 20% del mercado.**")

st.divider()

# ── Recomendaciones de Estrategia ────────────────────────────────────────────
st.subheader("💡 Recomendaciones Estratégicas")

recommendations = []

# 1. Productos con baja cobertura o stock bajo
for _, row in merged.iterrows():
    stock = row.get("StockActual")

    # Si no tengo (PVP es NaN) → GAP
    if pd.isna(row.get("PVP")):
        recom = {
            "tipo": "🚨 GAP",
            "producto": row.get("Descripcion_Mercado", "N/A")[:50],
            "razon": f"Mercado: {row.get('PVP_Mercado', 0):.2f}€",
            "accion": "Incorporar en catálogo"
        }
        recommendations.append(recom)
    elif pd.notna(stock) and stock < 3:
        # Tengo pero stock bajo
        recom = {
            "tipo": "⏰ Stock Bajo",
            "producto": row.get("Descripcion_Mercado", "N/A")[:50],
            "razon": f"Tu stock: {int(stock)} uds",
            "accion": "Reponer urgente"
        }
        recommendations.append(recom)

# 2. Productos donde soy más caro que el mercado
for _, row in merged.iterrows():
    diff = row.get("Diferencia_Precio")
    if pd.notna(diff) and diff > 2:
        recom = {
            "tipo": "💰 Precio Alto",
            "producto": row.get("Descripcion_Mercado", "N/A")[:50],
            "razon": f"Mercado: {row.get('PVP_Mercado', 0):.2f}€ | Tu: {row.get('PVP', 0):.2f}€",
            "accion": "Alinear precio"
        }
        recommendations.append(recom)

if recommendations:
    rec_df = pd.DataFrame(recommendations).drop_duplicates(subset=["producto"])

    for idx, (_, rec) in enumerate(rec_df.head(10).iterrows()):
        with st.container():
            col1, col2, col3, col4 = st.columns([1.5, 2.5, 3, 2])
            col1.markdown(f"**{rec['tipo']}**")
            col2.markdown(rec['producto'])
            col3.markdown(f"*{rec['razon']}*")
            col4.markdown(f"→ {rec['accion']}")
            if idx < len(rec_df.head(10)) - 1:
                st.divider()
else:
    st.info("✅ No hay recomendaciones inmediatas. Categoría bien posicionada.")
