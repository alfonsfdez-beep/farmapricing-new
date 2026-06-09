"""
Estrategia: Análisis Pareto 20/80 para identificar productos top ventas.

Muestra qué 20% de SKUs generan 80% de venta por familia/subfamilia.
Útil para decisiones de promoción y detección de concentración de riesgo.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from lib import data as d  # noqa: E402
from lib import estrategia as est  # noqa: E402
from lib import ui  # noqa: E402

ui.setup_page("Estrategia")
ui.page_header("Análisis Estratégico", "Regla de Pareto 20/80 para identificar productos top ventas")

# ── Cargar datos ──────────────────────────────────────────────────────────────
rec = d.get_recomendaciones()

if rec.empty:
    st.error("No hay datos disponibles. Ejecuta el pipeline de recomendaciones primero.")
    st.stop()

# ── Sidebar: Filtros ──────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("Filtros")

    familias_disponibles = sorted(
        rec["Familia"].dropna().unique().tolist()
    )
    familias_seleccionadas = st.multiselect(
        "Familias a analizar",
        familias_disponibles,
        default=familias_disponibles[:5] if len(familias_disponibles) > 0 else [],
    )

    mostrar_solo_top = st.checkbox("Mostrar solo top 20%", value=False)
    columna_venta = st.selectbox(
        "Métrica de venta para Pareto",
        ["Ventas_30d", "Ventas_7d", "Ventas_90d"],
        index=0,
    )

    st.divider()
    if st.button("🔄 Recargar datos", use_container_width=True):
        d.refresh_all()
        st.rerun()

    ui.sidebar_refresh_button()

# ── Filtrar datos por familia seleccionada ────────────────────────────────────
if not familias_seleccionadas:
    st.info("Selecciona al menos una familia en el sidebar para ver el análisis.")
    st.stop()

rec_filtrado = rec[rec["Familia"].isin(familias_seleccionadas)].copy()

if rec_filtrado.empty:
    st.warning("No hay datos para las familias seleccionadas.")
    st.stop()

# ── KPI Global ────────────────────────────────────────────────────────────────
st.subheader("Resumen Global")

col1, col2, col3, col4, col5 = st.columns(5)

stats_global = est.obtener_stats_pareto(rec_filtrado, columna_venta)

col1.metric("SKUs Totales", stats_global["n_total_skus"])
col2.metric("SKUs Top 20%", stats_global["n_top_20"])
col3.metric("% Top 20 del Catálogo", f"{stats_global['pct_top_20']:.1f}%")
col4.metric("Venta Total", f"${stats_global['venta_total']:.0f}")
col5.metric("Concentración", f"{stats_global['concentracion_pct']:.1f}%")

st.markdown(f"**📊 Insight:** {est.generar_insight_concentracion(stats_global)}")

st.divider()

# ── Análisis por Familia ──────────────────────────────────────────────────────
st.subheader("Análisis por Familia")

for familia in familias_seleccionadas:
    # Datos de esta familia
    familia_df = rec_filtrado[rec_filtrado["Familia"] == familia].copy()

    if familia_df.empty:
        continue

    # Crear tabs para subfamilias
    subfamilias = sorted(familia_df["Subfamilia"].dropna().unique().tolist())

    with st.expander(f"📁 **{familia}** ({len(familia_df)} SKUs)", expanded=True):
        # KPI por familia
        stats_familia = est.obtener_stats_pareto(familia_df, columna_venta)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("SKUs", stats_familia["n_total_skus"])
        c2.metric("Top 20%", stats_familia["n_top_20"])
        c3.metric("Venta", f"${stats_familia['venta_total']:.0f}")
        c4.metric("Concentración", f"{stats_familia['concentracion_pct']:.1f}%")

        st.caption(f"💡 {est.generar_insight_concentracion(stats_familia)}")

        st.markdown("---")

        # Tabla Pareto por subfamilia
        if len(subfamilias) > 1:
            st.markdown("#### Por Subfamilia")
            tab_list = st.tabs(subfamilias)
        else:
            tab_list = [None]

        for tab_idx, subfamilia in enumerate(subfamilias):
            # Dentro de tab o sin tab
            if len(subfamilias) > 1:
                context = tab_list[tab_idx]
            else:
                context = st

            with context:
                subfamilia_df = familia_df[familia_df["Subfamilia"] == subfamilia].copy()

                # Calcular Pareto
                pareto_df = est.calcular_pareto(subfamilia_df, columna_venta)

                # Filtrar si es necesario
                if mostrar_solo_top:
                    pareto_df = pareto_df[pareto_df["es_top_20_pct"]].copy()

                # Preparar tabla para visualización
                tabla_display = pareto_df[
                    ["rank", "IdArticulo", "Descripcion", columna_venta, "pct_acumulado", "PVP", "MargenActual_Pct", "StockActual"]
                ].copy()

                # Renombrar columnas
                tabla_display.columns = [
                    "Rank",
                    "CN",
                    "Descripción",
                    "Ventas 30d",
                    "Acum %",
                    "PVP",
                    "Margen %",
                    "Stock",
                ]

                # Configurar colores
                def color_top_20(val):
                    """Colorear fondo si está en top 20%"""
                    if val:
                        return "background-color: #d4edda"  # verde light
                    return ""

                # Mostrar tabla
                st.dataframe(
                    tabla_display.astype(
                        {
                            "Ventas 30d": "int",
                            "Acum %": "float",
                            "PVP": "float",
                            "Margen %": "float",
                            "Stock": "int",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                    height=min(400, 50 + len(tabla_display) * 35),
                )

                # Stats de esta subfamilia
                stats_subfam = est.obtener_stats_pareto(subfamilia_df, columna_venta)
                if subfamilia == subfamilias[0]:  # Mostrar insight solo una vez
                    st.markdown(
                        f"**{len(subfamilia_df)} SKUs:** {stats_subfam['n_top_20']} productos "
                        f"({stats_subfam['pct_top_20']:.0f}% del catálogo) generan "
                        f"{stats_subfam['concentracion_pct']:.1f}% de venta"
                    )

st.divider()

# ── Recomendaciones ──────────────────────────────────────────────────────────
st.subheader("🎯 Recomendaciones para Promoción")

recommendations = []

for familia in familias_seleccionadas:
    familia_df = rec_filtrado[rec_filtrado["Familia"] == familia].copy()
    stats = est.obtener_stats_pareto(familia_df, columna_venta)

    # Recomendación 1: Alto potencial en stock bajo
    top_20_df = familia_df.nlargest(stats["n_top_20"], columna_venta)
    low_stock_high_sales = top_20_df[
        (top_20_df["StockActual"] < 5) & (top_20_df[columna_venta] > 0)
    ]

    if not low_stock_high_sales.empty:
        for _, prod in low_stock_high_sales.iterrows():
            recommendations.append({
                "familia": familia,
                "tipo": "⏰ Stock Bajo",
                "producto": f"{prod.get('Descripcion', 'N/A')[:40]}",
                "accion": f"Reponer urgentemente (Stock: {int(prod.get('StockActual', 0))})",
            })

    # Recomendación 2: Considerar promoción en top 20%
    if stats["concentracion_pct"] >= 80:
        top_3 = familia_df.nlargest(3, columna_venta)
        for _, prod in top_3.iterrows():
            if prod.get(columna_venta, 0) > 0:
                recommendations.append({
                    "familia": familia,
                    "tipo": "📢 Promoción",
                    "producto": f"{prod.get('Descripcion', 'N/A')[:40]}",
                    "accion": f"Top venta ({prod.get(columna_venta, 0):.0f} uds) → Promocionar",
                })

    # Recomendación 3: Analizar productos lentos
    slow_movers = familia_df[familia_df[columna_venta] <= 1].head(3)
    if not slow_movers.empty:
        recommendations.append({
            "familia": familia,
            "tipo": "🤔 Análisis",
            "producto": f"{len(familia_df[familia_df[columna_venta] <= 1])} productos sin venta",
            "accion": "Revisar si eliminar del catálogo o reposicionar",
        })

if recommendations:
    rec_df = pd.DataFrame(recommendations)

    # Mostrar por tipo
    for rec_type in rec_df["tipo"].unique():
        col1, col2, col3, col4 = st.columns([1, 2, 2, 2])
        tipo_recs = rec_df[rec_df["tipo"] == rec_type]

        for idx, (_, rec) in enumerate(tipo_recs.iterrows()):
            if idx == 0:
                with col1:
                    st.markdown(f"**{rec['tipo']}**")
                with col2:
                    st.markdown(f"**{rec['familia']}**")
                with col3:
                    st.markdown(rec['producto'])
                with col4:
                    st.markdown(f"*{rec['accion']}*")
            else:
                with col1:
                    st.markdown("")
                with col2:
                    st.markdown(f"**{rec['familia']}**")
                with col3:
                    st.markdown(rec['producto'])
                with col4:
                    st.markdown(f"*{rec['accion']}*")
else:
    st.info("No hay recomendaciones inmediatas para las familias seleccionadas.")

ui.sidebar_refresh_button()
