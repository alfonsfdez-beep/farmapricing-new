"""
Dashboard ejecutivo — KPIs y top oportunidades.
"""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from lib import data as d  # noqa: E402
from lib import decisions as dec  # noqa: E402
from lib import ui  # noqa: E402

ui.setup_page("Dashboard")
ui.page_header("Dashboard ejecutivo", "Vista de alto nivel sobre el estado de tu pricing y surtido")

rec = d.get_recomendaciones()
huecos_fam = d.get_huecos_familia()
hist = dec.get_pricing_decisions()

if rec.empty:
    st.warning("No hay recomendaciones. Lanza el pipeline en el PC primero.")
    st.stop()

# -------------- KPIs --------------
accionables = rec[rec["TipoCambio"].isin(["PVP", "PROMO"])]
ya_decididos = dec.get_decided_ids("pricing")
pendientes = accionables[~accionables["IdArticulo"].astype(str).isin(ya_decididos)]

aprobados_30d = 0
if not hist.empty:
    last_30 = hist["Timestamp_dt"] >= (pd.Timestamp.now() - pd.Timedelta(days=30))
    aprobados_30d = int(((hist["Decision"] == "Aprobado") & last_30).sum())

impacto_facturacion = pd.to_numeric(
    rec.get("Impacto_Facturacion_30d_est", pd.Series(dtype=float)), errors="coerce"
).sum() if "Impacto_Facturacion_30d_est" in rec.columns else 0
impacto_margen = pd.to_numeric(
    rec.get("Impacto_Margen_30d_est", pd.Series(dtype=float)), errors="coerce"
).sum() if "Impacto_Margen_30d_est" in rec.columns else 0

cobertura_pond = None
if not huecos_fam.empty and "Cobertura_Pct" in huecos_fam.columns:
    tot = huecos_fam["Venta_Mercado_Total"].sum()
    if tot > 0:
        cobertura_pond = (
            huecos_fam["Cobertura_Pct"] * huecos_fam["Venta_Mercado_Total"]
        ).sum() / tot

c1, c2, c3, c4 = st.columns(4)
c1.metric("Recomendaciones pendientes", len(pendientes), help="Sin decisión aún")
c2.metric("Aprobadas (últimos 30 días)", aprobados_30d)
c3.metric(
    "Impacto facturación (a Q constante)",
    ui.euro(impacto_facturacion),
    help="Suma del impacto estimado sin asumir uplift de unidades — escenario conservador",
)
c4.metric(
    "Cobertura mercado (ponderada)",
    f"{cobertura_pond:.1f}%" if cobertura_pond else "-",
    help="% de la venta del mercado que ya tienes en catálogo",
)

st.divider()

# -------------- Distribución por clasificación --------------
left, right = st.columns([1, 1])

with left:
    st.subheader("Distribución por clasificación")
    counts = rec["Clasificacion"].value_counts().reset_index()
    counts.columns = ["Clasificacion", "n"]
    counts = counts[counts["Clasificacion"] != "NO_TOCAR"]
    if counts.empty:
        st.info("No hay clasificaciones accionables.")
    else:
        fig = px.pie(
            counts, names="Clasificacion", values="n", hole=0.55,
            color="Clasificacion",
            color_discrete_map=ui.CLASIF_COLORS,
        )
        fig.update_layout(height=320, margin=dict(t=10, b=10, l=10, r=10),
                          legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Top 10 oportunidades por impacto en margen")
    if "Impacto_Margen_30d_est" in rec.columns:
        top = rec[rec["TipoCambio"].isin(["PVP", "PROMO"])].copy()
        top["Impacto_Margen_30d_est_abs"] = top["Impacto_Margen_30d_est"].abs()
        top = top.sort_values("Impacto_Margen_30d_est_abs", ascending=False).head(10)
        if not top.empty:
            fig = px.bar(
                top.sort_values("Impacto_Margen_30d_est_abs"),
                x="Impacto_Margen_30d_est_abs",
                y="Descripcion",
                color="Clasificacion",
                orientation="h",
                color_discrete_map=ui.CLASIF_COLORS,
                hover_data=["IdArticulo", "PVP", "PVP_Mercado", "Impacto_Margen_30d_est"],
            )
            fig.update_layout(height=380, margin=dict(t=10, b=10, l=10, r=10),
                              xaxis_title="Impacto margen 30d (€, abs.)",
                              yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay oportunidades aún.")

st.divider()

# -------------- Cobertura por familia --------------
st.subheader("Cobertura por familia y venta potencial en lo que falta")

if huecos_fam.empty:
    st.info("Sin datos de huecos. Lanza el script 06 con --publish.")
else:
    fam = huecos_fam.copy()
    fam = fam.sort_values("Venta_Faltantes", ascending=True)
    fig = px.bar(
        fam,
        x="Venta_Faltantes",
        y="Familia",
        orientation="h",
        color="Cobertura_Pct",
        color_continuous_scale="RdYlGn",
        range_color=[0, 100],
        hover_data=["SKUs_Mercado", "SKUs_Que_Tengo", "SKUs_Que_Me_Faltan"],
    )
    fig.update_layout(
        height=520,
        coloraxis_colorbar=dict(title="Cobertura %"),
        xaxis_title="Venta del mercado en SKUs que NO tienes (€)",
        yaxis_title="",
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# -------------- Histórico reciente --------------
st.subheader("Decisiones recientes")
if hist.empty:
    st.info("Aún no has tomado decisiones. Ve al Centro de decisiones (Pricing) para empezar.")
else:
    last = hist.sort_values("Timestamp_dt", ascending=False).head(15)
    cols_show = [c for c in [
        "Timestamp", "IdArticulo", "Descripcion", "Clasificacion",
        "TipoCambio", "Decision", "Estado", "Notas",
    ] if c in last.columns]
    st.dataframe(last[cols_show], use_container_width=True, hide_index=True)

ui.sidebar_refresh_button()
